"""Rename column user_id and farmer_id it table Notifications

Revision ID: a93b8e1b222e
Revises: 2c80351839d6
Create Date: 2024-11-21 12:04:22.276975

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a93b8e1b222e'
down_revision = '2c80351839d6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('Notification', 'sender_id', user_id='user_id')
    op.alter_column('Notification', 'receiver_id', farmer_id='farmer_id')


def downgrade():
    op.alter_column('Notification', 'user_id', user_id='sender_id')
    # Rename new_column2 back to old_column2
    op.alter_column('Notification', 'farmer_id', farmer_id='receiver_id')
