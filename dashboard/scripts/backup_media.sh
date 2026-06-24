#!/usr/bin/env bash
# =============================================================================
# EKAFY — backup_media.sh
# tar.gz archive of a project's media directory.
#
# Usage:
#   backup_media.sh <slug> <projects_base_dir> <backups_dir>
# =============================================================================
set -euo pipefail

SLUG="${1:?SLUG required}"
PROJECTS_BASE="${2:-/srv/ekafy/projects}"
BACKUPS_DIR="${3:-/srv/ekafy/backups}"

MEDIA_DIR="$PROJECTS_BASE/$SLUG/media"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUPS_DIR/$SLUG"
OUTPUT_FILE="$BACKUP_DIR/${SLUG}_media_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$MEDIA_DIR" ]; then
  echo "ERROR: Media directory not found: $MEDIA_DIR"
  exit 1
fi

echo "=== [EKAFY] Archiving media: $MEDIA_DIR ==="
tar -czf "$OUTPUT_FILE" -C "$MEDIA_DIR" .
SIZE=$(du -sh "$OUTPUT_FILE" | cut -f1)
echo "✓ Media archive created: $OUTPUT_FILE ($SIZE)"
echo "$OUTPUT_FILE"
