from datetime import datetime, timedelta, timezone
import logging
import threading
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError

from app.database import get_session
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = {}
_failed_logins_lock = threading.Lock()


def _check_lockout(email: str) -> None:
    now = time.monotonic()
    with _failed_logins_lock:
        attempts = [t for t in _failed_logins.get(email, []) if now - t < _LOCKOUT_WINDOW_SECONDS]
        _failed_logins[email] = attempts
        if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")


def _record_failed_login(email: str) -> None:
    with _failed_logins_lock:
        _failed_logins.setdefault(email, []).append(time.monotonic())


def _clear_failed_logins(email: str) -> None:
    with _failed_logins_lock:
        _failed_logins.pop(email, None)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _create_token(user_id: str, token_type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    expire = (
        settings.access_token_expire_minutes
        if token_type == "access"
        else settings.refresh_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=expire),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await get_user_from_token(credentials.credentials, session)


async def get_user_from_token(
    token: str | None,
    session: AsyncSession | None = None,
) -> User:
    """Resolve a bearer token to a User. Used by both HTTP and WebSocket endpoints."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token must be an access token")
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    owns_session = session is not None
    if not owns_session:
        from app.database import async_session as _async_session
        session = _async_session()
    try:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    finally:
        if not owns_session:
            await session.close()


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "has_polymarket_key": bool(current_user.polymarket_key),
        "has_kalshi_key": bool(current_user.kalshi_key),
        "has_drift_key": bool(current_user.drift_key),
    }


class ExchangeKeysRequest(BaseModel):
    polymarket_key: str | None = None
    kalshi_key: str | None = None
    drift_key: str | None = None


@router.put("/keys")
async def set_exchange_keys(
    req: ExchangeKeysRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from app.services.encryption import encryption_service
    if req.polymarket_key:
        current_user.polymarket_key = encryption_service.encrypt(req.polymarket_key)
    if req.kalshi_key:
        current_user.kalshi_key = encryption_service.encrypt(req.kalshi_key)
    if req.drift_key:
        current_user.drift_key = encryption_service.encrypt(req.drift_key)
    await session.commit()
    return {"success": True}


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    result = await session.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        email=req.email,
        hashed_password=pwd_context.hash(req.password),
        display_name=req.display_name,
    )
    session.add(user)
    await session.commit()
    access_token = _create_token(user.id, "access")
    refresh_token = _create_token(user.id, "refresh")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    _check_lockout(req.email)
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        _record_failed_login(req.email)
        logger.warning("Failed login attempt for %s", req.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _clear_failed_logins(req.email)
    access_token = _create_token(user.id, "access")
    refresh_token = _create_token(user.id, "refresh")
    logger.info("User logged in: %s", user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, session: AsyncSession = Depends(get_session)):
    payload = _decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token must be a refresh token")
    user_id = payload.get("sub")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    access_token = _create_token(user.id, "access")
    refresh_token = _create_token(user.id, "refresh")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)
