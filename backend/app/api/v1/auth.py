from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    refresh_token_expires_at,
    verify_password,
)
from app.models.refresh_token_session import RefreshTokenSession
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def _issue_token_pair(user: User, db: Session) -> TokenResponse:
    refresh_token = create_refresh_token()
    session = RefreshTokenSession(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_token_expires_at(),
    )
    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(subject=str(user.id)),
        refresh_token=refresh_token,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    normalized_email = user_in.email.lower()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=normalized_email,
        hashed_password=get_password_hash(user_in.password),
        role="user",
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_email = form_data.username.lower()
    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    refresh_in: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    session = db.scalar(
        select(RefreshTokenSession).where(
            RefreshTokenSession.token_hash == hash_token(refresh_in.refresh_token),
            RefreshTokenSession.revoked_at.is_(None),
        )
    )

    if session is None or _is_expired(session.expires_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    session.revoked_at = datetime.now(timezone.utc)
    return _issue_token_pair(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    refresh_in: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> None:
    session = db.scalar(
        select(RefreshTokenSession).where(
            RefreshTokenSession.token_hash == hash_token(refresh_in.refresh_token),
            RefreshTokenSession.revoked_at.is_(None),
        )
    )

    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
