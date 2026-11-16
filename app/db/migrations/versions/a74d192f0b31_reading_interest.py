"""Separate reading interest from progress and add historical popularity events."""

import sqlalchemy as sa
from alembic import op

revision = "a74d192f0b31"
down_revision = "5c5c765a2d06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_interests",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "book_id", sa.Uuid(), sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reading_interest_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "book_id", sa.Uuid(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_interest_events_time_book_user",
        "reading_interest_events",
        ["created_at", "book_id", "user_id"],
    )
    op.create_index(
        "ix_interest_events_book_time", "reading_interest_events", ["book_id", "created_at"]
    )
    # Preserve explicit personal interest, without manufacturing historical events.
    op.execute("""
        INSERT INTO reading_interests (user_id, book_id, active, added_at, created_at, updated_at)
        SELECT user_id, book_id, TRUE, updated_at, created_at, updated_at
        FROM book_user_states WHERE state = 'want_to_read'
    """)
    op.execute("UPDATE book_user_states SET state = 'not_started' WHERE state = 'want_to_read'")
    op.execute("UPDATE learning_path_books SET state = 'not_started' WHERE state = 'want_to_read'")
    # Merge both old sources; completed takes precedence, then reading, then not_started.
    op.execute("""
        INSERT INTO book_user_states (user_id, book_id, state, created_at, updated_at)
        SELECT user_id, book_id,
               CASE MAX(weight) WHEN 2 THEN 'completed' WHEN 1 THEN 'reading'
                    ELSE 'not_started' END, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM (
            SELECT user_id, book_id,
                   CASE state WHEN 'completed' THEN 2 WHEN 'reading' THEN 1 ELSE 0 END AS weight
            FROM book_user_states
            UNION ALL
            SELECT p.user_id, b.book_id,
                   CASE b.state WHEN 'completed' THEN 2 WHEN 'reading' THEN 1 ELSE 0 END
            FROM learning_path_books b
            JOIN learning_path_stages s ON s.id = b.stage_id
            JOIN learning_paths p ON p.id = s.path_id
        ) old_states GROUP BY user_id, book_id
        ON CONFLICT (user_id, book_id) DO UPDATE SET state = EXCLUDED.state,
                                                    updated_at = EXCLUDED.updated_at
    """)
    op.execute("""
        UPDATE learning_path_books b SET state = u.state
        FROM learning_path_stages s, learning_paths p, book_user_states u
        WHERE s.id = b.stage_id AND p.id = s.path_id
          AND u.user_id = p.user_id AND u.book_id = b.book_id
    """)
    op.execute("""
        UPDATE learning_paths p SET progress = stats.progress,
            status = CASE WHEN p.status = 'archived' THEN 'archived'
                          WHEN stats.progress = 100 THEN 'completed'
                          WHEN p.status = 'completed' OR stats.started THEN 'active'
                          ELSE p.status END
        FROM (
            SELECT s.path_id,
                   ROUND(100.0 * COUNT(*) FILTER (WHERE b.state = 'completed') / COUNT(*), 2)
                       AS progress,
                   BOOL_OR(b.state <> 'not_started') AS started
            FROM learning_path_stages s JOIN learning_path_books b ON b.stage_id = s.id
            GROUP BY s.path_id
        ) stats WHERE stats.path_id = p.id
    """)


def downgrade() -> None:
    op.execute("UPDATE book_user_states SET state = 'want_to_read' WHERE state = 'not_started'")
    op.execute("UPDATE learning_path_books SET state = 'want_to_read' WHERE state = 'not_started'")
    op.drop_table("reading_interest_events")
    op.drop_table("reading_interests")
