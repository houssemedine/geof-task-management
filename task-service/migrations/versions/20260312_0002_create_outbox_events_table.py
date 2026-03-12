"""create outbox_events table

Revision ID: 20260312_0002
Revises: 20260312_0001
Create Date: 2026-03-12 16:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260312_0002"
down_revision: str | None = "20260312_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

outbox_status_enum = postgresql.ENUM(
    "pending",
    "published",
    "failed",
    name="outbox_status",
    create_type=False,
)


def upgrade() -> None:
    """Applique la migration vers la version cible."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        outbox_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("routing_key", sa.String(length=128), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "status",
            outbox_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("event_id", name="uq_outbox_events_event_id"),
    )
    op.create_index("ix_outbox_events_event_id", "outbox_events", ["event_id"], unique=False)
    op.create_index(
        "ix_outbox_events_status_available_at",
        "outbox_events",
        ["status", "available_at"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"], unique=False
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"], unique=False)


def downgrade() -> None:
    """Annule la migration vers la version précédente."""
    bind = op.get_bind()

    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status_available_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_id", table_name="outbox_events")
    op.drop_table("outbox_events")

    if bind.dialect.name == "postgresql":
        outbox_status_enum.drop(bind, checkfirst=True)
