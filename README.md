# EKAFY DJ

EKAFY DJ is a Django-based VPS management dashboard. It is designed to run on a single Ubuntu server and help manage Django projects, deployments, services, logs, backups, monitoring, users, and audit records from one web interface.

The production installer in this repository deploys the app to:

```text
/srv/ekafydj
```

## What The App Includes

- Django dashboard with two-factor login support
- PostgreSQL database
- Redis cache and Celery broker
- Gunicorn application service
- Celery worker and Celery Beat services
- Nginx reverse proxy
- Project deployment, rollback, service control, log viewing, backups, monitoring, users, and audit pages
- DRF API under `/api/v1/`

## Repository Layout

```text
.
|-- dashboard/
|   |-- config/          Django settings, URLs, WSGI, ASGI, Celery
|   |-- api/             DRF router
|   |-- apps/
|   |   |-- audit/       Audit log
|   |   |-- backups/     Backup records and backup tasks
|   |   |-- core/        Shared helpers, permissions, context
|   |   |-- deployments/ Deployment history and task execution
|   |   |-- logs/        Log viewer
|   |   |-- monitoring/  System metrics and health checks
|   |   |-- projects/    Managed project CRUD
|   |   |-- services/    systemd service actions
|   |   `-- users/       Custom user model and roles
|   |-- scripts/         Server automation scripts
|   `-- templates/       Django templates
|-- requirements/
|   |-- base.txt
|   |-- development.txt
|   `-- production.txt
|-- install.sh           Clean production installer
|-- Makefile             Local development commands
`-- .env.example         Environment variable template
```

## Production Install

Run the installer on the Ubuntu server.

```bash
chmod +x install.sh
sudo ./install.sh
```

Important: `install.sh` is a clean installer. It removes and recreates `/srv/ekafydj`.

The installer currently does the following:

1. Stops `ekafydj-dashboard` if it exists.
2. Deletes `/srv/ekafydj`.
3. Installs system packages: Git, Curl, Nginx, Redis, PostgreSQL, Python venv/dev packages, build tools, libpq, and OpenSSL.
4. Creates the system user `ekafy`.
5. Clones the repository into `/srv/ekafydj`.
6. Creates `/srv/ekafydj/.venv`.
7. Installs production Python requirements, `phonenumbers`, and `gunicorn`.
8. Creates a fresh database password and Django `SECRET_KEY`.
9. Creates or updates:
   - database: `ekafydj_db`
   - database user: `ekafydj_user`
   - env file: `/srv/ekafydj/dashboard/.env`
10. Creates platform folders:
   - `/srv/ekafydj/logs`
   - `/srv/ekafydj/projects`
   - `/srv/ekafydj/backups`
   - `/srv/ekafydj/deployments`
11. Verifies the Django database connection.
12. Runs migrations.
13. Updates old Celery Beat task names if needed.
14. Collects static files.
15. Creates and enables systemd services:
   - `ekafydj-dashboard`
   - `ekafydj-celery`
   - `ekafydj-celery-beat`
16. Creates the Nginx site `/etc/nginx/sites-available/ekafydj`.
17. Enables the Nginx site and reloads Nginx.

After a successful install, open:

```text
http://SERVER_IP/account/login/
```

The installer runs the post-install verifier before printing the final completion message. If you want to run the verifier again manually:

```bash
sudo bash /srv/ekafydj/dashboard/scripts/verify_install.sh
```

To allow the verifier to apply safe repairs for common drift, such as resetting the PostgreSQL role password from `.env` and restarting EKAFY services:

```bash
sudo bash /srv/ekafydj/dashboard/scripts/verify_install.sh --fix
```

## Production Paths

| Purpose | Path |
| --- | --- |
| App root | `/srv/ekafydj` |
| Django project | `/srv/ekafydj/dashboard` |
| Virtualenv | `/srv/ekafydj/.venv` |
| Env file | `/srv/ekafydj/dashboard/.env` |
| Static files | `/srv/ekafydj/dashboard/staticfiles` |
| Media files | `/srv/ekafydj/dashboard/media` |
| Logs | `/srv/ekafydj/logs` |
| Managed projects | `/srv/ekafydj/projects` |
| Backups | `/srv/ekafydj/backups` |
| Deployments | `/srv/ekafydj/deployments` |

## Production Services

```bash
sudo systemctl status ekafydj-dashboard --no-pager
sudo systemctl status ekafydj-celery --no-pager
sudo systemctl status ekafydj-celery-beat --no-pager
```

Restart services:

```bash
sudo systemctl restart ekafydj-dashboard
sudo systemctl restart ekafydj-celery
sudo systemctl restart ekafydj-celery-beat
```

View logs:

```bash
sudo journalctl -u ekafydj-dashboard -n 120 --no-pager -l
sudo journalctl -u ekafydj-celery -n 120 --no-pager -l
sudo journalctl -u ekafydj-celery-beat -n 120 --no-pager -l
sudo tail -n 120 /srv/ekafydj/logs/ekafy_dashboard.log
```

## Create An Admin User

After installation:

```bash
cd /srv/ekafydj/dashboard
sudo -u ekafy env DJANGO_SETTINGS_MODULE=config.settings.production /srv/ekafydj/.venv/bin/python manage.py createsuperuser
```

Superusers are treated as admins by the app.

## Production Environment

The installer writes `/srv/ekafydj/dashboard/.env`.

Main values:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DB_NAME=ekafydj_db
DB_USER=ekafydj_user
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2
EKAFY_BASE_DIR=/srv/ekafydj
EKAFY_LOGS_DIR=/srv/ekafydj/logs
```

If PostgreSQL password authentication fails, reset the database role from the deployed `.env`:

```bash
cd /srv/ekafydj/dashboard

