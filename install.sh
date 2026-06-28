#!/usr/bin/env bash
set -euo pipefail

########################################
# EKAFY INSTALLER v3.1 (CLEAN EDITION)
########################################

cd /tmp


# ---------- CONFIG ----------
APP_NAME="ekafydj"
APP_USER="ekafy"
APP_GROUP="www-data"

APP_DIR="/srv/${APP_NAME}"
REPO_URL="https://github.com/rangavimukthiem/ekafydj.git"

BRANCH="main"
echo "🛑 Stopping service..."
sudo systemctl stop ekafy || true

echo "🧹 Cleaning old installation..."
sudo rm -rf "$APP_DIR

PYTHON_BIN="python3"
VENV_DIR="${APP_DIR}/.venv"

DB_NAME="${APP_NAME}_db"
DB_USER="${APP_NAME}_user"

ENV_FILE="${APP_DIR}/dashboard/.env"

export DEBIAN_FRONTEND=noninteractive
export HOME="${APP_DIR}"

echo "======================================"
echo "🚀 EKAFY INSTALLER v3.1 (CLEAN)"
echo "======================================"

########################################
# 1. SYSTEM DEPENDENCIES
########################################
echo "📦 Installing system packages..."

sudo apt update -y && sudo apt upgrade -y

sudo apt install -y \
    git curl nginx redis-server \
    postgresql postgresql-contrib \
    ${PYTHON_BIN} ${PYTHON_BIN}-venv ${PYTHON_BIN}-dev \
    build-essential libpq-dev openssl

sudo systemctl enable --now nginx redis-server postgresql

########################################
# 2. USER SETUP (SAFE)
########################################
echo "👤 Setting up user..."

if ! id "${APP_USER}" &>/dev/null; then
    sudo useradd --system --create-home \
        --home-dir "${APP_DIR}" \
        --shell /bin/bash \
        "${APP_USER}"
fi

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

########################################
# 3. GIT CLONE (OWNED BY APP USER)
########################################
echo "📥 Cloning/Updating Git repo..."

if [ -d "${APP_DIR}/.git" ]; then
    sudo -u "${APP_USER}" git -C "${APP_DIR}" reset --hard
    sudo -u "${APP_USER}" git -C "${APP_DIR}" clean -fd
    sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch origin
    sudo -u "${APP_USER}" git -C "${APP_DIR}" checkout "${BRANCH}"
    sudo -u "${APP_USER}" git -C "${APP_DIR}" pull origin "${BRANCH}"
else
    sudo -u "${APP_USER}" git clone \
        --depth 1 \
        --branch "${BRANCH}" \
        "${REPO_URL}" \
        "${APP_DIR}"
fi

########################################
# 4. VIRTUAL ENV (OWNED PROPERLY)
########################################
echo "🐍 Creating virtual environment..."

sudo -u "${APP_USER}" ${PYTHON_BIN} -m venv "${VENV_DIR}"

sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip

########################################
# 5. PYTHON DEPENDENCIES (FIXED ORDER)
########################################
echo "📦 Installing Python dependencies..."

# core requirements first
sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements/production.txt"

# missing hard dependencies (IMPORTANT FIX)
sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install \
    phonenumbers \
    gunicorn

########################################
# 6. ENV FILE
########################################
echo "⚙️ Setting environment variables..."

if [ ! -f "${ENV_FILE}" ]; then
    sudo -u "${APP_USER}" cp "${APP_DIR}/.env.example" "${ENV_FILE}" || true
    echo "⚠️ Edit env file: ${ENV_FILE}"
fi

########################################
# 7. POSTGRES SETUP
########################################
echo "🐘 Setting up database..."

DB_PASS=$(openssl rand -base64 32)

sudo -u postgres psql -tc \
"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
sudo -u postgres psql -c \
"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres createdb "${DB_NAME}" -O "${DB_USER}" 2>/dev/null || true

echo "DB OK: ${DB_NAME}"

########################################
# 8. DJANGO SETUP (CLEAN ORDER)
########################################
echo "🧱 Running Django setup..."

cd "${APP_DIR}/dashboard"

sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" manage.py migrate

sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" manage.py collectstatic --noinput || true

########################################
# 9. SYSTEMD SERVICES
########################################
echo "🔁 Creating systemd services..."

sudo tee /etc/systemd/system/${APP_NAME}-dashboard.service > /dev/null <<EOF
[Unit]
Description=EKAFY Django
After=network.target postgresql.service redis.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
EOF

########################################
# 10. ENABLE SERVICE
########################################
sudo systemctl daemon-reload
sudo systemctl enable --now ${APP_NAME}-dashboard

########################################
# 11. NGINX
########################################
echo "🌐 Configuring Nginx..."

sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias ${APP_DIR}/dashboard/staticfiles/;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}

sudo nginx -t && sudo systemctl reload nginx

########################################
# DONE
########################################
echo "======================================"
echo "🔥 INSTALLER v3.1 COMPLETE"
echo "======================================"
echo "URL: http://SERVER_IP"
echo "APP: ${APP_DIR}"
echo "VENV: ${VENV_DIR}"
echo "DB: ${DB_NAME}"
echo "======================================"