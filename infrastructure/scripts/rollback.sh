#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
export COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

echo "Rolling back backend to the previously deployed image..."
if docker image inspect pmbuilder-backend:previous > /dev/null 2>&1; then
    docker tag pmbuilder-backend:previous pmbuilder-backend:latest
    docker compose up -d --no-deps backend
    echo "Rollback complete."
else
    echo "No previous image found (pmbuilder-backend:previous). Nothing to roll back to."
    exit 1
fi
