# EKAFY — Production-Ready VPS Management Platform

## Overview

EKAFY is a Django-based SaaS-style dashboard that runs on a Ubuntu 24.04 LTS VPS and allows administrators to deploy, monitor, restart, backup, and manage multiple Django projects running on the same server. The dashboard itself is one of the managed applications.

**Tech Stack**: Python 3.12 · Django 5.x · DRF · PostgreSQL · Redis · Nginx · Gunicorn · Systemd · TailwindCSS · HTMX · AlpineJS

---

## Architecture Overview

```
/srv/ekafy/
├── dashboard/              ← EKAFY Django project (the manager)
│   ├── config/             ← Django settings, urls, wsgi, asgi
│   ├── apps/
│   │   ├── core/           ← Base models, mixins, utils
│   │   ├── projects/       ← Managed project CRUD & metadata
│   │   ├── deployments/    ← Git pull, migrate, collectstatic, restart
│   │   ├── services/       ← Systemd service control (start/stop/restart/status)
│   │   ├── logs/           ← Live log tail & log archive viewer
│   │   ├── backups/        ← DB dump & media backup scheduling
│   │   ├── monitoring/     ← CPU, RAM, disk, per-project health checks
│   │   ├── users/          ← Admin user management, RBAC, 2FA
│   │   └── audit/          ← Immutable audit log for all actions
│   ├── api/                ← DRF ViewSets & serializers
│   ├── templates/          ← Jinja2/Django templates
│   ├── static/             ← TailwindCSS build output, JS
│   ├── scripts/            ← Bash helpers called by the platform
│   └── manage.py
├── projects/               ← Managed Django project roots live here
│   └── <project-slug>/
│       ├── .venv/
│       ├── repo/           ← git clone target
│       └── ...
├── logs/                   ← Aggregated log symlinks
├── backups/                ← Backup archives
└── deployments/            ← Deployment artefacts & rollback manifests
```

---

## Clean Architecture Layers

```
┌──────────────────────────────────────────────────────┐
│  Presentation (Templates + HTMX + AlpineJS)         │
│  API (DRF ViewSets)                                  │
├──────────────────────────────────────────────────────┤
│  Application / Service Layer                         │
│  (DeploymentService, BackupService, LogService …)    │
├──────────────────────────────────────────────────────┤
│  Domain / Repository Layer                           │
│  (ProjectRepository, DeploymentRepository …)         │
├──────────────────────────────────────────────────────┤
│  Infrastructure                                      │
│  (PostgreSQL, Redis, Systemd, Shell scripts, Nginx)  │
└──────────────────────────────────────────────────────┘
```

---

## Proposed Changes — Complete File Structure

### `/srv/ekafy/dashboard/` — Django Project Root

#### [NEW] `config/settings/`
- `base.py` — Installed apps, middleware, auth, static/media, logging
- `development.py` — DEBUG=True, SQLite fallback, console email
- `production.py` — PostgreSQL, Redis cache, SECURE_* headers, Celery
- `testing.py` — In-memory SQLite, fast password hasher

#### [NEW] `config/`
- `urls.py` — Root URL dispatcher (dashboard + API + HTMX partials)
- `wsgi.py` / `asgi.py`
- `celery.py` — Celery app with Redis broker

---

### Django Apps

#### [NEW] `apps/core/`
| File | Purpose |
|------|---------|
| `models.py` | `TimestampedModel`, `UUIDModel` base classes |
| `mixins.py` | `ServiceMixin`, `AuditableMixin` |
| `exceptions.py` | Domain exceptions (`DeploymentError`, `BackupError` …) |
| `utils.py` | Shell runner, slug generator, path helpers |
| `permissions.py` | Custom DRF permissions |

#### [NEW] `apps/projects/`
| File | Purpose |
|------|---------|
| `models.py` | `Project` (slug, git_url, branch, venv_path, db_name, systemd_service, nginx_conf, status) |
| `repositories.py` | `ProjectRepository` — DB queries abstracted |
| `services.py` | `ProjectService` — create project dir structure, init venv, create DB |
| `views.py` | List / Detail / Create / Edit HTMX views |
| `api/` | DRF serializers + ViewSets |
| `forms.py` | Django forms for project creation |
| `urls.py` | URL patterns |

