"""Track availability in the last successful source snapshot."""
from alembic import op
import sqlalchemy as sa

revision = '9c03bc671a20'
down_revision = '4e64820b13ce'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('events', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column('events', 'is_active')
