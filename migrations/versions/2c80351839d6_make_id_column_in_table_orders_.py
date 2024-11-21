"""make id column in table Orders autogenerate

Revision ID: 2c80351839d6
Revises: 080f0b8a2044
Create Date: 2024-11-21 11:49:18.606836

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c80351839d6'
down_revision = '080f0b8a2044'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE orders_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Orders', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('orders_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Orders', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS orders_id_seq")