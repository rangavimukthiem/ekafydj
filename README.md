# EKAFY — VPS Application Management Platform

> Deploy, monitor, restart, backup, and manage multiple Django projects running on a single Ubuntu 24.04 LTS VPS.

---

## Architecture

```
/srv/ekafy/
├── dashboard/          ← EKAFY Django project (this codebase)
│   ├── config/         ← Settings, urls, wsgi, asgi, celery
│   ├── apps/
│   │   ├── core/       ← Base models, exceptions, utils
│   │   ├── projects/   ← Managed project CRUD
│   │   ├── deployments/← Git pull → pip → migrate → restart pipeline
│   │   ├── services/   ← Systemd start/stop/restart/status
│   │   ├── logs/       ← journalctl + file log viewer
│   │   ├── backups/    ← pg_dump, media archive, S3 upload
│   │   ├── monitoring/ ← CPU/RAM/disk metrics, health checks
│   │   ├── users/      ← RBAC user management, invitations
│   │   └── audit/      ← Immutable audit log
│   ├── api/            ← DRF REST API (v1)
│   ├── templates/      ← TailwindCSS + HTMX + AlpineJS
│   └── scripts/        ← Bash automation scripts
├── projects/           ← Managed project roots
├── logs/               ← Aggregated logs
├── backups/            ← Backup archives
└── deployments/        ← Deployment manifests
```

---

## Prerequisites

- Ubuntu 24.04 LTS
- Python 3.12
- PostgreSQL 16
- Redis 7
- Nginx
- Node.js 20+ (for TailwindCSS build)

---

## Quick Start (Development)

```bash
# 1. Clone the repo
git clone git@github.com:yourorg/ekafy.git /srv/ekafy
cd /srv/ekafy

# 2. Copy environment file
cp .env.example dashboard/.env
# Edit dashboard/.env with your values

# 3. First-time setup (creates venv, installs deps, migrates, creates superuser)
make setup

# 4. Start development server
make dev
# → http://localhost:8000

# 5. Start Celery worker (in a separate terminal)
make worker

# 6. Start Celery beat scheduler (in a separate terminal)
make beat
```

---

## Production Deployment on Ubuntu 24.04

### 1. System packages

```bash
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    postgresql-16 libpq-dev \
    redis-server nginx git curl

sudo systemctl enable --now postgresql redis-server nginx
```

### 2. Create ekafy system user

```bash
sudo useradd --system --home /srv/ekafy --shell /bin/bash ekafy
sudo mkdir -p /srv/ekafy
sudo chown ekafy:ekafy /srv/ekafy
```

### 3. Clone and configure

```bash
sudo -u ekafy git clone git@github.com:yourorg/ekafy.git /srv/ekafy
cd /srv/ekafy
sudo -u ekafy cp .env.example dashboard/.env
sudo -u ekafy nano dashboard/.env  # Fill in production values
```

### 4. Setup virtualenv and dependencies

```bash
sudo -u ekafy python3.12 -m venv .venv
sudo -u ekafy .venv/bin/pip install -r requirements/production.txt
```

### 5. Database and migrations

```bash
sudo -u postgres createuser ekafy_user
sudo -u postgres createdb ekafy_db -O ekafy_user
sudo -u postgres psql -c "ALTER USER ekafy_user WITH PASSWORD 'your-password';"

cd /srv/ekafy/dashboard
sudo -u ekafy DJANGO_SETTINGS_MODULE=config.settings.production \
    ../.venv/bin/python manage.py migrate
sudo -u ekafy DJANGO_SETTINGS_MODULE=config.settings.production \
    ../.venv/bin/python manage.py createsuperuser
sudo -u ekafy DJANGO_SETTINGS_MODULE=config.settings.production \
    ../.venv/bin/python manage.py collectstatic --noinput
```

### 6. Systemd units for EKAFY dashboard

