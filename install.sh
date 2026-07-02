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
sudo systemctl stop "${APP_NAME}-dashboard" || true

echo "🧹 Cleaning old installation..."
sudo rm -rf "$APP_DIR"

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

# DB_PASS=$(openssl rand -hex 24)
# SECRET_KEY=$(openssl rand -hex 48)

DB_PASS=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 48)

sudo -u postgres psql -tc \
"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
sudo -u postgres psql -c \
"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres psql -c \
"ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres createdb "${DB_NAME}" -O "${DB_USER}" 2>/dev/null || true
sudo -u postgres psql -c \
"ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c \
"GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo "DB OK: ${DB_NAME}"

sudo tee "${ENV_FILE}" > /dev/null <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=*
DJANGO_SETTINGS_MODULE=config.settings.production
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EKAFY_BASE_DIR=${APP_DIR}
EKAFY_PROJECTS_DIR=${APP_DIR}/projects
EKAFY_LOGS_DIR=${APP_DIR}/logs
EKAFY_BACKUPS_DIR=${APP_DIR}/backups
EKAFY_DEPLOYMENTS_DIR=${APP_DIR}/deployments
EKAFY_SCRIPTS_DIR=${APP_DIR}/dashboard/scripts
USE_S3_BACKUPS=False
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EOF
sudo sed -i 's/\r$//' "${ENV_FILE}"
sudo chown "${APP_USER}:${APP_GROUP}" "${ENV_FILE}"
sudo chmod 640 "${ENV_FILE}"
sudo mkdir -p "${APP_DIR}/logs" "${APP_DIR}/projects" "${APP_DIR}/backups" "${APP_DIR}/deployments"
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}/logs" "${APP_DIR}/projects" "${APP_DIR}/backups" "${APP_DIR}/deployments"

########################################
# 8. DJANGO SETUP (CLEAN ORDER)
########################################
echo "🧱 Running Django setup..."

cd "${APP_DIR}/dashboard"

DJANGO_ENV=(
    DJANGO_SETTINGS_MODULE=config.settings.production
    DB_NAME="${DB_NAME}"
    DB_USER="${DB_USER}"
    DB_PASSWORD="${DB_PASS}"
    DB_HOST=localhost
    DB_PORT=5432
)

sudo -u "${APP_USER}" env "${DJANGO_ENV[@]}" "${VENV_DIR}/bin/python" manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('Django DB OK')"

sudo -u "${APP_USER}" env "${DJANGO_ENV[@]}" "${VENV_DIR}/bin/python" manage.py migrate

sudo -u "${APP_USER}" env "${DJANGO_ENV[@]}" "${VENV_DIR}/bin/python" manage.py shell -c \
    "from django_celery_beat.models import PeriodicTask; mapping={'apps.monitoring.tasks.collect_system_metrics':'monitoring.collect_system_metrics','apps.monitoring.tasks.check_project_health':'monitoring.check_project_health','apps.backups.tasks.run_scheduled_backups':'backups.run_scheduled_backups','apps.deployments.tasks.cleanup_old_deployment_logs':'deployments.cleanup_old_deployment_logs','apps.monitoring.tasks.cleanup_old_metrics':'monitoring.cleanup_old_metrics'}; [PeriodicTask.objects.filter(task=old).update(task=new) for old,new in mapping.items()]; print('Celery beat task names OK')"

sudo -u "${APP_USER}" env "${DJANGO_ENV[@]}" "${VENV_DIR}/bin/python" manage.py collectstatic --noinput || true

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

sudo tee /etc/systemd/system/${APP_NAME}-celery.service > /dev/null <<EOF
[Unit]
Description=EKAFY Celery Worker
After=network.target redis.service postgresql.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery -A config.celery worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/${APP_NAME}-celery-beat.service > /dev/null <<EOF
[Unit]
Description=EKAFY Celery Beat
After=network.target redis.service postgresql.service

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/dashboard
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery -A config.celery beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

########################################
# 10. ENABLE SERVICE
########################################
sudo systemctl daemon-reload
sudo systemctl enable --now ${APP_NAME}-dashboard
sudo systemctl enable --now ${APP_NAME}-celery
sudo systemctl enable --now ${APP_NAME}-celery-beat

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
