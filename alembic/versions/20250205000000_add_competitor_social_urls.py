"""Add competitor social URLs (twitter, instagram, facebook, reddit, discord).

Revision ID: 20250205000000
Revises:
Create Date: 2025-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250205000000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("competitors", sa.Column("twitter_url", sa.String(512), nullable=True))
    op.add_column("competitors", sa.Column("instagram_url", sa.String(512), nullable=True))
    op.add_column("competitors", sa.Column("facebook_url", sa.String(512), nullable=True))
    op.add_column("competitors", sa.Column("reddit_url", sa.String(512), nullable=True))
    op.add_column("competitors", sa.Column("discord_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("competitors", "discord_url")
    op.drop_column("competitors", "reddit_url")
    op.drop_column("competitors", "facebook_url")
    op.drop_column("competitors", "instagram_url")
    op.drop_column("competitors", "twitter_url")
