#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/../backups"

log() { echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*"; }

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/pmbuilder_$TIMESTAMP.sql.gz"

log "Starting database backup..."

PGPASSWORD=pmpass pg_dump \
    -h localhost \
    -U pmuser \
    -d pmbuilder \
    --no-owner \
    --no-acl \
    | gzip > "$BACKUP_FILE"

log "Backup written to $BACKUP_FILE"

log "Removing backups older than 30 days..."
find "$BACKUP_DIR" -name "pmbuilder_*.sql.gz" -mtime +30 -delete

if [ -n "${S3_BUCKET:-}" ]; then
    log "Uploading to S3 bucket: $S3_BUCKET"
    aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/$(basename "$BACKUP_FILE")"
    log "S3 upload complete"
fi

log "Backup completed successfully"
