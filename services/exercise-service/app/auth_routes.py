from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.auth import (
    ATHLETE_SCOPES,
    create_access_token,
    get_current_user,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.db import get_session
from app.models import Token, UserRead, UserRegister, UserTable

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    session: Session = Depends(get_session),
) -> UserRead:
    # Password rules live in the backend (single source of truth).
    try:
        validate_password_strength(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = session.exec(select(UserTable).where(UserTable.username == data.username)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Role/scopes are forced server-side: self-registration is always athlete.
    user = UserTable(
        username=data.username,
        hashed_password=hash_password(data.password),
        role="athlete",
        scopes=list(ATHLETE_SCOPES),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead(username=user.username, role=user.role, scopes=user.scopes)


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> Token:
    user = session.exec(select(UserTable).where(UserTable.username == form_data.username)).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Grant the intersection of what the user holds and what was requested.
    # An empty request defaults to all of the user's scopes.
    requested = set(form_data.scopes) if form_data.scopes else set(user.scopes)
    granted = [scope for scope in user.scopes if scope in requested]
    token = create_access_token(user.username, granted)
    return Token(access_token=token, scopes=granted)


@router.get("/me", response_model=UserRead)
def read_me(user: UserTable = Depends(get_current_user)) -> UserRead:
    return UserRead(username=user.username, role=user.role, scopes=user.scopes)
