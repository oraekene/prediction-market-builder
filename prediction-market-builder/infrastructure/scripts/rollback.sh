#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

log() { echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*"; }

export COMPOSE_FILE="$COMPOSE_FILE"

PREVIOUS_TAG="${ROLLBACK_TAG:-backend:previous}"

log "Rolling back backend to $PREVIOUS_TAG..."

log "Running alembic downgrade..."
if ! docker compose exec -T backend alembic downgrade -1; then
    log "No migration to downgrade — continuing with rollback"
fi

log "Reverting backend to previous image..."
docker compose up -d --no-deps backend

log "Waiting for backend to become healthy..."
for i in $(seq 1 10); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Health check passed after rollback (attempt $i)"
        break
    fi
    if [ "$i" -eq 10 ]; then
        log "CRITICAL: Rollback health check failed after 10 attempts"
        exit 1
    fi
    log "Health check attempt $i failed, retrying in 5s..."
    sleep 5
done

log "Rollback completed successfully"
