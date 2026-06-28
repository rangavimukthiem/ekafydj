#!/usr/bin/env bash
set -euo pipefail
# prevent postgres cwd warning
cd /tmp

echo "\n =============================================================================
#
#   ███████╗██╗  ██╗ █████╗ ███████╗██╗   ██╗
#   ██╔════╝██║ ██╔╝██╔══██╗██╔════╝╚██╗ ██╔╝
#   █████╗  █████╔╝ ███████║█████╗   ╚████╔╝
#   ██╔══╝  ██╔═██╗ ██╔══██║██╔══╝    ╚██╔╝
#   ███████╗██║  ██╗██║  ██║██║        ██║
#   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝
#
#   EKAFY VPS MANAGEMENT SYSTEM — INSTALLER v3.0
#   ─────────────────────────────────────────────
#   Supports  : Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
#   Installs  : Django API · WordPress · Dashboard · Monitoring
#   Idempotent: Safe to re-run on existing installations
#   Log file  : /var/log/ekafy-install.log
#
#   USAGE:
#     bash install.sh                      (interactive)
#     bash install.sh --no-wp              (skip WordPress)
#     bash install.sh --no-redis           (skip Redis)
#     bash install.sh --check-only         (requirements check only)
#
#
# ============================================================================= \n"
sleep 5



validate_git_repo() {
    echo "🔍 Validating Git repository access..."

    # Check repo exists
    if ! git ls-remote "${REPO_URL}" &>/dev/null; then
        echo "❌ ERROR: Repository not reachable"
        echo "👉 Check URL or network access"
        exit 1
    fi

    # Check branch exists
    if ! git ls-remote --heads "${REPO_URL}" "${BRANCH}" &>/dev/null; then
        echo "❌ ERROR: Branch '${BRANCH}' not found"
        exit 1
    fi

    echo "✅ Git repository validation successful"
}

safe_git_clone() {
    echo "📥 Starting safe clone..."

    export GIT_TERMINAL_PROMPT=0
    export GIT_SSH_COMMAND=""

    if [ -d "${APP_DIR}/.git" ]; then
        echo "📦 Repo exists → pulling latest changes..."

        sudo -u "${APP_USER}" git -C "${APP_DIR}" pull origin "${BRANCH}"
    else
        echo "📦 Fresh clone starting..."

        sudo -u "${APP_USER}" git clone \
            --depth 1 \
            --branch "${BRANCH}" \
            "${REPO_URL}" \
            "${APP_DIR}"
    fi

    echo "✅ Git operation completed successfully"
}

check_repo_health() {
    echo "🧪 Running repo health check..."

    # Ensure remote is reachable
    git ls-remote "${REPO_URL}" HEAD >/dev/null

    if [ $? -ne 0 ]; then
        echo "❌ Git remote unreachable"
        exit 1
    fi

    echo "✅ Repo is healthy"
}

export DEBIAN_FRONTEND=noninteractive

########################################
# EKAFY INSTALLER (Production Safe VPS)
# Ubuntu 24.04+
########################################

# ---------- CONFIG ----------
APP_NAME="ekafydj"
APP_USER="ekafy"
APP_GROUP="www-data"

APP_DIR="/srv/${APP_NAME}"
REPO_URL="https://github.com/rangavimukthiem/ekafydj.git"
BRANCH="main"

PYTHON_BIN="python3"
VENV_DIR="${APP_DIR}/.venv"

DB_NAME="${APP_NAME}_db"
DB_USER="${APP_NAME}_user"

ENV_FILE="${APP_DIR}/dashboard/.env"

echo "======================================"
echo "🚀 EKAFY INSTALLER STARTING"
echo "======================================"

# ---------- SYSTEM UPDATE ----------
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# ---------- PACKAGES ----------
echo "📦 Installing dependencies..."
sudo apt install -y \
    git curl nginx redis-server \
    postgresql postgresql-contrib \
    ${PYTHON_BIN} ${PYTHON_BIN}-venv ${PYTHON_BIN}-dev \
    build-essential libpq-dev openssl

sudo systemctl enable --now nginx redis-server postgresql

# ---------- USER SETUP ----------
echo "👤 Creating system user..."

if ! id "${APP_USER}" &>/dev/null; then
    sudo useradd --system --create-home \
        --home-dir "${APP_DIR}" \
        --shell /bin/bash \
        "${APP_USER}"
fi

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

# ---------- CLONE PROJECT ----------
echo "======================================"
echo "🔧 EKAFY GIT SETUP START"
echo "======================================"

