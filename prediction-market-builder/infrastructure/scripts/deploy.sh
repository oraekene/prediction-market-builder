#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
LOG_FILE="$PROJECT_DIR/../deploy.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"; }

log "Starting deployment..."

cd "$PROJECT_DIR/.."

log "Pulling latest from git..."
git pull origin main

log "Building frontend..."
cd frontend
npm ci
npm run build
cd ..

export COMPOSE_FILE="$COMPOSE_FILE"

log "Building backend image..."
docker compose build backend

log "Running database migrations..."
docker compose exec -T backend alembic upgrade head

log "Restarting backend services with rolling update..."
docker compose up -d --no-deps --scale backend=2 backend

log "Running health checks..."
for i in $(seq 1 10); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Health check passed (attempt $i)"
        break
    fi
    if [ "$i" -eq 10 ]; then
        log "Health check failed after 10 attempts — rolling back..."
        "$SCRIPT_DIR/rollback.sh"
        exit 1
    fi
    log "Health check attempt $i failed, retrying in 5s..."
    sleep 5
done

log "Deployment completed successfully"
