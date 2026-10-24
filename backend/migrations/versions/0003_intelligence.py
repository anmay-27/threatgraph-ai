from alembic import op
from app.models.intelligence import Entity, AnalysisEntity

revision = "0003"
down_revision = "0002"


def upgrade():
    for table in (Entity.__table__, AnalysisEntity.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in (AnalysisEntity.__table__, Entity.__table__):
        table.drop(op.get_bind(), checkfirst=True)
