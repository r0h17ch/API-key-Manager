from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_sessionmaker
from app.core.security import get_password_hash
from app.models.user import User


class AdminSeedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    admin_email: str = Field(
        default="admin@example.com",
        validation_alias="ADMIN_EMAIL",
    )
    admin_password: str = Field(
        default="Admin@12345",
        validation_alias="ADMIN_PASSWORD",
        min_length=8,
    )


def seed_admin_user(db: Session, settings: AdminSeedSettings | None = None) -> User:
    settings = settings or AdminSeedSettings()
    admin_email = settings.admin_email.lower()

    admin = db.scalar(select(User).where(User.email == admin_email))
    if admin is not None:
        if admin.role != "admin":
            admin.role = "admin"
            db.commit()
            db.refresh(admin)
        return admin

    admin = User(
        email=admin_email,
        hashed_password=get_password_hash(settings.admin_password),
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def main() -> None:
    session_factory = get_sessionmaker()
    with session_factory() as db:
        admin = seed_admin_user(db)
        print(f"Admin user is ready: {admin.email}")


if __name__ == "__main__":
    main()
