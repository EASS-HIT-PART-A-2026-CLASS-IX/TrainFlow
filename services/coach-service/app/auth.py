import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production-please-32b")
ALGORITHM = "HS256"
REQUIRED_SCOPE = "coach:use"

_bearer = HTTPBearer(auto_error=True)


def require_coach(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Verify a JWT issued by exercise-service and require the coach:use scope.
    Returns the raw token so the route can forward it to exercise-service."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

    if REQUIRED_SCOPE not in payload.get("scopes", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Missing scope: {REQUIRED_SCOPE}",
        )
    return token
