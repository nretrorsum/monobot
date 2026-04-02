#!/bin/sh
set -e

echo "Running migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info