"""Support provider-scoped identities for the Telegram migration.

Revision ID: c5a7e21d64b9
Revises: ef19b20c8d41
"""

import sqlalchemy as sa

from alembic import op


revision = "c5a7e21d64b9"
down_revision = "ef19b20c8d41"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("identity_provider", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("external_user_id", sa.BigInteger(), nullable=True)
        )

    op.execute(
        sa.text(
            "UPDATE users SET identity_provider = 'max', external_user_id = max_user_id"
        )
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("identity_provider", nullable=False)
        batch_op.alter_column("external_user_id", nullable=False)
        batch_op.drop_index("ix_users_max_user_id")
        batch_op.drop_column("max_user_id")
        batch_op.create_unique_constraint(
            "uq_users_identity", ["identity_provider", "external_user_id"]
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("max_user_id", sa.BigInteger(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE users SET max_user_id = external_user_id "
            "WHERE identity_provider = 'max'"
        )
    )
    # Telegram identities cannot be represented in the legacy MAX-only schema.
    op.execute(sa.text("DELETE FROM users WHERE identity_provider <> 'max'"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_identity", type_="unique")
        batch_op.drop_column("identity_provider")
        batch_op.drop_column("external_user_id")
        batch_op.alter_column("max_user_id", nullable=False)
        batch_op.create_index("ix_users_max_user_id", ["max_user_id"], unique=True)
