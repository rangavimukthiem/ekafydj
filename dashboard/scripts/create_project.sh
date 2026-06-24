#!/usr/bin/env bash
# =============================================================================
# EKAFY — create_project.sh
# Scaffolds a new managed Django project on the VPS.
#
# Usage:
#   create_project.sh <slug> <git_url> <git_branch> <python_version> \
#                     <db_name> <db_user> <db_password> <projects_base_dir>
#
# Run as: sudo -u ekafy bash create_project.sh ...
# =============================================================================
set -euo pipefail

LOG_FILE="/srv/ekafy/logs/scaffold_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

PROJECT_SLUG="${1:?SLUG required}"
GIT_URL="${2:?GIT_URL required}"
GIT_BRANCH="${3:-main}"
PYTHON_VERSION="${4:-3.12}"
DB_NAME="${5:?DB_NAME required}"
DB_USER="${6:?DB_USER required}"
DB_PASSWORD="${7:?DB_PASSWORD required}"
PROJECTS_BASE="${8:-/srv/ekafy/projects}"

PROJECT_DIR="$PROJECTS_BASE/$PROJECT_SLUG"
REPO_DIR="$PROJECT_DIR/repo"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"
MEDIA_DIR="$PROJECT_DIR/media"
STATIC_DIR="$PROJECT_DIR/static"

echo "=== [EKAFY] Scaffolding project: $PROJECT_SLUG ==="
echo "    Dir:    $PROJECT_DIR"
echo "    Repo:   $GIT_URL ($GIT_BRANCH)"
echo "    Python: $PYTHON_VERSION"
echo "    DB:     $DB_NAME"

# ── 1. Create directory structure ────────────────────────────────────────────
echo "--- Step 1: Creating directories ---"
mkdir -p "$REPO_DIR" "$LOG_DIR" "$MEDIA_DIR" "$STATIC_DIR"
echo "✓ Directories created"

# ── 2. Clone repository ───────────────────────────────────────────────────────
echo "--- Step 2: Cloning repository ---"
if [ -d "$REPO_DIR/.git" ]; then
  echo "  Repository already exists — pulling latest"
  git -C "$REPO_DIR" fetch origin
  git -C "$REPO_DIR" checkout "$GIT_BRANCH"
  git -C "$REPO_DIR" pull origin "$GIT_BRANCH"
else
  git clone --branch "$GIT_BRANCH" --single-branch "$GIT_URL" "$REPO_DIR"
fi
echo "✓ Repository ready"

# ── 3. Create virtual environment ────────────────────────────────────────────
echo "--- Step 3: Creating virtualenv (Python $PYTHON_VERSION) ---"
PYTHON_BIN="python$PYTHON_VERSION"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools --quiet
echo "✓ Virtualenv created"

# ── 4. Install dependencies ───────────────────────────────────────────────────
echo "--- Step 4: Installing dependencies ---"
if [ -f "$REPO_DIR/requirements/production.txt" ]; then
  "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements/production.txt" --quiet
elif [ -f "$REPO_DIR/requirements.txt" ]; then
  "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet
else
  echo "  WARNING: No requirements file found"
fi
echo "✓ Dependencies installed"

# ── 5. Create PostgreSQL database and user ────────────────────────────────────
echo "--- Step 5: Creating PostgreSQL database ---"
if sudo -u postgres psql -lqt | cut -d\| -f1 | grep -qw "$DB_NAME"; then
  echo "  Database '$DB_NAME' already exists — skipping"
else
  sudo -u postgres psql -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';"
  sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"
  echo "✓ Database and user created"
fi

# ── 6. Set permissions ────────────────────────────────────────────────────────
echo "--- Step 6: Setting permissions ---"
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
echo "✓ Permissions set"

echo ""
echo "=== [EKAFY] Project '$PROJECT_SLUG' scaffolded successfully ==="
echo "    Next: create_systemd_service.sh and create_nginx_conf.sh"
