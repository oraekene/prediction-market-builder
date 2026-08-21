#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
export COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

docker compose exec -T backend alembic upgrade head