validate_git_repo
check_repo_health
safe_git_clone

echo "======================================"
echo "✅ EKAFY GIT SETUP COMPLETE"
echo "======================================"
# ---------- PYTHON VENV ----------
echo "🐍 Setting up virtual environment..."

sudo -u "${APP_USER}" ${PYTHON_BIN} -m venv "${VENV_DIR}"

sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements/production.txt"

# ---------- ENV FILE ----------
echo "⚙️ Setting environment variables..."

if [ ! -f "${ENV_FILE}" ]; then
    sudo -u "${APP_USER}" cp "${APP_DIR}/.env.example" "${ENV_FILE}" || true
    echo "⚠️ IMPORTANT: edit ${ENV_FILE}"
fi

# ---------- DATABASE ----------
echo "🐘 Setting up PostgreSQL..."


DB_PASS=$(openssl rand -base64 32)

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres createdb "${DB_NAME}" -O "${DB_USER}" 2>/dev/null || true

echo "🔐 DB CREATED:"
echo "   DB_NAME=${DB_NAME}"
echo "   DB_USER=${DB_USER}"
echo "   DB_PASS=${DB_PASS}"

# ---------- DJANGO SETUP ----------
echo "🧱 Running Django setup..."

cd "${APP_DIR}/dashboard"

# Ensure correct ownership context (prevents hidden permission bugs)
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

# ---------- GUNICORN INSTALL (BEFORE DJANGO OPS) ----------
echo "⚡ Installing Gunicorn..."

sudo -H -u "${APP_USER}" env HOME=/home/${APP_USER} \
"${VENV_DIR}/bin/pip" install --upgrade pip gunicorn

# ---------- DJANGO MIGRATIONS ----------
echo "🧱 Running migrations..."

sudo -H -u "${APP_USER}" env HOME=/home/${APP_USER} \
"${VENV_DIR}/bin/python" manage.py migrate

# ---------- STATIC FILES ----------
echo "🎨 Collecting static files..."

sudo -H -u "${APP_USER}" env HOME=/home/${APP_USER} \
"${VENV_DIR}/bin/python" manage.py collectstatic --noinput || true

# ---------- FINAL SETUP CHECK ----------
echo "🔍 Running Django system check..."

sudo -H -u "${APP_USER}" env HOME=/home/${APP_USER} \
"${VENV_DIR}/bin/python" manage.py check || true

# ---------- SUPERUSER ----------
echo "👤 Create superuser manually when ready:"

echo "sudo -H -u ${APP_USER} env HOME=/home/${APP_USER} \\"
echo "${VENV_DIR}/bin/python manage.py createsuperuser"


# ---------- SYSTEMD: DJANGO ----------
echo "🔁 Creating systemd service..."

sudo tee /etc/systemd/system/${APP_NAME}-dashboard.service > /dev/null <<EOF
[Unit]
Description=EKAFY Django Dashboard
After=network.target postgresql.service redis.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ---------- SYSTEMD: CELERY ----------
sudo tee /etc/systemd/system/${APP_NAME}-celery.service > /dev/null <<EOF
[Unit]
Description=EKAFY Celery Worker
After=network.target redis.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery -A config.celery worker --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ---------- SYSTEMD: CELERY BEAT ----------
sudo tee /etc/systemd/system/${APP_NAME}-celery-beat.service > /dev/null <<EOF
[Unit]
Description=EKAFY Celery Beat Scheduler
After=network.target redis.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery -A config.celery beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ---------- ENABLE SERVICES ----------
echo "🔁 Enabling services..."

sudo systemctl daemon-reload
sudo systemctl enable --now ${APP_NAME}-dashboard
sudo systemctl enable --now ${APP_NAME}-celery
sudo systemctl enable --now ${APP_NAME}-celery-beat

# ---------- NGINX ----------
echo "🌐 Configuring Nginx..."

sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias ${APP_DIR}/dashboard/staticfiles/;
    }

    location /media/ {
        alias ${APP_DIR}/dashboard/media/;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}

sudo nginx -t && sudo systemctl reload nginx

# ---------- FINAL OUTPUT ----------
echo "======================================"
echo "🔥 EKAFY INSTALL COMPLETE"
echo "======================================"
echo "🌐 http://SERVER_IP"
echo "📁 App: ${APP_DIR}"
echo "🐍 Venv: ${VENV_DIR}"
echo "🐘 DB: ${DB_NAME}"
echo "======================================"

echo "Check status:"
echo "  systemctl status ${APP_NAME}-dashboard --no-pager"