DB_USER=$(sudo awk -F= '/^DB_USER=/{gsub(/\r/,""); print $2}' .env)
DB_PASSWORD=$(sudo awk -F= '/^DB_PASSWORD=/{gsub(/\r/,""); print $2}' .env)
DB_NAME=$(sudo awk -F= '/^DB_NAME=/{gsub(/\r/,""); print $2}' .env)

sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo env PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "select current_user;"
```

## Local Development

The Makefile is for local development, not for the VPS production install.

Requirements:

- Python 3.12 available as `python3.12`
- PostgreSQL/Redis configured for your local `.env`
- Bash-like shell for the Makefile commands

Start from the repository root:

```bash
cp .env.example dashboard/.env
make setup
make dev
```

The development server runs on:

```text
http://localhost:8000
```

## Makefile Commands

The Makefile uses these defaults:

| Variable | Value | Meaning |
| --- | --- | --- |
| `PYTHON` | `python3.12` | Python executable used to create `.venv` |
| `VENV` | `.venv` | Local virtualenv folder |
| `SETTINGS` | `config.settings.development` | Default Django settings module for dev commands |
| `MANAGE` | `.venv/bin/python dashboard/manage.py` | Manage.py command path |
| `CELERY` | `.venv/bin/celery` | Celery executable path |

Available targets:

| Command | What it does | When to use it |
| --- | --- | --- |
| `make help` | Prints the command list | When you forget the target names |
| `make setup` | Runs `install`, `migrate`, then `createsuperuser` | First local setup |
| `make install` | Creates `.venv`, upgrades packaging tools, installs `requirements/development.txt` | Install or refresh local Python dependencies |
| `make dev` | Runs `python manage.py runserver 0.0.0.0:8000` using development settings | Start local Django server |
| `make migrate` | Runs Django migrations using development settings | Apply database migrations locally |
| `make makemigrations` | Creates new Django migration files | After changing models |
| `make createsuperuser` | Runs Django `createsuperuser` using development settings | Create a local admin user |
| `make collectstatic` | Runs `collectstatic` using production settings | Check/static-build production assets locally |
| `make test` | Runs pytest with testing settings | Full test run |
| `make test-fast` | Runs pytest quietly with `--no-cov` | Faster test run while developing |
| `make lint` | Runs Ruff on `dashboard/` and mypy on `dashboard/apps/` | Code quality checks |
| `make worker` | Starts a local Celery worker with development settings | Test background tasks locally |
| `make beat` | Starts a local Celery Beat scheduler with development settings | Test scheduled tasks locally |
| `make shell` | Opens Django `shell_plus` with development settings | Inspect or modify local app data |
| `make logs` | Tails `/srv/ekafydj/logs/ekafy_dashboard.log` | Watch production-style dashboard logs on a server |

Notes:

- `make setup` will ask for superuser details because it includes `createsuperuser`.
- `make collectstatic` uses production settings intentionally.
- `make logs` points to the production log path, so it is mainly useful on the server.
- Production deployment should use `sudo ./install.sh`, not `make setup`.

## URLs

| URL | Purpose |
| --- | --- |
| `/account/login/` | Login |
| `/account/logout/` | Logout |
| `/` | Dashboard index |
| `/list/` | Project list |
| `/new/` | Create project |
| `/deployments/` | Deployment list |
| `/services/<slug>/status/` | Project service status |
| `/logs/<slug>/` | Project log viewer |
| `/backups/` | Backup list |
| `/monitoring/` | Monitoring dashboard |
| `/users/` | User management |
| `/audit/` | Audit log |
| `/api/v1/` | REST API |
| `/django-admin/` | Django admin |

## REST API

Base path:

```text
/api/v1/
```

Registered API resources:

| Endpoint | Purpose |
| --- | --- |
| `/api/v1/projects/` | Projects |
| `/api/v1/deployments/` | Deployments |
| `/api/v1/backups/` | Backups |
| `/api/v1/metrics/` | System metrics |

Authentication is handled by Django session auth or JWT, depending on the endpoint/client.

## Roles

| Role | Access |
| --- | --- |
| Admin | Full access. Superusers are also treated as admins. |
| Operator | Operational access such as deploys, restarts, backups, and logs. |
| Viewer | Read-only dashboard access. |

## Common Troubleshooting

Check whether the app is reachable through Gunicorn:

```bash
curl -fsS -o /tmp/ekafydj-login-gunicorn.html http://127.0.0.1:8000/account/login/?next=/
```

Check whether it is reachable through Nginx:

```bash
curl -fsS -o /tmp/ekafydj-login-nginx.html http://127.0.0.1/account/login/?next=/
```

To test the public IP host header through local Nginx:

```bash
APP_PUBLIC_HOST=45.130.164.233 sudo -E bash /srv/ekafydj/dashboard/scripts/verify_install.sh
```

If Nginx warns about duplicate `server_name _`, list enabled sites:

```bash
ls -l /etc/nginx/sites-enabled/
sudo grep -R "server_name _" -n /etc/nginx/sites-enabled /etc/nginx/sites-available
```

If login gives HTTP 500, read the Django traceback:

```bash
sudo journalctl -u ekafydj-dashboard -n 120 --no-pager -l
sudo tail -n 120 /srv/ekafydj/logs/ekafy_dashboard.log
```

If Celery Beat sends unregistered task names, rerun the installer or run migrations from `/srv/ekafydj/dashboard`; the installer updates old Beat task names after migration.

## License

Proprietary. All rights reserved.
