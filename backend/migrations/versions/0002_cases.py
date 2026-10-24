"""Add cases without rewriting or deleting historical investigations."""

from alembic import op
from app.models.cases import Case, CaseAsset, CaseEvent

revision = "0002"
down_revision = "0001"


def upgrade():
    for table in (Case.__table__, CaseAsset.__table__, CaseEvent.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in (CaseEvent.__table__, CaseAsset.__table__, Case.__table__):
        table.drop(op.get_bind(), checkfirst=True)
