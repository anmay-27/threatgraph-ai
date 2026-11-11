from alembic import op
from app.services.google_auth import GoogleIdentity, OAuthAttempt

revision = '0007'
down_revision = '0006'


def upgrade():
    GoogleIdentity.__table__.create(op.get_bind(), checkfirst=True)
    OAuthAttempt.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    OAuthAttempt.__table__.drop(op.get_bind(), checkfirst=True)
    GoogleIdentity.__table__.drop(op.get_bind(), checkfirst=True)
