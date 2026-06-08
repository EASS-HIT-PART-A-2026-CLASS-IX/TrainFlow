import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlmodel import Session, select

from app.db import get_session
from app.models import UserTable

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production-please-32b")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

SCOPES = {
    "exercises:write": "Create, update, and delete catalog exercises",
    "history:read": "Read workout history",
    "history:write": "Log workout sessions",
    "coach:use": "Request AI-generated workout plans",
}

# Role -> scope mapping. New self-registrations are always athletes; admin is
# seeded only. The backend is the sole authority for these grants.
ALL_SCOPES = ["exercises:write", "history:read", "history:write", "coach:use"]
ATHLETE_SCOPES = ["history:read", "history:write", "coach:use"]

MIN_PASSWORD_LENGTH = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", scopes=SCOPES, auto_error=True)


def validate_password_strength(password: str) -> None:
    """Single source of truth for password rules, enforced server-side."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(
    subject: str,
    scopes: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "scopes": scopes, "iat": now, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> UserTable:
    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": authenticate_value},
        ) from exc
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    token_scopes = payload.get("scopes", [])

    user = session.exec(select(UserTable).where(UserTable.username == username)).first()
    if user is None:
        raise credentials_exception

    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Missing scope: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


def require_scopes(*scopes: str):
    """Dependency factory enforcing that the caller's token carries every scope."""

    def dependency(user: UserTable = Security(get_current_user, scopes=list(scopes))) -> UserTable:
        return user

    return dependency


def is_admin(user: UserTable) -> bool:
    return user.role == "admin"


# Reusable history dependencies that also hand the route the resolved user, so
# routes can enforce per-user ownership (athlete sees own; admin sees all).
require_history_read = require_scopes("history:read")
require_history_write = require_scopes("history:write")
