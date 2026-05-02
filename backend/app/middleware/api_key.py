from collections.abc import Callable

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.deps import get_sessionmaker
from app.core.security import verify_password
from app.models.api_key import APIKey


class APIKeyMiddlewareSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key_header_name: str = Field(default="X-API-Key", validation_alias="API_KEY_HEADER_NAME")
    api_key_protected_path_prefixes: str = Field(
        default="",
        validation_alias="API_KEY_PROTECTED_PATH_PREFIXES",
    )

    @property
    def protected_prefixes(self) -> tuple[str, ...]:
        return tuple(
            prefix.strip()
            for prefix in self.api_key_protected_path_prefixes.split(",")
            if prefix.strip()
        )


class APIKeyVerificationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Callable,
        settings: APIKeyMiddlewareSettings | None = None,
    ) -> None:
        super().__init__(app)
        self.settings = settings or APIKeyMiddlewareSettings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._requires_api_key(request.url.path):
            return await call_next(request)

        raw_key = request.headers.get(self.settings.api_key_header_name)
        if not raw_key:
            return JSONResponse({"detail": "API key required"}, status_code=401)

        api_key = self._find_valid_api_key(raw_key)
        if api_key is None:
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        request.state.api_key_id = api_key.id
        request.state.api_key_user_id = api_key.user_id
        return await call_next(request)

    def _requires_api_key(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.settings.protected_prefixes)

    def _find_valid_api_key(self, raw_key: str) -> APIKey | None:
        key_prefix = raw_key[:8]
        session_factory = get_sessionmaker()

        with session_factory() as db:
            candidates = db.scalars(
                select(APIKey).where(
                    APIKey.key_prefix == key_prefix,
                    APIKey.is_revoked.is_(False),
                )
            )

            for api_key in candidates:
                if verify_password(raw_key, api_key.hashed_key):
                    return api_key

        return None
