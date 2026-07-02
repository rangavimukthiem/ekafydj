# EKAFY — Makefile
# Usage: make <target>

.PHONY: help setup install dev test lint migrate createsuperuser collectstatic worker beat shell

PYTHON  := python3.12
VENV    := .venv
PIP     := $(VENV)/bin/pip
MANAGE  := $(VENV)/bin/python dashboard/manage.py
CELERY  := $(VENV)/bin/celery
SETTINGS := config.settings.development

help:
	@echo ""
	@echo "  EKAFY — Development Commands"
	@echo "  ──────────────────────────────"
	@echo "  make setup          — Full first-time setup"
	@echo "  make install        — Install Python dependencies"
	@echo "  make dev            — Run development server"
	@echo "  make test           — Run pytest"
	@echo "  make lint           — Run ruff + mypy"
	@echo "  make migrate        — Apply database migrations"
	@echo "  make makemigrations — Create new migrations"
	@echo "  make createsuperuser — Create admin user"
	@echo "  make collectstatic  — Collect static files"
	@echo "  make worker         — Start Celery worker"
	@echo "  make beat           — Start Celery beat scheduler"
	@echo "  make shell          — Django shell"
	@echo ""

setup: install migrate createsuperuser
	@echo "✓ EKAFY setup complete. Run 'make dev' to start."

install:
	@echo "Creating virtualenv..."
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip wheel setuptools
	$(PIP) install -r requirements/development.txt
	@echo "✓ Dependencies installed"

dev:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(VENV)/bin/python manage.py runserver 0.0.0.0:8000

migrate:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(VENV)/bin/python manage.py migrate

makemigrations:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(VENV)/bin/python manage.py makemigrations

createsuperuser:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(VENV)/bin/python manage.py createsuperuser

collectstatic:
	cd dashboard && DJANGO_SETTINGS_MODULE=config.settings.production ../$(VENV)/bin/python manage.py collectstatic --noinput

test:
	cd dashboard && DJANGO_SETTINGS_MODULE=config.settings.testing ../$(VENV)/bin/python -m pytest tests/ -v

test-fast:
	cd dashboard && DJANGO_SETTINGS_MODULE=config.settings.testing ../$(VENV)/bin/python -m pytest tests/ -q --no-cov

lint:
	$(VENV)/bin/ruff check dashboard/
	$(VENV)/bin/mypy dashboard/apps/

worker:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(CELERY) -A config.celery worker --loglevel=info --concurrency=4

beat:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(CELERY) -A config.celery beat --loglevel=info

shell:
	cd dashboard && DJANGO_SETTINGS_MODULE=$(SETTINGS) ../$(VENV)/bin/python manage.py shell_plus

logs:
	tail -f /srv/ekafydj/logs/ekafy_dashboard.log
