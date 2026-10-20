"""add super administrator role

Revision ID: 9b6f3a2d1c44
Revises: 37071af904d4
Create Date: 2026-07-26 18:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "9b6f3a2d1c44"
down_revision: str | None = "37071af904d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'super_admin' WHERE role = 'admin'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
