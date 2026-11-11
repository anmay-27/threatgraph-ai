from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, requests
from app.core.config import settings
from app.models.database import Session
from app.services import google_auth as oauth
from app.services.auth import Account, password_hash


def test_google_login_security_and_persistence(monkeypatch):
    monkeypatch.setattr(settings, 'auth_required', True)
    monkeypatch.setattr(settings, 'google_client_id', 'test-client')
    monkeypatch.setattr(settings, 'google_client_secret', 'test-secret')
    subject = uuid4().hex
    email = subject + '@gmail.com'
    profile = {'sub': subject, 'email': email, 'email_verified': True}
    calls = []
    async def provider(code, verifier):
        calls.append((code, verifier))
        return profile
    monkeypatch.setattr(oauth, 'google_profile', provider)
    with TestClient(app) as client:
        requests.clear()
        assert client.get('/api/v1/auth/providers').json() == {'google': True}
        def start():
            response = client.get('/api/v1/auth/google/start', follow_redirects=False)
            params = parse_qs(urlparse(response.headers['location']).query)
            assert params['scope'] == ['openid email']
            assert params['code_challenge_method'] == ['S256']
            assert 'test-secret' not in response.headers['location']
            assert 'HttpOnly' in response.headers['set-cookie']
            return params['state'][0]
        def callback(state, **params):
            return client.get('/api/v1/auth/google/callback', params={'state': state, 'code': 'test-code', **params}, follow_redirects=False)
        state = start()
        assert 'expired' in callback('wrong-state').headers['location']
        assert not calls
        state = start()
        assert callback(state).headers['location'] == '/'
        account = client.get('/api/v1/auth/me').json()
        assert account['email'] == email and account['role'] == 'USER'
        assert client.get('/api/v1/admin/users').status_code == 403
        assert client.post('/api/v1/auth/logout').status_code == 200
        assert client.get('/api/v1/auth/me').status_code == 401
        client.cookies.set('tg_oauth', state)
        assert 'expired' in callback(state).headers['location']
        client.cookies.clear()
        state = start()
        assert callback(state).headers['location'] == '/'
        assert client.get('/api/v1/auth/me').json()['id'] == account['id']
        client.post('/api/v1/auth/logout')
        state = start()
        assert 'cancelled' in callback(state, error='access_denied').headers['location']
        state = start()
        with Session() as db:
            db.get(oauth.OAuthAttempt, oauth.digest(state)).expires = datetime.now(timezone.utc)-timedelta(seconds=1)
            db.commit()
        assert 'expired' in callback(state).headers['location']
        profile['email_verified'] = False
        assert 'unverified' in callback(start()).headers['location']
        profile.update(sub=uuid4().hex, email_verified=True)
        assert 'existing_account' in callback(start()).headers['location']
        assert client.get('/api/v1/auth/me').status_code == 401
        async def failed(*args):
            raise httpx.ConnectError('network failure')
        monkeypatch.setattr(oauth, 'google_profile', failed)
        assert 'unavailable' in callback(start()).headers['location']
        monkeypatch.setattr(settings, 'google_client_secret', '')
        assert client.get('/api/v1/auth/providers').json() == {'google': False}
        assert client.get('/api/v1/auth/google/start').status_code == 503


def test_google_token_exchange_uses_fixed_endpoints(monkeypatch):
    import asyncio
    seen = []
    async def handler(request):
        seen.append(request)
        if request.url.path == '/token':
            assert b'code_verifier=verifier' in request.content
            return httpx.Response(200, json={'access_token': 'provider-token'})
        assert request.headers['authorization'] == 'Bearer provider-token'
        return httpx.Response(200, json={'sub': 'subject', 'email_verified': True})
    original = httpx.AsyncClient
    monkeypatch.setattr(oauth.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    assert asyncio.run(oauth.google_profile('code', 'verifier'))['sub'] == 'subject'
    assert [r.url.host for r in seen] == ['oauth2.googleapis.com', 'openidconnect.googleapis.com']
