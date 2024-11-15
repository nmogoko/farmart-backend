"""Make id column in table requests autogenerate

Revision ID: 452cef9cf700
Revises: 
Create Date: 2024-11-14 22:03:18.014317

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '452cef9cf700'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE requests_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Requests', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('requests_id_seq')"))



def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Requests', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS requests_id_seq")