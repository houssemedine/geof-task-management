"""create tasks table

Revision ID: 20260312_0001
Revises:
Create Date: 2026-03-12 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260312_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


task_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "done",
    name="task_status",
    create_type=False,
)
task_priority_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    name="task_priority",
    create_type=False,
)


def upgrade() -> None:
    """Applique la migration vers la version cible."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        task_status_enum.create(bind, checkfirst=True)
        task_priority_enum.create(bind, checkfirst=True)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            task_status_enum,
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            task_priority_enum,
            nullable=False,
            server_default="medium",
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"], unique=False)


def downgrade() -> None:
    """Annule la migration vers la version précédente."""
    bind = op.get_bind()

    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")

    if bind.dialect.name == "postgresql":
        task_priority_enum.drop(bind, checkfirst=True)
        task_status_enum.drop(bind, checkfirst=True)
