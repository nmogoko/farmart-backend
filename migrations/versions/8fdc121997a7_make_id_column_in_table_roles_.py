"""make id column in table roles  autoincrement

Revision ID: 8fdc121997a7
Revises: 63ddbd6be953
Create Date: 2024-11-15 22:02:02.036708

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8fdc121997a7'
down_revision = '63ddbd6be953'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE roles_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Roles', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('roles_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Roles', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS roles_id_seq")