```bash
# Gunicorn socket
sudo tee /etc/systemd/system/ekafy-dashboard.socket <<EOF
[Unit]
Description=EKAFY Dashboard Gunicorn Socket

[Socket]
ListenStream=/run/gunicorn/ekafy-dashboard.sock

[Install]
WantedBy=sockets.target
EOF

# Gunicorn service
sudo tee /etc/systemd/system/ekafy-dashboard.service <<EOF
[Unit]
Description=EKAFY Dashboard Gunicorn
Requires=ekafy-dashboard.socket
After=network.target

[Service]
Type=notify
User=ekafy
Group=www-data
WorkingDirectory=/srv/ekafy/dashboard
ExecStart=/srv/ekafy/.venv/bin/gunicorn \
    --workers 4 --bind unix:/run/gunicorn/ekafy-dashboard.sock \
    --log-level info \
    --access-logfile /srv/ekafy/logs/dashboard_access.log \
    config.wsgi:application
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
EnvironmentFile=/srv/ekafy/dashboard/.env
Restart=on-failure
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Celery worker
sudo tee /etc/systemd/system/ekafy-celery.service <<EOF
[Unit]
Description=EKAFY Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=ekafy
Group=ekafy
WorkingDirectory=/srv/ekafy/dashboard
ExecStart=/srv/ekafy/.venv/bin/celery -A config.celery worker --loglevel=info --concurrency=4 --detach
EnvironmentFile=/srv/ekafy/dashboard/.env
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Celery beat
sudo tee /etc/systemd/system/ekafy-celery-beat.service <<EOF
[Unit]
Description=EKAFY Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=ekafy
WorkingDirectory=/srv/ekafy/dashboard
ExecStart=/srv/ekafy/.venv/bin/celery -A config.celery beat --loglevel=info
EnvironmentFile=/srv/ekafy/dashboard/.env
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ekafy-dashboard.socket ekafy-dashboard.service
sudo systemctl enable --now ekafy-celery ekafy-celery-beat
```

### 7. Nginx configuration

```bash
sudo tee /etc/nginx/sites-available/ekafy <<EOF
upstream ekafy_dashboard {
    server unix:/run/gunicorn/ekafy-dashboard.sock fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location /static/ {
        alias /srv/ekafy/dashboard/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /srv/ekafy/dashboard/media/;
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://ekafy_dashboard;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/ekafy /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Enable HTTPS
sudo certbot --nginx -d your-domain.com
```

### 8. Sudo permissions for EKAFY scripts

```bash
# Allow ekafy user to manage project services and run scripts
sudo tee /etc/sudoers.d/ekafy <<EOF
ekafy ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ekafy-*.service
ekafy ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ekafy-*.service
ekafy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ekafy-*.service
ekafy ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload ekafy-*.service
ekafy ALL=(ALL) NOPASSWD: /usr/bin/systemctl status ekafy-*.service
ekafy ALL=(ALL) NOPASSWD: /usr/bin/journalctl
ekafy ALL=(ALL) NOPASSWD: /usr/sbin/nginx
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ekafy-*.service
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ekafy-*.service
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ekafy-*.service
EOF
sudo chmod 440 /etc/sudoers.d/ekafy
```

---

## Development Commands

| Command | Description |
|---------|-------------|
| `make setup` | First-time setup (venv + deps + db + superuser) |
| `make dev` | Start development server on :8000 |
| `make test` | Run full pytest suite with coverage |
| `make test-fast` | Run tests without coverage (faster) |
| `make lint` | ruff + mypy checks |
| `make migrate` | Apply Django migrations |
| `make worker` | Start Celery worker |
| `make beat` | Start Celery beat scheduler |
| `make shell` | Django shell_plus |
| `make logs` | Tail EKAFY dashboard log |

---

## REST API

Base URL: `/api/v1/`

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/v1/projects/` | GET, POST | List / create projects |
| `/api/v1/projects/{slug}/` | GET, PUT, DELETE | Project detail |
| `/api/v1/projects/{slug}/deploy/` | POST | Trigger deployment |
| `/api/v1/projects/{slug}/status/` | GET | Systemd service status |
| `/api/v1/deployments/` | GET | List deployments |
| `/api/v1/backups/` | GET | List backups |
| `/api/v1/backups/trigger/` | POST | Trigger backup |
| `/api/v1/metrics/` | GET | System metrics (last 500) |

Authentication: Session or JWT (`Authorization: Bearer <token>`)

---

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: create/delete projects, manage users, view audit log |
| **Operator** | Deploy, restart, backup, view logs, create projects |
| **Viewer** | Read-only: view dashboard, projects, deployments, backups |

---

## License

Proprietary — All rights reserved.
