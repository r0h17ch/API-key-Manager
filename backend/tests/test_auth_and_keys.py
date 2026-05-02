from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.refresh_token_session import RefreshTokenSession
from app.models.user import User


def test_register_login_refresh_logout_flow(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "dev@example.com", "password": "strongpassword"},
    )

    assert register_response.status_code == 201
    assert register_response.json()["email"] == "dev@example.com"

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "dev@example.com", "password": "strongpassword"},
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["token_type"] == "bearer"
    assert login_payload["access_token"]
    assert login_payload["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    rotated_payload = refresh_response.json()
    assert rotated_payload["access_token"]
    assert rotated_payload["refresh_token"] != login_payload["refresh_token"]

    reused_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )

    assert reused_refresh_response.status_code == 401

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_payload["refresh_token"]},
    )

    assert logout_response.status_code == 204


def test_api_key_lifecycle(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "keys@example.com", "password": "strongpassword"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "keys@example.com", "password": "strongpassword"},
    )
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    create_response = client.post(
        "/api/v1/keys/",
        json={"name": "CI key"},
        headers=headers,
    )

    assert create_response.status_code == 201
    created_key = create_response.json()
    assert len(created_key["api_key"]) == 32
    assert created_key["key_prefix"] == created_key["api_key"][:8]

    list_response = client.get("/api/v1/keys/", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "CI key"
    assert "hashed_key" not in list_response.json()[0]
    assert "api_key" not in list_response.json()[0]

    revoke_response = client.delete(f"/api/v1/keys/{created_key['id']}", headers=headers)

    assert revoke_response.status_code == 204
    assert client.get("/api/v1/keys/", headers=headers).json() == []


def test_admin_can_manage_user_roles(client, db_session: Session):
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("strongpassword"),
        role="admin",
    )
    user = User(
        email="user@example.com",
        hashed_password=get_password_hash("strongpassword"),
        role="user",
    )
    db_session.add_all([admin, user])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "strongpassword"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    users_response = client.get("/api/v1/admin/users", headers=headers)

    assert users_response.status_code == 200
    assert len(users_response.json()) == 2

    promote_response = client.patch(
        f"/api/v1/admin/users/{user.id}/role",
        json={"role": "admin"},
        headers=headers,
    )

    assert promote_response.status_code == 200
    assert promote_response.json()["role"] == "admin"


def test_expired_refresh_token_is_rejected(client, db_session: Session):
    client.post(
        "/api/v1/auth/register",
        json={"email": "expired@example.com", "password": "strongpassword"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "expired@example.com", "password": "strongpassword"},
    )
    refresh_token = login_response.json()["refresh_token"]

    for session in db_session.query(RefreshTokenSession):
        session.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db_session.commit()

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 401
