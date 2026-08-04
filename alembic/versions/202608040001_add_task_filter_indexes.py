"""add task filter indexes

Revision ID: 202608040001
Revises: 202607300001
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202608040001"
down_revision: str | None = "202607300001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_tasks_project_status",
        "tasks",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_priority",
        "tasks",
        ["project_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_assignee",
        "tasks",
        ["project_id", "assignee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_project_assignee", table_name="tasks")
    op.drop_index("ix_tasks_project_priority", table_name="tasks")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
