"""Make id column in table CallbackMetadatum autogenerate

Revision ID: cdd303922e15
Revises: 84b17844f80b
Create Date: 2024-11-14 23:59:27.209993

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cdd303922e15'
down_revision = '84b17844f80b'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE callbackmetadatum_id_seq")

    # Alter the column to use the sequence
    op.alter_column('CallbackMetadata', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('callbackmetadatum_id_seq')"))

def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('CallbackMetadata', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS callbackmetadatum_id_seq")
