#!/usr/bin/env bash
# =============================================================================
# EKAFY — backup_db.sh
# pg_dump a managed project's database with gzip compression.
#
# Usage:
#   backup_db.sh <slug> <db_name> <db_user> <db_password> <backups_dir>
# =============================================================================
set -euo pipefail

SLUG="${1:?SLUG required}"
DB_NAME="${2:?DB_NAME required}"
DB_USER="${3:?DB_USER required}"
DB_PASSWORD="${4:?DB_PASSWORD required}"
BACKUPS_DIR="${5:-/srv/ekafy/backups}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUPS_DIR/$SLUG"
OUTPUT_FILE="$BACKUP_DIR/${SLUG}_db_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "=== [EKAFY] Backing up database: $DB_NAME ==="

export PGPASSWORD="$DB_PASSWORD"
pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$OUTPUT_FILE"
unset PGPASSWORD

SIZE=$(du -sh "$OUTPUT_FILE" | cut -f1)
echo "✓ Backup created: $OUTPUT_FILE ($SIZE)"
echo "$OUTPUT_FILE"
