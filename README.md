# API Key Manager

Production-oriented API key management service built with FastAPI, PostgreSQL, Redis, React, and Docker.

The application supports user registration, JWT authentication, refresh-token sessions, admin user management, API key generation, API key verification, API key listing, and soft revocation. Raw API keys are returned only once at creation time; persisted keys are stored as hashes.

## Architecture

```text
apiKeyMngr/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # API routers and dependencies
│   │   ├── core/         # Security and settings utilities
│   │   ├── middleware/   # API key verification middleware
│   │   ├── models/       # SQLAlchemy models
│   │   └── schemas/      # Pydantic schemas
│   ├── alembic/          # Database migrations
│   ├── Dockerfile
│   └── main.py           # FastAPI entrypoint
├── frontend/             # React + Vite application
│   ├── src/
│   │   ├── api/          # Axios client
│   │   ├── components/   # Shared UI components
│   │   ├── context/      # Auth state
│   │   └── pages/        # Login, register, dashboard
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── .env                  # Local runtime configuration
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.x, Pydantic Settings, PyJWT, Passlib
- **Database:** PostgreSQL 15
- **Cache:** Redis
- **Frontend:** React, Vite, React Router DOM, Axios, Lucide React
- **Infrastructure:** Docker Compose, Nginx for frontend static hosting

## Prerequisites

- Docker and Docker Compose
- Node.js 22+ for local frontend development
- Python 3.11+ and `uv` for local backend development

## Environment Configuration

Create a root `.env` file. A safe starting point is available in `.env.example`:

```bash
cp .env.example .env
```

Local development values:

```env
POSTGRES_USER=api_key_user
POSTGRES_PASSWORD=api_key_password
POSTGRES_DB=api_key_manager

DATABASE_URL=postgresql+psycopg2://api_key_user:api_key_password@localhost:5432/api_key_manager
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=0123456789abcdef0123456789abcdef
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_ALGORITHM=HS256
API_KEY_HEADER_NAME=X-API-Key
API_KEY_PROTECTED_PATH_PREFIXES=
```

For Docker, `docker-compose.yml` overrides the backend database and Redis hostnames to use internal service names:

- PostgreSQL: `db:5432`
- Redis: `cache:6379`

Use a strong, randomly generated `SECRET_KEY` before deploying outside local development.

## Running with Docker

Build and start all services:

```bash
docker compose up -d --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Stop services:

```bash
docker compose down
```

Stop services and remove persisted database/cache volumes:

```bash
docker compose down -v
```

## Running Locally

Start only the infrastructure services:

```bash
docker compose up -d db cache
```

Run the backend:

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server usually runs at:

```text
http://localhost:5173
```

## API Overview

Base URL:

```text
http://localhost:8000/api/v1
```

Authentication:

- `POST /auth/register` creates a user account.
- `POST /auth/login` accepts OAuth2 form credentials and returns an access token plus refresh token.
- `POST /auth/refresh` rotates a refresh token and returns a new token pair.
- `POST /auth/logout` revokes a refresh-token session.

API keys:

- `POST /keys/` creates a new API key and returns the raw key once.
- `GET /keys/` lists active keys for the authenticated user.
- `DELETE /keys/{key_id}` revokes a key owned by the authenticated user.
- `GET /keys/admin/all` lists all keys and requires an admin user.

Admin:

- `GET /admin/users` lists all users and requires an admin user.
- `PATCH /admin/users/{user_id}/role` updates a user's role to `user` or `admin`.

Authenticated requests require:

```http
Authorization: Bearer <access_token>
```

Downstream API key verification is available through middleware. Configure `API_KEY_PROTECTED_PATH_PREFIXES` as a comma-separated list of path prefixes to protect, then send API keys in the configured header:

```http
X-API-Key: <raw_api_key>
```

## Frontend Workflow

The frontend provides:

- Login and registration screens
- Access-token and refresh-token persistence in `localStorage`
- Automatic access-token refresh on `401` responses
- Protected dashboard route
- API key list with name and key prefix
- Key generation modal
- One-time raw key display
- Key revocation action

Axios is configured in `frontend/src/api/axios.js` with:

```text
http://localhost:8000/api/v1
```

## Backend Notes

The backend entrypoint is:

```text
backend/main.py
```

Run it with:

```bash
uvicorn main:app --reload
```

The SQLAlchemy models are defined in:

- `backend/app/models/user.py`
- `backend/app/models/api_key.py`
- `backend/app/models/refresh_token_session.py`

Run migrations with:

```bash
cd backend
uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
```


## Quality Checks

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Backend import check:

```bash
cd backend
uv run python -m compileall -q main.py app
```

Backend tests:

```bash
cd backend
uv run pytest
```

Docker Compose validation:

```bash
docker compose config
```

## Security Considerations

- Raw API keys are displayed only at creation time.
- API keys are stored hashed in the database.
- Refresh tokens are stored hashed in the database and rotated on use.
- Revocation is implemented as a soft delete via `is_revoked`.
- Registration always creates regular users; admin role changes require an existing admin.
- API key middleware can protect downstream routes using the `X-API-Key` header.
- Replace local development secrets before production deployment.
- Add rate limiting, audit logs, and HTTPS termination before production use.

## Current Status

Implemented:

- Docker Compose infrastructure
- Backend FastAPI app assembly
- User and API key SQLAlchemy models
- Alembic migrations
- JWT access-token authentication
- Refresh-token session management
- API key create/list/revoke endpoints
- API key verification middleware for downstream routes
- Admin user-management endpoints
- Automated backend tests
- GitHub Actions CI for backend tests, frontend lint/build, and Docker Compose validation
- React login/register/dashboard frontend
- Dockerfiles for backend and frontend

Future enhancements:

- Add rate limiting and abuse protection
- Add audit logs for key creation, revocation, login, and role changes
- Add a first-admin bootstrap command
- Add production secret management
- Add HTTPS termination and deployment manifests
