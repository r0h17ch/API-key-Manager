import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_current_user, get_db
from app.core.security import get_password_hash
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyUpdate

router = APIRouter(tags=["api-keys"])


class APIKeyCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    key_prefix: str = Field(min_length=8, max_length=8)
    api_key: str = Field(min_length=32, max_length=32)
    is_revoked: bool
    created_at: datetime


@router.post(
    "/",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    key_in: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    raw_key = secrets.token_hex(16)
    key = APIKey(
        user_id=current_user.id,
        name=key_in.name,
        key_prefix=raw_key[:8],
        hashed_key=get_password_hash(raw_key),
    )

    db.add(key)
    db.commit()
    db.refresh(key)

    return {
        "id": key.id,
        "user_id": key.user_id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "api_key": raw_key,
        "is_revoked": key.is_revoked,
        "created_at": key.created_at,
    }


@router.get("/", response_model=list[APIKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[APIKey]:
    return list(
        db.scalars(
            select(APIKey)
            .where(
                APIKey.user_id == current_user.id,
                APIKey.is_revoked.is_(False),
            )
            .order_by(APIKey.created_at.desc())
        )
    )


@router.get("/admin/all", response_model=list[APIKeyResponse])
def list_all_api_keys(
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> list[APIKey]:
    return list(db.scalars(select(APIKey).order_by(APIKey.created_at.desc())))


@router.patch("/{key_id}", response_model=APIKeyResponse)
def update_api_key(
    key_id: uuid.UUID,
    key_in: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIKey:
    query = select(APIKey).where(APIKey.id == key_id, APIKey.is_revoked.is_(False))
    if current_user.role != "admin":
        query = query.where(APIKey.user_id == current_user.id)

    key = db.scalar(query)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    key.name = key_in.name
    db.commit()
    db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    query = select(APIKey).where(APIKey.id == key_id, APIKey.is_revoked.is_(False))
    if current_user.role != "admin":
        query = query.where(APIKey.user_id == current_user.id)

    key = db.scalar(query)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    key.is_revoked = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
