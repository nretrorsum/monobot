# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monobot — Python 3.13 project using FastAPI and SQLAlchemy, managed with uv.
Integrates with Monobank API for transaction tracking and provides JWT-based authentication.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the app
uv run python main.py

# Run with FastAPI dev server
uv run fastapi dev main.py

# Add a dependency
uv add <package>

# Docker
docker compose up --build

# Alembic migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Tech Stack

- **Runtime**: Python 3.13
- **Package manager**: uv (see `uv.lock`)
- **Web framework**: FastAPI
- **ORM**: SQLAlchemy (async, asyncpg)
- **Auth**: JWT (python-jose) + bcrypt
- **Config**: `src/core/config.py` (environment/settings from `.env`)
- **Migrations**: Alembic
- **Task queue**: Celery + Redis
- **Containerization**: Docker + Docker Compose (app, postgres, redis, celery-worker, celery-beat)

## Project Structure

```
src/
├── core/              # Config, DB session, security, JWT, hashing, dependencies
├── models/            # SQLAlchemy ORM models (BaseUuidModel, User, RefreshToken, UserToken, UserTransaction)
├── schemas/           # Pydantic schemas
├── services/          # Business logic
└── routers/           # FastAPI routers
```

## Auth System

- JWT-based with access (15min) + refresh (30d) tokens
- Web clients: httpOnly cookies, mobile clients: Bearer header + JSON body
- Client detection via `X-Client-Type: mobile` header
- Refresh token rotation with theft detection (sha256 jti stored in DB)
- Key files: `src/core/jwt.py`, `src/core/hashing.py`, `src/core/dependencies.py`, `src/services/jwt_auth.py`, `src/routers/jwt_auth.py`
