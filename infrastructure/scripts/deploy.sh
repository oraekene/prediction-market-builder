#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$INFRA_DIR")"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"
LOG_FILE="$REPO_ROOT/deploy.log"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

cd "$REPO_ROOT"

log "Pulling latest from git..."
git pull origin main

export COMPOSE_FILE

log "Tagging current backend image as previous (for rollback)..."
docker tag pmbuilder-backend:latest pmbuilder-backend:previous 2>/dev/null || true

log "Building backend image..."
docker compose build backend

log "Starting services..."
docker compose up -d

log "Running database migrations..."
docker compose exec -T backend alembic upgrade head

log "Running health checks..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Health check passed (attempt $i)"
        exit 0
    fi
    if [ "$i" -eq 12 ]; then
        log "Health check failed after 12 attempts — rolling back..."
        "$SCRIPT_DIR/rollback.sh"
        exit 1
    fi
    log "Health check attempt $i failed, retrying in 5s..."
    sleep 5
done
