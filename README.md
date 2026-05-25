# Secondbrain Social API

A small FastAPI API for users, login, short posts, and follows. It is built as a take-home style project: enough structure to show the pieces clearly, without adding layers that do not pull their weight here.

## What is included

- User registration with unique usernames and emails
- Login with JWT bearer tokens
- Password hashing with PBKDF2-SHA256 and per-password salts
- Post creation with 280-character content
- A feed made from your posts and posts from people you follow
- Follow and unfollow endpoints
- Docker Compose setup for the API and PostgreSQL
- Tests that run without PostgreSQL

## Stack

- FastAPI
- SQLAlchemy async sessions
- PostgreSQL with `psycopg`
- Pydantic and Pydantic Settings
- PyJWT
- pytest
- uv

## Run it with Docker

Copy the example environment file:

```bash
cp .env.example .env
```

Choose a real `SECRET_KEY` in `.env` before using the app outside local development. The database values in `.env.example` are local defaults.

Start the API and database:

```bash
docker compose up --build
```

The API runs at `http://127.0.0.1:8000`. Docker Compose starts PostgreSQL, waits for it to become healthy, then points the API at `db:5432`.

## Run it without Docker

Install dependencies:

```bash
uv sync
```

Set the required environment variables. In PowerShell:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/secondbrain"
```

Then start the API:

```bash
uv run fastapi dev
```

The app creates tables on startup. For this project, that keeps setup simple. In a production app, schema changes would move into migrations.

## Run tests

```bash
uv run pytest
```

Tests use FastAPI dependency overrides and a temporary SQLite database file, so PostgreSQL does not need to be running.

## Authentication

Create a user:

```powershell
curl -X POST http://127.0.0.1:8000/users `
  -H "Content-Type: application/json" `
  -d '{"username":"alice","email":"alice@example.com","password":"Password1!"}'
```

Log in:

```powershell
curl -X POST http://127.0.0.1:8000/login `
  -H "Content-Type: application/json" `
  -d '{"username":"alice","password":"Password1!"}'
```

Use the returned token on protected endpoints:

```http
Authorization: Bearer <access_token>
```

Passwords must be 8 to 128 characters and include uppercase, lowercase, numeric, and special characters. Access tokens expire after 30 minutes.

## Endpoints

### `POST /users`

Registers a user.

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "Password1!"
}
```

Returns `201` with the new user. The response does not include the password hash. Duplicate usernames or emails return `409`.

### `POST /login`

Logs in a user.

```json
{
  "username": "alice",
  "password": "Password1!"
}
```

Returns a bearer token:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

Invalid credentials return `401`.

### `POST /posts`

Creates a post. Requires a bearer token.

```json
{
  "content": "hello world"
}
```

Returns `201` with the post and author.

### `GET /posts?limit=20&offset=0`

Returns your feed. The feed contains your posts and posts from users you follow, newest first. `limit` must be between 1 and 100.

Requires a bearer token.

### `POST /users/follow/{username}`

Follows another user by username. Requires a bearer token.

- Self-follow returns `400`
- Unknown users return `404`
- Duplicate follows return `409`

### `DELETE /users/follow/{username}`

Unfollows a user by username. Requires a bearer token.

Returns `204` on success.

## Project layout

```text
app/
  config.py      settings loaded from environment variables and .env
  database.py    engine and session setup
  models.py      SQLAlchemy models
  routes.py      FastAPI routes and HTTP status handling
  schemas.py     Pydantic request and response models
  security.py    password hashing, JWTs, and auth dependencies
  services.py    business logic used by the routes
tests/
  conftest.py    test database and dependency overrides
  test_api.py    API behavior tests
  test_config.py settings tests
```

The code intentionally skips a repository layer, refresh tokens, profile pages, and migrations. Those would make sense in a larger service, but they would add noise to this version.
