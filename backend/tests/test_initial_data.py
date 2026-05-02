from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.initial_data import AdminSeedSettings, seed_admin_user
from app.models.user import User


def test_seed_admin_user_creates_default_admin(db_session: Session):
    settings = AdminSeedSettings(
        ADMIN_EMAIL="Admin@Example.com",
        ADMIN_PASSWORD="Admin@12345",
    )

    admin = seed_admin_user(db_session, settings)

    assert admin.email == "admin@example.com"
    assert admin.role == "admin"
    assert verify_password("Admin@12345", admin.hashed_password)


def test_seed_admin_user_promotes_existing_user_without_changing_password(
    db_session: Session,
):
    existing_user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("existing-password"),
        role="user",
    )
    db_session.add(existing_user)
    db_session.commit()

    settings = AdminSeedSettings(
        ADMIN_EMAIL="admin@example.com",
        ADMIN_PASSWORD="Admin@12345",
    )

    admin = seed_admin_user(db_session, settings)

    assert admin.id == existing_user.id
    assert admin.role == "admin"
    assert verify_password("existing-password", admin.hashed_password)
