from alembic import op
from app.services.jobs import JobControl

revision = "0006"
down_revision = "0005"


def upgrade():
    JobControl.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    JobControl.__table__.drop(op.get_bind(), checkfirst=True)
