"""Add dataset content orientation and optional matching score."""

import sqlalchemy as sa
from alembic import op

revision = "c8d21f63a710"
down_revision = "a74d192f0b31"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("books", sa.Column("content_orientation", sa.String(16), nullable=True))
    op.create_check_constraint(
        op.f("ck_books_content_orientation_values"),
        "books",
        "content_orientation IN ('theory', 'balanced', 'practice')",
    )
    op.add_column(
        "recommendation_items", sa.Column("orientation_score", sa.Numeric(5, 2), nullable=True)
    )


def downgrade():
    op.drop_column("recommendation_items", "orientation_score")
    op.drop_constraint(op.f("ck_books_content_orientation_values"), "books", type_="check")
    op.drop_column("books", "content_orientation")
