# TaskHub

TaskHub là API quản lý công việc được xây dựng bằng FastAPI, dùng làm ứng dụng mẫu cho kế hoạch triển khai 9 ngày trong `implementation_plan_9_days.md`.

## Phạm vi Day 1

- Cấu trúc dự án FastAPI theo kiến trúc phân lớp.
- App factory và instance ứng dụng FastAPI.
- Router API có version dưới `/api/v1`.
- Hook khởi động/tắt ứng dụng bằng lifespan.
- Điểm vào dependency injection cho cấu hình.
- Schema nền tảng bằng Pydantic v2.
- Cấu hình theo biến môi trường với `pydantic-settings`.
- Định dạng response lỗi chuẩn.
- Cấu hình logging.
- Endpoint kiểm tra health check.

## Phạm vi Day 2

- Async engine và session factory với SQLAlchemy 2.x.
- Dependency database session cho route/service FastAPI.
- Cấu hình Alembic và migration schema ban đầu.
- Model và relationship cho User, Workspace, WorkspaceMember, Project, Task, Label, TaskLabel, Comment, và Notification.
- `BaseRepository[T]` generic hỗ trợ async CRUD và phân trang.
- Test repository dùng SQLite async.

## Phạm vi Day 3

- Đăng ký người dùng với email duy nhất và được chuẩn hóa.
- Đăng nhập với kiểm tra mật khẩu và JWT access/refresh token.
- Xoay vòng refresh token với cơ chế thu hồi lưu trong database.
- Đăng xuất bằng cách thu hồi refresh token.
- Endpoint hồ sơ `GET /api/v1/users/me` được bảo vệ bằng Bearer token.
- Cập nhật hồ sơ qua `PATCH /api/v1/users/me`.
- Đổi mật khẩu qua `POST /api/v1/users/me/change-password` kèm thu hồi refresh token.
- OpenAPI HTTP Bearer auth scheme cho các endpoint được bảo vệ.

## Phạm vi Day 4

- CRUD Workspace dưới `/api/v1/workspaces`.
- Membership owner được tạo tự động khi workspace được tạo.
- Endpoint mời thành viên, liệt kê thành viên, cập nhật role, và xóa thành viên khỏi workspace.
- RBAC cho các role workspace: `OWNER`, `EDITOR`, và `VIEWER`.
- Thành viên có thể đọc workspace, `OWNER`/`EDITOR` có thể cập nhật workspace, và chỉ `OWNER` có thể quản lý thành viên hoặc xóa workspace.
- Membership owner của workspace không thể bị xóa hoặc hạ quyền thông qua chức năng quản lý thành viên.

## Phạm vi Day 5

- CRUD Project dưới `/api/v1/workspaces/{workspace_id}/projects` và `/api/v1/projects/{project_id}`.
- Endpoint archive project tại `POST /api/v1/projects/{project_id}/archive`.
- RBAC của workspace được áp dụng cho quyền truy cập project: thành viên có thể đọc project, `OWNER`/`EDITOR` có thể tạo, cập nhật, archive, và xóa project.
- Người không phải thành viên không thể truy cập project trong workspace.

## Phạm vi Day 6

- CRUD Task dưới `/api/v1/projects/{project_id}/tasks` và `/api/v1/tasks/{task_id}`.
- Tạo/cập nhật task hỗ trợ assignee, status, priority, description, và due date.
- Danh sách task hỗ trợ lọc theo `status`, `priority`, và `assignee_id`.
- Danh sách task trả về metadata phân trang: `items`, `total`, `page`, `limit`, và `pages`.
- RBAC của workspace được áp dụng cho quyền truy cập task: thành viên có thể đọc task, `OWNER`/`EDITOR` có thể tạo, cập nhật, và xóa task.
- Người được assign task phải là thành viên của workspace chứa project của task.

## Phạm vi Day 7

- CRUD label theo project và gán/gỡ label cho task.
- Tạo, liệt kê, và xóa comment trên task theo quyền truy cập.
- Cơ chế Redis cache-aside cho danh sách task đã lọc, kèm invalidate cache khi có thay đổi ghi.
- Background notification khi task được assign cho thành viên workspace.

## Phạm vi Day 8

- Middleware request context với request ID, thời gian xử lý, request logging, và security headers.
- Response JSON thống nhất cho lỗi ứng dụng, HTTP, validation, và lỗi ngoài dự kiến.
- Tài liệu OpenAPI đầy đủ với tags, HTTP Bearer authentication, và schema response lỗi dùng chung.
- Chính sách truy cập workspace tập trung, được tái sử dụng bởi các service workspace, project, task, label, và comment.
- Composite database indexes cho bộ lọc task theo status, priority, và assignee trong một project.

## Phạm vi Day 9

- Dockerfile cho ứng dụng FastAPI.
- Docker Compose stack cho API, PostgreSQL 16, và Redis 7.
- Container khởi động sẽ chạy Alembic migrations trước khi nhận traffic.
- README có hướng dẫn setup, biến môi trường, Docker, và kiểm tra chất lượng.

## Database

URL database mặc định khi chạy local:

```text
sqlite+aiosqlite:///./taskhub.db
```

Có thể override bằng `DATABASE_URL` trong file `.env` nếu muốn dùng MySQL/PostgreSQL.

Các cấu hình liên quan đến auth:

```text
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379/0
TASK_LIST_CACHE_TTL_SECONDS=60
```

URL database/cache khi chạy bằng Docker Compose:

```text
DATABASE_URL=postgresql+asyncpg://taskhub:taskhub@db:5432/taskhub
REDIS_URL=redis://redis:6379/0
```

Xem trước SQL migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

Chạy migration trên database đang cấu hình:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Phát triển local

Tạo virtual environment, cài dependencies, và chạy ứng dụng:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Mở các URL sau:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/api/v1/health`

## Docker Compose

Khởi động toàn bộ stack:

```powershell
docker compose up --build
```

API container sẽ chờ PostgreSQL sẵn sàng, chạy `alembic upgrade head`, rồi khởi động Uvicorn trên port `8000`.

Mở các URL sau:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/api/v1/health`

Dừng stack:

```powershell
docker compose down
```

Xóa volume PostgreSQL và Redis đã lưu khi cần môi trường sạch:

```powershell
docker compose down --volumes
```

## Kiểm tra chất lượng

```powershell
pytest
mypy .
ruff check .
```