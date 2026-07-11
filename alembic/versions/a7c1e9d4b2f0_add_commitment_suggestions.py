"""add commitment_suggestions table (Story 5.6)

Revision ID: a7c1e9d4b2f0
Revises: e470256e035f
Create Date: 2026-07-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a7c1e9d4b2f0'
down_revision: Union[str, Sequence[str], None] = 'e470256e035f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'commitment_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('signature', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['localuser.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_commitment_suggestions_user_id'),
        'commitment_suggestions', ['user_id'], unique=False,
    )
    op.create_index(
        op.f('ix_commitment_suggestions_signature'),
        'commitment_suggestions', ['signature'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_commitment_suggestions_signature'), table_name='commitment_suggestions',
    )
    op.drop_index(
        op.f('ix_commitment_suggestions_user_id'), table_name='commitment_suggestions',
    )
    op.drop_table('commitment_suggestions')
