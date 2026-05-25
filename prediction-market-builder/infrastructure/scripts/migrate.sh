#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

log() { echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*"; }

DRY_RUN=false
SEED_SCRIPT="$SCRIPT_DIR/seed_data.py"

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

if [ "$DRY_RUN" = true ]; then
    log "Dry-run mode — showing SQL without executing"
    docker compose exec -T -e DRY_RUN=true backend alembic upgrade head --sql
    exit 0
fi

export COMPOSE_FILE="$COMPOSE_FILE"

log "Running database migrations..."
if ! docker compose exec -T backend alembic upgrade head; then
    log "Migration failed — initiating rollback..."
    docker compose exec -T backend alembic downgrade -1
    exit 1
fi
log "Migrations applied successfully"

log "Checking if seed data is needed..."
SEED_NEEDED=$(docker compose exec -T backend python -c "
import asyncio
from app.database import async_session
from app.models import User
from sqlalchemy import select

async def check():
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        return 'empty' if result.scalar_one_or_none() is None else 'seeded'

print(asyncio.run(check()))
")

if [ "$SEED_NEEDED" = "empty" ]; then
    log "Database is empty — running seed script..."
    docker compose exec -T backend python "$SEED_SCRIPT"
    log "Seed data inserted"
else
    log "Database already has data — skipping seed"
fi

log "Migration completed successfully"
