from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.middleware import api_key as api_key_middleware
from app.middleware.api_key import APIKeyMiddlewareSettings, APIKeyVerificationMiddleware
from app.models import Base
from app.models.api_key import APIKey
from app.models.user import User


def test_api_key_middleware_accepts_valid_key(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    raw_key = "1234567890abcdef1234567890abcdef"

    with SessionLocal() as db:
        user = User(
            email="middleware@example.com",
            hashed_password=get_password_hash("strongpassword"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(
            APIKey(
                user_id=user.id,
                name="middleware",
                key_prefix=raw_key[:8],
                hashed_key=get_password_hash(raw_key),
            )
        )
        db.commit()

    monkeypatch.setattr(api_key_middleware, "get_sessionmaker", lambda: SessionLocal)

    app = FastAPI()
    app.add_middleware(
        APIKeyVerificationMiddleware,
        settings=APIKeyMiddlewareSettings(
            API_KEY_PROTECTED_PATH_PREFIXES="/downstream",
        ),
    )

    @app.get("/downstream/resource")
    def downstream_resource():
        return {"ok": True}

    client = TestClient(app)

    missing_response = client.get("/downstream/resource")
    assert missing_response.status_code == 401

    valid_response = client.get(
        "/downstream/resource",
        headers={"X-API-Key": raw_key},
    )
    assert valid_response.status_code == 200
    assert valid_response.json() == {"ok": True}
