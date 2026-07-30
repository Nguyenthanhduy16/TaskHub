from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

TokenType = Literal["access", "refresh"]
_PASSWORD_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 260_000


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_ITERATIONS,
    )
    return "$".join(
        (
            _PASSWORD_ALGORITHM,
            str(_PASSWORD_ITERATIONS),
            _base64url_encode(salt),
            _base64url_encode(password_hash),
        ),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt_value, expected_value = password_hash.split("$", 3)
        if algorithm != _PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_value)
        salt = _base64url_decode(salt_value)
        expected = _base64url_decode(expected_value)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def create_jwt(
    *,
    subject: str,
    token_type: TokenType,
    secret_key: str,
    expires_delta: timedelta,
    token_id: str | None = None,
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if token_id is not None:
        payload["jti"] = token_id

    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join((_json_segment(header), _json_segment(payload)))
    signature = _sign(signing_input, secret_key)
    return f"{signing_input}.{signature}", expires_at


def decode_jwt(token: str, *, secret_key: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature = token.split(".", 2)
    except ValueError as exc:
        raise TokenError("Invalid token format.") from exc

    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = _sign(signing_input, secret_key)
    if not hmac.compare_digest(expected_signature, signature):
        raise TokenError("Invalid token signature.")

    header = _decode_json_segment(header_segment)
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise TokenError("Unsupported token header.")

    payload = _decode_json_segment(payload_segment)
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise TokenError("Token expiration is missing.")
    if expires_at < int(datetime.now(UTC).timestamp()):
        raise TokenError("Token has expired.")

    return payload


def generate_token_id() -> str:
    return secrets.token_urlsafe(32)


def _json_segment(value: dict[str, Any]) -> str:
    return _base64url_encode(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _decode_json_segment(segment: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_base64url_decode(segment))
    except (json.JSONDecodeError, ValueError) as exc:
        raise TokenError("Invalid token payload.") from exc
    if not isinstance(decoded, dict):
        raise TokenError("Invalid token payload.")
    return cast(dict[str, Any], decoded)


def _sign(signing_input: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
