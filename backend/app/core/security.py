import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

import bcrypt as bcrypt_backend
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _patch_bcrypt_backend_for_passlib() -> None:
    if not hasattr(bcrypt_backend, "__about__"):
        bcrypt_backend.__about__ = SimpleNamespace(
            __version__=getattr(bcrypt_backend, "__version__", "unknown")
        )

    original_hashpw = bcrypt_backend.hashpw

    if getattr(original_hashpw, "_passlib_compat", False):
        return

    def hashpw_compat(password: bytes, salt: bytes) -> bytes:
        try:
            return original_hashpw(password, salt)
        except ValueError as exc:
            if "password cannot be longer than 72 bytes" in str(exc) and len(password) > 72:
                return original_hashpw(password[:72], salt)
            raise

    hashpw_compat._passlib_compat = True
    bcrypt_backend.hashpw = hashpw_compat


_patch_bcrypt_backend_for_passlib()

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = Field(validation_alias="SECRET_KEY", min_length=32)
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        gt=0,
    )
    refresh_token_expire_days: int = Field(
        default=30,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
        gt=0,
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")


@lru_cache
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expires_at() -> datetime:
    settings = get_security_settings()
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_security_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_security_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except InvalidTokenError:
        raise

    return payload
