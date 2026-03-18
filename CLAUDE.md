# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monobot — Python 3.13 project using FastAPI and SQLAlchemy, managed with uv.

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
```

## Tech Stack

- **Runtime**: Python 3.13
- **Package manager**: uv (see `uv.lock`)
- **Web framework**: FastAPI
- **ORM**: SQLAlchemy
- **Config**: `config.py` (environment/settings)
- **Containerization**: Docker + Docker Compose