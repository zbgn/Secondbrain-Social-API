import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
bearer_scheme = HTTPBearer(auto_error=False)


def get_secret_key() -> str:
    secret_key = get_settings().secret_key
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required")
    return secret_key


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    salt_b64 = base64.b64encode(salt).decode()
    digest_b64 = base64.b64encode(digest).decode()
    return f"pbkdf2_sha256$600000${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        base64.b64decode(salt),
        int(iterations),
    )
    return hmac.compare_digest(base64.b64encode(digest).decode(), expected)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "exp": expires_at}
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error

    try:
        payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except InvalidTokenError, KeyError, ValueError:
        raise credentials_error from None

    user = await db.scalar(
        select(User).options(selectinload(User.following)).where(User.id == user_id)
    )
    if user is None:
        raise credentials_error
    return user
