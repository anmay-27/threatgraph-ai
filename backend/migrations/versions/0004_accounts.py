from alembic import op
from app.services.auth import Account, LoginSession, AnalysisOwner

revision = "0004"
down_revision = "0003"


def upgrade():
    for table in (Account.__table__, LoginSession.__table__, AnalysisOwner.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in (AnalysisOwner.__table__, LoginSession.__table__, Account.__table__):
        table.drop(op.get_bind(), checkfirst=True)