#### [NEW] `apps/deployments/`
| File | Purpose |
|------|---------|
| `models.py` | `Deployment` (project FK, commit_hash, status, triggered_by, started_at, finished_at, log) |
| `repositories.py` | `DeploymentRepository` |
| `services.py` | `DeploymentService.deploy()` — git pull → pip install → migrate → collectstatic → restart |
| `tasks.py` | Celery tasks for async deployment |
| `views.py` | Trigger deploy, live log stream (SSE/HTMX polling) |
| `api/` | DRF endpoints |

#### [NEW] `apps/services/`
| File | Purpose |
|------|---------|
| `models.py` | `ServiceStatus` snapshot model |
| `services.py` | `SystemdService` — wraps `systemctl` calls via subprocess |
| `views.py` | Start / Stop / Restart / Status HTMX views |
| `api/` | DRF endpoints |

#### [NEW] `apps/logs/`
| File | Purpose |
|------|---------|
| `services.py` | `LogService` — tail journalctl / file logs, stream via SSE |
| `views.py` | Log viewer with filter & search |
| `api/` | REST endpoint returning paginated log lines |

#### [NEW] `apps/backups/`
| File | Purpose |
|------|---------|
| `models.py` | `Backup` (project, type=db/media/full, size, path, status, created_at) |
| `repositories.py` | `BackupRepository` |
| `services.py` | `BackupService` — `pg_dump`, tar media, upload to S3 (optional) |
| `tasks.py` | Celery periodic tasks (cron schedules per project) |
| `views.py` | List, trigger, download, delete backups |
| `api/` | DRF endpoints |

#### [NEW] `apps/monitoring/`
| File | Purpose |
|------|---------|
| `models.py` | `SystemMetric` (cpu, memory, disk, timestamp) |
| `services.py` | `MonitoringService` — reads `/proc`, `psutil`, checks HTTP endpoints |
| `tasks.py` | Celery beat task (every 60s) |
| `views.py` | Dashboard charts (Chart.js via HTMX polling) |
| `api/` | Time-series REST API |

#### [NEW] `apps/users/`
| File | Purpose |
|------|---------|
| `models.py` | `EkafyUser` (extends AbstractUser, role=admin/operator/viewer, 2FA) |
| `services.py` | `UserService` — invite, role change, 2FA setup |
| `views.py` | Login, logout, profile, user management |
| `forms.py` | Login, invite, role forms |

#### [NEW] `apps/audit/`
| File | Purpose |
|------|---------|
| `models.py` | `AuditLog` (user, action, resource_type, resource_id, ip, timestamp, meta JSON) |
| `middleware.py` | Auto-capture request user + IP |
| `services.py` | `AuditService.log()` — called from service layer |
| `views.py` | Audit log list with filters |

---

### API Layer

#### [NEW] `api/`
- `router.py` — DRF DefaultRouter registrations
- `viewsets/` — Per-app ViewSets
- `serializers/` — Per-app serializers
- `authentication.py` — Token + Session auth
- `throttling.py` — Per-user rate limits

---

### Templates

#### [NEW] `templates/`
```
templates/
├── base.html               ← TailwindCSS layout, nav, sidebar
├── components/
│   ├── sidebar.html
│   ├── topbar.html
│   ├── card.html
│   ├── badge.html
│   ├── modal.html
│   └── toast.html
├── dashboard/
│   └── index.html          ← Overview: projects, metrics, recent deployments
├── projects/
│   ├── list.html
│   ├── detail.html
│   └── create.html
├── deployments/
│   ├── list.html
│   └── detail.html         ← Live log stream
├── logs/
│   └── viewer.html
├── backups/
│   └── list.html
├── monitoring/
│   └── dashboard.html
├── users/
│   ├── login.html
│   └── list.html
└── audit/
    └── list.html
```

---

### Scripts

