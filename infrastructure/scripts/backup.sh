#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$INFRA_DIR")"
export COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

BACKUP_DIR="$REPO_ROOT/backups"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +'%Y%m%d_%H%M%S')"

echo "Backing up PostgreSQL to $BACKUP_DIR/postgres_$STAMP.dump ..."
docker compose exec -T postgres pg_dump -U pmuser -d pmbuilder -F c \
    > "$BACKUP_DIR/postgres_$STAMP.dump"

echo "Backup written. Restore with:"
echo "  docker compose exec -T postgres pg_restore -U pmuser -d pmbuilder -c < $BACKUP_DIR/postgres_$STAMP.dump"
