"""make id column in table animals autogenerate

Revision ID: e6d7a8391e2e
Revises: d182b7a3ab20
Create Date: 2024-11-19 23:06:15.193499

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6d7a8391e2e'
down_revision = 'd182b7a3ab20'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE animals_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Animals', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('animals_id_seq')"))



def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Animals', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS animals_id_seq")
