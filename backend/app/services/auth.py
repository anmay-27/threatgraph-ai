"""Optional account mode for shared deployments; local mode is explicitly single user."""

import hashlib
import hmac
import secrets
from contextvars import ContextVar
from types import MappingProxyType
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, select, delete
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base, Session
from app.core.config import settings

principal = ContextVar(
    "principal", default=MappingProxyType({"id": "local", "role": "ADMIN"})
)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="USER")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AnalysisOwner(Base):
    __tablename__ = "analysis_owners"
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    owner_id: Mapped[str] = mapped_column(String(100), index=True)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()
    )


def own_analysis(db, row):
    db.flush()
    db.add(AnalysisOwner(analysis_id=row.id, owner_id=principal.get()["id"]))


def accessible(db, analysis_id):
    if not settings.auth_required:
        return True
    owner = db.get(AnalysisOwner, analysis_id)
    return owner is not None and owner.owner_id == principal.get()["id"]


def scope(statement):
    from app.models.database import Analysis

    if settings.auth_required:
        statement = statement.where(
            Analysis.id.in_(
                select(AnalysisOwner.analysis_id).where(
                    AnalysisOwner.owner_id == principal.get()["id"]
                )
            )
        )
    return statement


def allowed_analysis_ids():
    return select(AnalysisOwner.analysis_id).where(
        AnalysisOwner.owner_id == principal.get()["id"]
    )


def authenticate(request):
    if not settings.auth_required:
        return {"id": "local", "role": "ADMIN"}
    authorization = request.headers.get("authorization", "")
    token = (
        authorization[7:]
        if authorization.startswith("Bearer ")
        else request.cookies.get("tg_session", "")
    )
    with Session() as db:
        session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        if not session or session.expires.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise HTTPException(401, "Sign in to access your investigations")
        account = db.get(Account, session.account_id)
        if not account:
            raise HTTPException(401, "Session expired")
        return {"id": account.id, "email": account.email, "role": account.role}


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


@router.post("/token")
def create_token(request: Request):
    if not settings.auth_required:
        raise HTTPException(409, "API token is not needed in local mode")
    user = authenticate(request)
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=12)
    with Session() as db:
        db.add(
            LoginSession(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                account_id=user["id"],
                expires=expires,
            )
        )
        db.commit()
    return {
        "token": token,
        "expires": expires,
        "warning": "This token grants access as your account. Keep it private.",
    }


@router.get("/me")
def me(request: Request):
    return {**authenticate(request), "auth_required": settings.auth_required}


@router.post("/register", status_code=201)
def register(body: Credentials):
    if not settings.auth_required:
        raise HTTPException(409, "Account mode is disabled")
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "Enter an email address")
    from sqlalchemy.exc import IntegrityError

    with Session() as db:
        account = Account(email=email, password_hash=password_hash(body.password))
        db.add(account)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Account cannot be created with this address")
    return {"created": True}


@router.post("/login")
def login(body: Credentials, response: Response):
    if not settings.auth_required:
        raise HTTPException(409, "Account mode is disabled")
    with Session() as db:
        account = db.scalar(
            select(Account).where(Account.email == body.email.strip().lower())
        )
        expected = (
            account.password_hash
            if account
            else password_hash("dummy-password-for-timing")
        )
        if (
            not hmac.compare_digest(
                password_hash(body.password, expected.split(":")[0]), expected
            )
            or not account
        ):
            raise HTTPException(401, "Invalid email or password")
        token = secrets.token_urlsafe(32)
        db.add(
            LoginSession(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                account_id=account.id,
                expires=datetime.now(timezone.utc) + timedelta(hours=12),
            )
        )
        db.commit()
    response.set_cookie(
        "tg_session",
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        max_age=43200,
        path="/",
    )
    return {"signed_in": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    user = authenticate(request)
    with Session() as db:
        db.execute(delete(LoginSession).where(LoginSession.account_id == user["id"]))
        db.commit()
    response.delete_cookie("tg_session", path="/")
    return {"signed_out": True}
