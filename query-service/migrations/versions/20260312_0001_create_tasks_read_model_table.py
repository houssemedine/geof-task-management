"""create tasks_read_model table

Revision ID: 20260312_0001
Revises:
Create Date: 2026-03-12 13:20:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260312_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration vers la version cible."""
    op.create_table(
        "tasks_read_model",
        sa.Column("task_id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
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
        sa.Column(
            "last_event_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_tasks_read_model_status", "tasks_read_model", ["status"], unique=False)
    op.create_index("ix_tasks_read_model_priority", "tasks_read_model", ["priority"], unique=False)
    op.create_index(
        "ix_tasks_read_model_assigned_to",
        "tasks_read_model",
        ["assigned_to"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_read_model_updated_at",
        "tasks_read_model",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Annule la migration vers la version précédente."""
    op.drop_index("ix_tasks_read_model_updated_at", table_name="tasks_read_model")
    op.drop_index("ix_tasks_read_model_assigned_to", table_name="tasks_read_model")
    op.drop_index("ix_tasks_read_model_priority", table_name="tasks_read_model")
    op.drop_index("ix_tasks_read_model_status", table_name="tasks_read_model")
    op.drop_table("tasks_read_model")
