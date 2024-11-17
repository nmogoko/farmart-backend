"""Make id column in table Cart autogenerate

Revision ID: d7a25810c7cc
Revises: cdd303922e15
Create Date: 2024-11-15 20:02:53.624039

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7a25810c7cc'
down_revision = 'cdd303922e15'
branch_labels = None
depends_on = None


def upgrade():
    # Create the sequence
    op.execute("CREATE SEQUENCE cart_id_seq")

    # Alter the column to use the sequence
    op.alter_column('Cart', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=sa.text("nextval('cart_id_seq')"))


def downgrade():
    # Optionally remove the default if necessary
    op.alter_column('Cart', 'id', 
                    existing_type=sa.Integer(), 
                    existing_nullable=False, 
                    server_default=None)

    # Drop the sequence in downgrade
    op.execute("DROP SEQUENCE IF EXISTS cart_id_seq")
