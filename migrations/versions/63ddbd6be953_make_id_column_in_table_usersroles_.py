"""make id column in table usersroles  autoincrement

Revision ID: 63ddbd6be953
Revises: 059e013d85ae
Create Date: 2024-11-15 22:01:41.069798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63ddbd6be953'
down_revision = '059e013d85ae'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE users_roles_id_seq")

    # Alter the column to use the sequence
    op.alter_column('UsersRoles', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('users_roles_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('UsersRoles', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS users_roles_id_seq")

