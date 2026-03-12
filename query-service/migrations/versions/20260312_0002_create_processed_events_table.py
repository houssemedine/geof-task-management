"""create processed_events table

Revision ID: 20260312_0002
Revises: 20260312_0001
Create Date: 2026-03-12 16:20:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260312_0002"
down_revision: str | None = "20260312_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration vers la version cible."""
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_processed_events_event_type", "processed_events", ["event_type"], unique=False
    )


def downgrade() -> None:
    """Annule la migration vers la version précédente."""
    op.drop_index("ix_processed_events_event_type", table_name="processed_events")
    op.drop_table("processed_events")
