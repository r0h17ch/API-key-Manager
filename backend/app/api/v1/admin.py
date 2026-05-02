import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserRoleUpdate

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
def list_users(
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: uuid.UUID,
    role_in: UserRoleUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_admin.id and role_in.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot remove their own admin role",
        )

    user.role = role_in.role
    db.commit()
    db.refresh(user)
    return user
