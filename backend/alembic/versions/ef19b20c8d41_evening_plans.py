"""Store personal evening routes independently of event reactions."""

from alembic import op
import sqlalchemy as sa

revision = "ef19b20c8d41"
down_revision = "9c03bc671a20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evening_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evening_plans_user_id", "evening_plans", ["user_id"])


def downgrade():
    op.drop_index("ix_evening_plans_user_id", table_name="evening_plans")
    op.drop_table("evening_plans")
