# TaskHub

TaskHub is a FastAPI task management API built as the sample app for the 9-day implementation plan in `implementation_plan_9_days.md`.

## Day 1 Scope

- Layered FastAPI project structure.
- FastAPI app factory and application instance.
- Versioned API router under `/api/v1`.
- Lifespan startup/shutdown hooks.
- Dependency injection entrypoint for settings.
- Pydantic v2 base schemas.
- Environment-based settings with `pydantic-settings`.
- Standard error response shape.
- Logging configuration.
- Health check endpoint.

## Local Development

Create a virtual environment, install dependencies, and run the app:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/api/v1/health`

## Checks

```powershell
pytest
mypy .
ruff check .
```