"""make id column in table users autoincrement

Revision ID: 059e013d85ae
Revises: cdd303922e15
Create Date: 2024-11-15 22:01:09.551560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '059e013d85ae'
down_revision = 'cdd303922e15'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE users_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Users', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('users_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Users', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS users_id_seq")
