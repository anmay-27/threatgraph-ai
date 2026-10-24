from alembic import op
from app.services.feedback import Feedback

revision = "0005"
down_revision = "0004"


def upgrade():
    Feedback.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    Feedback.__table__.drop(op.get_bind(), checkfirst=True)
