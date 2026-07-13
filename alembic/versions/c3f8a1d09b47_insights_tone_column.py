"""insights tone column (watch | win)

Adds the second, orthogonal axis to `insights`. `severity` answers "how urgent is this?" and
structurally cannot express "this is good news" -- a win has no criticality -- so the positive
detectors (Subscription ended / Commitments covered / Spending pace improved) need their own
field rather than a fourth `severity` value that would corrupt the tier ordering.

Revision ID: c3f8a1d09b47
Revises: 1598ad304eb1
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1d09b47'
down_revision: Union[str, Sequence[str], None] = '1598ad304eb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='watch' backfills every pre-existing row: an insight written before this
    # column existed was, by definition, one of the five FR-8.1 warnings. Without the default
    # they would come back NULL and the page would have to guess.
    # batch_alter_table mirrors the SQLite-safe pattern the other insights migrations use.
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'tone',
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default='watch',
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.drop_column('tone')
