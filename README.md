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


## Day 2 Scope

- SQLAlchemy 2.x async engine and session factory.
- Database session dependency for FastAPI routes/services.
- Alembic configuration and initial schema migration.
- Models and relationships for User, Workspace, WorkspaceMember, Project, Task, Label, TaskLabel, Comment, and Notification.
- Generic `BaseRepository[T]` with async CRUD and pagination.
- Repository test using SQLite async.


## Day 3 Scope

- User registration with unique normalized email.
- Login with password verification and JWT access/refresh tokens.
- Refresh token rotation with database-backed revocation.
- Logout by revoking refresh tokens.
- Bearer-protected `GET /api/v1/users/me` profile endpoint.
- `PATCH /api/v1/users/me` profile updates.
- `POST /api/v1/users/me/change-password` with refresh token revocation.
- OpenAPI HTTP Bearer auth scheme for protected endpoints.

## Day 4 Scope

- Workspace CRUD under `/api/v1/workspaces`.
- Workspace owner membership is created automatically when a workspace is created.
- Workspace member invite, list, role update, and remove endpoints.
- RBAC for workspace roles: `OWNER`, `EDITOR`, and `VIEWER`.
- Members can read workspaces, `OWNER`/`EDITOR` can update workspaces, and only `OWNER` can manage members or delete workspaces.
- Workspace owner membership cannot be removed or downgraded through member management.

## Day 5 Scope

- Project CRUD under `/api/v1/workspaces/{workspace_id}/projects` and `/api/v1/projects/{project_id}`.
- Archive project endpoint at `POST /api/v1/projects/{project_id}/archive`.
- Workspace RBAC applies to project access: members can read projects, `OWNER`/`EDITOR` can create, update, archive, and delete projects.
- Non-members cannot access projects in a workspace.

## Day 6 Scope

- Task CRUD under `/api/v1/projects/{project_id}/tasks` and `/api/v1/tasks/{task_id}`.
- Task create/update supports assignee, status, priority, description, and due date.
- Task list supports filtering by `status`, `priority`, and `assignee_id`.
- Task list returns pagination metadata: `items`, `total`, `page`, `limit`, and `pages`.
- Workspace RBAC applies to task access: members can read tasks, `OWNER`/`EDITOR` can create, update, and delete tasks.
- Task assignees must be members of the task project workspace.
## Database

Default local database URL:

```text
sqlite+aiosqlite:///./taskhub.db
```

Override with `DATABASE_URL` in `.env` for MySQL/PostgreSQL later.

Auth-related settings:

```text
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Run migration SQL preview:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

Run migrations against the configured database:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
## Local Development

Create a virtual environment, install dependencies, and run the app:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
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

