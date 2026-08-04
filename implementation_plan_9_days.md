# TaskHub Implementation Plan - 9 Days

Nguon yeu cau: `info.pdf`

Muc tieu: xay dung TaskHub - Task Management API bang FastAPI theo dung noi dung module trong PDF. Moi feature/module phai duoc lam qua pull request rieng, review, fix review comments, roi moi merge vao `main`.

## Nguyen tac lam viec

- Moi ngay tuong ung mot branch va mot pull request chinh.
- Quy trinh moi PR: tao branch -> implement -> test/lint/typecheck -> mo PR -> review -> fix comments -> merge.
- Khong merge neu chua pass:
  - `ruff`
  - `mypy`
  - test suite hien co
  - migration check neu co thay doi schema
- Khong gom nhieu module khong lien quan vao cung mot PR neu co the tach duoc.
- Sau khi merge moi PR, cap nhat README/checklist neu co thay doi cach setup hoac API contract.

## Scope theo PDF

Tech stack:

- FastAPI 0.111+
- SQLAlchemy 2.x async
- Alembic
- Pydantic v2
- Redis 7
- MySQL 8 hoac PostgreSQL 16
- Docker / docker compose

Entities chinh:

- User
- Workspace
- WorkspaceMember
- Project
- Task
- Label
- TaskLabel
- Comment
- Notification

Features bat buoc:

- Auth: register, login, refresh token, logout/revoke refresh token
- User: get profile, update profile, change password
- Workspace: CRUD, invite member, remove member, role/permission
- Project: CRUD trong workspace, archive project
- Task: CRUD, assign member, status, priority, due date
- Label: CRUD per project, gan/bo label cho task
- Comment: them/xoa comment tren task
- Filtering va pagination cho task theo status, priority, assignee
- Redis cache cho `GET /api/v1/projects/{id}/tasks`, invalidate khi co thay doi
- Background task gui notification khi task duoc assign
- RBAC theo ADMIN / OWNER / EDITOR / VIEWER va resource ownership
- Swagger/ReDoc day du, Bearer auth scheme, document error responses
- `docker compose up` chay duoc app + DB + Redis
- Ruff pass 100%, mypy khong co error

## Ke hoach 9 ngay

| Ngay | Module theo PDF | Branch / PR | Noi dung | Dieu kien merge |
|---|---|---|---|---|
| 1 | Core Setup & Architecture | `feature/core-setup-architecture` | Layered architecture, FastAPI app instance, `APIRouter`, lifespan events, routing, request handling, dependency injection, Pydantic v2 base schemas, config bang `pydantic-settings`, logging base | App skeleton chay duoc, Swagger/ReDoc mo duoc, health check pass |
| 2 | Database: SQLAlchemy 2.x & Alembic | `feature/database-alembic` | SQLAlchemy async, DB session dependency, model definition, relationships, `BaseRepository[T]`, async CRUD, pagination, Alembic migration, tich hop DB vao FastAPI | Migration tao schema thanh cong, repository CRUD co test co ban |
| 3 | Business Logic & Core Features | `feature/auth-user` | Register, login, refresh token, logout/revoke token, password hashing, JWT, `GET/PATCH /users/me`, change password | Auth flow pass qua API, Bearer auth dung trong docs |
| 4 | Business Logic & Core Features | `feature/workspace-rbac` | Workspace CRUD, invite/remove member, roles `OWNER/EDITOR/VIEWER`, `get_current_user`, role-based access control, resource ownership | Permission tests cho owner/editor/viewer pass |
| 5 | Business Logic & Core Features | `feature/project-management` | Project CRUD trong workspace, archive project, validate quyen truy cap workspace/project | Project API chi cho phep member hop le thao tac |
| 6 | Business Logic & Core Features | `feature/task-management` | Task CRUD, assign task cho member, chuyen status, set priority, due date, filtering theo status/priority/assignee, pagination | Task list filter + pagination dung, assign chi cho member hop le |
| 7 | Business Logic & Core Features | `feature/labels-comments-cache-notification` | Label CRUD, gan/bo label cho task, them/xoa comment, Redis cache cho task list, invalidate cache, background notification khi assign task | Cache hit/invalidate co test, notification background task duoc trigger |
| 8 | Review, Refactor & Optimization | `feature/review-refactor-optimization` | Middleware, exception handling, API documentation, Swagger/ReDoc Bearer auth, document error responses, performance review, refactor DRY, remove duplicate code | Error response thong nhat, docs day du, code quality pass |
| 9 | Final Stabilization / Delivery | `feature/final-hardening-docker-readme` | Dockerfile optional, docker-compose app + DB + Redis, README setup/env/docker compose, final regression test, ruff 100%, mypy no error | `docker compose up` chay duoc, README hoan chinh, full checks pass |

## Checklist moi ngay

1. Pull latest `main`.
2. Tao branch theo ten trong ke hoach.
3. Implement dung scope cua ngay do.
4. Them hoac cap nhat migration neu thay doi schema.
5. Them hoac cap nhat tests lien quan.
6. Chay local checks:
   - `ruff check .`
   - `mypy .`
   - test command cua project
7. Mo pull request.
8. Reviewer review.
9. Fix review comments.
10. Re-run checks.
11. Merge vao `main`.
12. Cap nhat trang thai ben duoi.

## Trang thai thuc hien

- [x] Day 1 - Core Setup & Architecture
- [x] Day 2 - Database: SQLAlchemy 2.x & Alembic
- [x] Day 3 - Auth & User
- [x] Day 4 - Workspace & RBAC
- [x] Day 5 - Project Management
- [x] Day 6 - Task Management
- [x] Day 7 - Labels, Comments, Cache, Notification
- [x] Day 8 - Review, Refactor & Optimization
- [ ] Day 9 - Final Hardening, Docker, README

## Ghi chu tiep tuc

- PDF goc la file scan, noi dung da duoc doc bang OCR nen co the co loi dau tieng Viet, nhung lich tren da bam theo cac module va feature chinh trong PDF.
- Khi bat dau implement that, doc lai `info.pdf` neu can doi chieu endpoint hoac acceptance criteria.
- Uu tien hoan thanh toi thieu features 1-8 va 11-12 trong PDF neu thoi gian bi cat giam.

