"""Ajout de calculated_hash et modification agent_deposit_path_template

Revision ID: 00e32758568b
Revises: cab26e4373c0
Create Date: 2025-06-17 20:27:43.326287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00e32758568b'
down_revision: Union[str, None] = 'cab26e4373c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
