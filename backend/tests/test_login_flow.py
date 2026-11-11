from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, requests
from app.core.config import settings
from app.models.database import Session
from app.services.auth import Account, LoginSession

def test_credentials_sessions_and_admin_exclusion(monkeypatch):
    monkeypatch.setattr(settings,'auth_required',True)
    credentials={'email':f'{uuid4().hex}@example.test','password':'a-long-private-test-passphrase'}
    with TestClient(app) as client:
        requests.clear()
        assert client.post('/api/v1/auth/register',json={**credentials,'password':'short'}).status_code==422
        assert client.post('/api/v1/auth/register',json={**credentials,'email':'bad@address'}).status_code==422
        assert client.post('/api/v1/auth/register',json={**credentials,'role':'ADMIN'}).status_code==201
        assert client.post('/api/v1/auth/register',json=credentials).status_code==409
        with Session() as db:
            account=db.scalar(select(Account).where(Account.email==credentials['email']))
            assert account.role=='USER'
            assert account.password_hash!=credentials['password']
            assert credentials['password'] not in account.password_hash
        assert client.post('/api/v1/auth/login',json={**credentials,'password':'incorrect-passphrase'}).status_code==401
        result=client.post('/api/v1/auth/login',json=credentials)
        assert result.status_code==200
        assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=strict' in result.headers['set-cookie']
        cookie=client.cookies.get('tg_session')
        assert client.get('/api/v1/auth/me').json()['email']==credentials['email']
        assert client.get('/api/v1/cases').status_code==200
        assert client.get('/api/v1/admin/users').status_code==403
        assert client.post('/api/v1/auth/logout').status_code==200
        assert client.get('/api/v1/history').status_code==401
        assert client.get('/api/v1/history',headers={'Authorization':'Bearer '+cookie}).status_code==401
        requests.clear()
        assert client.post('/api/v1/auth/login',json=credentials).status_code==200
        with Session() as db:
            for session in db.scalars(select(LoginSession).where(LoginSession.account_id==account.id)):
                session.expires=datetime.now(timezone.utc)-timedelta(seconds=1)
            db.commit()
        assert client.get('/api/v1/auth/me').status_code==401
