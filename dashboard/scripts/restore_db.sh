#!/usr/bin/env bash
# =============================================================================
# EKAFY — restore_db.sh
# Drop and restore a PostgreSQL database from a .sql.gz dump file.
#
# Usage:
#   restore_db.sh <slug> <db_name> <db_user> <db_password> <backup_file>
#
# WARNING: This drops and recreates the database!
# =============================================================================
set -euo pipefail

SLUG="${1:?SLUG required}"
DB_NAME="${2:?DB_NAME required}"
DB_USER="${3:?DB_USER required}"
DB_PASSWORD="${4:?DB_PASSWORD required}"
BACKUP_FILE="${5:?BACKUP_FILE required}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "=== [EKAFY] Restoring database: $DB_NAME ==="
echo "    From: $BACKUP_FILE"
echo ""
echo "!!! WARNING: This will DROP and RECREATE the database '$DB_NAME' !!!"
read -r -p "    Type 'yes' to confirm: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

export PGPASSWORD="$DB_PASSWORD"

echo "--- Stopping service: ekafy-$SLUG.service ---"
sudo systemctl stop "ekafy-$SLUG.service" || true

echo "--- Dropping database ---"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"
sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO \"$DB_USER\";"

echo "--- Restoring from backup ---"
zcat "$BACKUP_FILE" | psql -U "$DB_USER" -h localhost "$DB_NAME"

unset PGPASSWORD

echo "--- Restarting service ---"
sudo systemctl start "ekafy-$SLUG.service"

echo ""
echo "=== [EKAFY] Database restore complete ==="
