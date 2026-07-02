#!/usr/bin/env bash
# =============================================================================
# EKAFY — deploy_project.sh
# Full deployment pipeline: git pull → pip install → migrate → static → restart
#
# Usage:
#   deploy_project.sh <slug> <projects_base_dir> <settings_module>
# =============================================================================
set -euo pipefail

PROJECT_SLUG="${1:?SLUG required}"
EKAFY_BASE_DIR="${EKAFY_BASE_DIR:-/srv/ekafydj}"
PROJECTS_BASE="${2:-${EKAFY_PROJECTS_DIR:-$EKAFY_BASE_DIR/projects}}"
SETTINGS_MODULE="${3:-config.settings.production}"

PROJECT_DIR="$PROJECTS_BASE/$PROJECT_SLUG"
REPO_DIR="$PROJECT_DIR/repo"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
MANAGE="$REPO_DIR/manage.py"
SERVICE_NAME="ekafy-$PROJECT_SLUG.service"

EKAFY_LOGS_DIR="${EKAFY_LOGS_DIR:-$EKAFY_BASE_DIR/logs}"
mkdir -p "$EKAFY_LOGS_DIR"
LOG_FILE="$EKAFY_LOGS_DIR/deploy_${PROJECT_SLUG}_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== [EKAFY] Deploying: $PROJECT_SLUG ==="
echo "    Settings: $SETTINGS_MODULE"
echo "    Time: $(date)"

# ── 1. git pull ───────────────────────────────────────────────────────────────
echo "--- Step 1/5: git pull ---"
cd "$REPO_DIR"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git pull origin "$BRANCH"
COMMIT=$(git log -1 --format="%H %s")
echo "✓ Pulled: $COMMIT"

# ── 2. pip install ────────────────────────────────────────────────────────────
echo "--- Step 2/5: pip install ---"
if [ -f "$REPO_DIR/requirements/production.txt" ]; then
  "$PIP" install -r "$REPO_DIR/requirements/production.txt" --quiet
elif [ -f "$REPO_DIR/requirements.txt" ]; then
  "$PIP" install -r "$REPO_DIR/requirements.txt" --quiet
fi
echo "✓ Dependencies up to date"

# ── 3. migrate ────────────────────────────────────────────────────────────────
echo "--- Step 3/5: migrate ---"
DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" "$PYTHON" "$MANAGE" migrate --noinput
echo "✓ Migrations applied"

# ── 4. collectstatic ─────────────────────────────────────────────────────────
echo "--- Step 4/5: collectstatic ---"
DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" "$PYTHON" "$MANAGE" collectstatic --noinput --clear --verbosity=0
echo "✓ Static files collected"

# ── 5. restart service ───────────────────────────────────────────────────────
echo "--- Step 5/5: systemctl restart $SERVICE_NAME ---"
sudo systemctl restart "$SERVICE_NAME"
sleep 2
STATUS=$(sudo systemctl is-active "$SERVICE_NAME")
if [ "$STATUS" = "active" ]; then
  echo "✓ Service is running"
else
  echo "✗ Service failed to start! Status: $STATUS"
  sudo journalctl -u "$SERVICE_NAME" -n 30 --no-pager
  exit 1
fi

echo ""
echo "=== [EKAFY] Deployment of '$PROJECT_SLUG' SUCCEEDED ==="
echo "    Commit: $COMMIT"
echo "    Time:   $(date)"
