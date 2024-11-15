"""Make id column in table Transactions autogenerate

Revision ID: 84b17844f80b
Revises: 452cef9cf700
Create Date: 2024-11-14 23:53:53.595798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84b17844f80b'
down_revision = '452cef9cf700'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE transactions_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Transactions', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('transactions_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Transactions', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS transactions_id_seq")
