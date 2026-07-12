"""merge insights dismiss lifecycle with commitment suggestions and reasoning

Revision ID: 1598ad304eb1
Revises: 5df0e3b5340d, a7c1e9d4b2f0
Create Date: 2026-07-11 17:43:10.240895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1598ad304eb1'
down_revision: Union[str, Sequence[str], None] = ('5df0e3b5340d', 'a7c1e9d4b2f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
