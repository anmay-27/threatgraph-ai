"""Server-side Google authorization-code login. Never automatically link by email."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import String, DateTime, ForeignKey, select, delete
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.models.database import Base, Session
from app.services.auth import router, Account, LoginSession, password_hash


class GoogleIdentity(Base):
    __tablename__ = 'google_identities'
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('accounts.id', ondelete='CASCADE'), unique=True)


class OAuthAttempt(Base):
    __tablename__ = 'oauth_attempts'
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    verifier: Mapped[str] = mapped_column(String(128))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def enabled():
    return bool(settings.auth_required and settings.google_client_id and settings.google_client_secret)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def finish(error=None):
    response = RedirectResponse('/' + ('?auth_error=' + error if error else ''), status_code=303)
    response.delete_cookie('tg_oauth', path='/api/v1/auth/google')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('/providers')
def providers():
    return {'google': enabled()}


@router.get('/google/start')
def start():
    if not enabled():
        raise HTTPException(503, 'Google sign-in has not been configured')
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    with Session() as db:
        db.execute(delete(OAuthAttempt).where(OAuthAttempt.expires < datetime.now(timezone.utc)))
        db.add(OAuthAttempt(state_hash=digest(state), verifier=verifier, expires=datetime.now(timezone.utc)+timedelta(minutes=10)))
        db.commit()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    response = RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': settings.google_client_id, 'redirect_uri': settings.google_redirect_uri,
        'response_type': 'code', 'scope': 'openid email', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account',
    }))
    response.set_cookie('tg_oauth', state, httponly=True, secure=settings.secure_cookies,
                        samesite='lax', max_age=600, path='/api/v1/auth/google')
    response.headers['Cache-Control'] = 'no-store'
    return response


async def google_profile(code, verifier):
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        token = await client.post('https://oauth2.googleapis.com/token', data={
            'code': code, 'client_id': settings.google_client_id,
            'client_secret': settings.google_client_secret, 'redirect_uri': settings.google_redirect_uri,
            'grant_type': 'authorization_code', 'code_verifier': verifier,
        })
        token.raise_for_status()
        access = token.json()['access_token']
        profile = await client.get('https://openidconnect.googleapis.com/v1/userinfo',
                                   headers={'Authorization': 'Bearer ' + access})
        profile.raise_for_status()
        return profile.json()


@router.get('/google/callback')
async def callback(request: Request, state: str = '', code: str = '', error: str = ''):
    if not enabled():
        return finish('unavailable')
    cookie = request.cookies.get('tg_oauth', '')
    if not state or not cookie or not hmac.compare_digest(digest(state), digest(cookie)):
        return finish('expired')
    with Session() as db:
        # Atomic consumption prevents replay, including concurrent callbacks.
        attempt = db.execute(delete(OAuthAttempt).where(OAuthAttempt.state_hash == digest(state)).returning(OAuthAttempt.verifier, OAuthAttempt.expires)).first()
        db.commit()
    if not attempt or attempt.expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return finish('expired')
    if error or not code:
        return finish('cancelled')
    try:
        profile = await google_profile(code, attempt.verifier)
        subject, email = profile.get('sub'), profile.get('email', '').strip().lower()
        if not isinstance(subject, str) or not subject or len(subject)>255 or profile.get('email_verified') is not True or not email or len(email)>254:
            return finish('unverified')
        with Session() as db:
            identity = db.get(GoogleIdentity, subject)
            account = db.get(Account, identity.account_id) if identity else None
            if not account:
                if db.scalar(select(Account).where(Account.email == email)):
                    return finish('existing_account')
                # Random, discarded password prevents password login to Google-only accounts.
                account = Account(email=email, password_hash=password_hash(secrets.token_urlsafe(64)), role='USER')
                db.add(account)
                db.flush()
                db.add(GoogleIdentity(subject=subject, account_id=account.id))
            token = secrets.token_urlsafe(32)
            db.add(LoginSession(token_hash=digest(token), account_id=account.id, expires=datetime.now(timezone.utc)+timedelta(hours=12)))
            db.commit()
        response = finish()
        response.set_cookie('tg_session', token, httponly=True, secure=settings.secure_cookies,
                            samesite='strict', max_age=43200, path='/')
        return response
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, IntegrityError):
        return finish('unavailable')
