"""insights dismiss lifecycle columns

Revision ID: 5df0e3b5340d
Revises: 31751a886cde
Create Date: 2026-07-11 12:18:35.249646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5df0e3b5340d'
down_revision: Union[str, Sequence[str], None] = '31751a886cde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills any pre-existing rows so the NOT NULL columns below can be
    # added in one step (table is empty pre-launch, but this is safe either way).
    # batch_alter_table mirrors the existing migration file's SQLite-safe pattern exactly.
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'effect', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''
            )
        )
        batch_op.add_column(
            sa.Column(
                'severity',
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default='important',
            )
        )
        batch_op.add_column(
            sa.Column('metric_value', sa.Numeric(precision=12, scale=2), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'dedup_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''
            )
        )
        batch_op.add_column(sa.Column('dismissed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.drop_column('dismissed_at')
        batch_op.drop_column('dedup_key')
        batch_op.drop_column('metric_value')
        batch_op.drop_column('severity')
        batch_op.drop_column('effect')
