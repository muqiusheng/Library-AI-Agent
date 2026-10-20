from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c5c765a2d06'
down_revision: Union[str, None] = '3a5209ad7926'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
