"""make id column in table farmersprofile autogenerate

Revision ID: 305f525c6d85
Revises: 8fdc121997a7
Create Date: 2024-11-17 15:43:50.398516

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '305f525c6d85'
down_revision = '8fdc121997a7'
branch_labels = None
depends_on = None

def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE farmers_profile_id_seq")

    # Alter the column to use the sequence
    op.alter_column('FarmersProfile', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('farmers_profile_id_seq')"))



def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('FarmersProfile', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS farmers_profile_id_seq")