#### [NEW] `scripts/`
| Script | Purpose |
|--------|---------|
| `deploy_project.sh` | Full deployment lifecycle: git pull, pip install, migrate, collectstatic, reload gunicorn |
| `create_project.sh` | Scaffold new managed project: mkdir, venv, createdb, nginx conf, systemd unit |
| `backup_db.sh` | pg_dump with timestamped filename |
| `backup_media.sh` | tar.gz media directory |
| `restore_db.sh` | Drop + restore from dump |
| `tail_logs.sh` | Wrapper around journalctl for a given service |
| `check_health.sh` | HTTP health check returning JSON |
| `create_systemd_service.sh` | Write & enable systemd unit file |
| `create_nginx_conf.sh` | Write nginx server block & reload |

---

### Infrastructure Config Templates

#### [NEW] `config_templates/`
| File | Purpose |
|------|---------|
| `nginx_project.conf.j2` | Nginx server block template |
| `gunicorn.service.j2` | Systemd service unit template |
| `gunicorn.socket.j2` | Systemd socket unit template |
| `env.j2` | `.env` template for managed projects |

---

### Celery & Background Jobs

- **Broker**: Redis
- **Beat scheduler**: `django-celery-beat` (schedules stored in DB, manageable from dashboard)
- **Workers**: One dedicated Celery worker systemd service

| Task | Schedule |
|------|---------|
| `monitoring.tasks.collect_metrics` | Every 60s |
| `backups.tasks.run_scheduled_backups` | Per-project cron from DB |
| `deployments.tasks.check_pending_deploys` | Every 30s |

---

### DevOps Files

#### [NEW] Root of `/srv/ekafy/`
| File | Purpose |
|------|---------|
| `requirements/base.txt` | Core Python dependencies |
| `requirements/production.txt` | Prod extras (gunicorn, psycopg2-binary, redis, boto3) |
| `requirements/development.txt` | Dev extras (django-debug-toolbar, factory-boy, pytest-django) |
| `Makefile` | `make setup`, `make migrate`, `make deploy`, `make test` |
| `README.md` | Setup & operations guide |
| `.env.example` | Environment variable template |

---

## Key Design Decisions

> [!IMPORTANT]
> **Service Layer Pattern**: All business logic lives in `services.py` per app. Views and API are thin — they call service methods only. No raw DB queries in views.

> [!IMPORTANT]
> **Repository Pattern**: Each app has a `repositories.py` wrapping ORM queries. Service layer only calls repository methods. This makes unit testing trivial (mock the repo).

> [!NOTE]
> **Async Deployments**: All deployments run as Celery tasks. The view triggers the task and redirects to a live-polling log page (HTMX + SSE). No blocking HTTP responses.

> [!NOTE]
> **Shell Script Safety**: All bash scripts validate inputs, use `set -euo pipefail`, and log to a timestamped file under `/srv/ekafy/logs/`.

> [!NOTE]
> **HTMX + AlpineJS**: Used for in-page updates (log tailing, status badges, modal confirmations) without a full SPA framework.

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Deployment scope**: Should I generate the complete Python/Django source code for all apps, or just the folder structure + key files (models, services, views, urls)?

> [!IMPORTANT]
> **Q2 — Multi-tenancy**: Is EKAFY single-tenant (one admin manages one VPS) or multi-tenant (multiple organizations, each with their own project pool)?

> [!IMPORTANT]
> **Q3 — Notification channels**: Should failed deployments/backups send alerts via email only, or also Slack/Telegram webhooks?

> [!IMPORTANT]
> **Q4 — S3 / remote backup**: Should backup uploads to S3/Backblaze B2 be implemented, or local disk only for now?

> [!IMPORTANT]
> **Q5 — HTTPS / TLS**: Should the platform generate Let's Encrypt TLS certificates automatically (via certbot) for managed projects, or is TLS out of scope?

---

## Verification Plan

### Automated Tests
```bash
# Unit tests
pytest --tb=short -q

# Coverage
pytest --cov=apps --cov-report=term-missing

# Linting
ruff check .
mypy apps/
```

### Manual Verification
1. Dashboard loads at `http://localhost:8000/` with correct sidebar, topbar
2. Create a new project → triggers `create_project.sh` → project directory appears
3. Trigger deployment → Celery task runs → live log updates via HTMX
4. Start/Stop systemd service → badge updates in real-time
5. Backup created → downloadable from the backup list
6. Audit log records every action with user + IP
