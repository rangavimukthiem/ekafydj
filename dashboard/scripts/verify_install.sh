#!/usr/bin/env bash
set -u

APP_NAME="${APP_NAME:-ekafydj}"
APP_USER="${APP_USER:-ekafy}"
APP_DIR="${APP_DIR:-/srv/${APP_NAME}}"
DASHBOARD_DIR="${APP_DIR}/dashboard"
VENV_DIR="${APP_DIR}/.venv"
ENV_FILE="${DASHBOARD_DIR}/.env"
VERIFY_SINCE="$(date '+%Y-%m-%d %H:%M:%S')"
FIX_MODE=0
FAILURES=0

if [ "${1:-}" = "--fix" ]; then
    FIX_MODE=1
fi

section() {
    printf "\n==> %s\n" "$1"
}

ok() {
    printf "OK: %s\n" "$1"
}

warn() {
    printf "WARN: %s\n" "$1"
}

fail() {
    printf "FAIL: %s\n" "$1"
    FAILURES=$((FAILURES + 1))
}

run_check() {
    local description="$1"
    shift
    if "$@" >/tmp/ekafydj-verify.out 2>/tmp/ekafydj-verify.err; then
        ok "$description"
        return 0
    fi

    fail "$description"
    sed 's/^/  /' /tmp/ekafydj-verify.err
    return 1
}

env_value() {
    local key="$1"
    sudo awk -F= -v key="$key" '$1 == key { gsub(/\r/, "", $2); print $2; exit }' "$ENV_FILE"
}

section "EKAFY post-install verification"
printf "App: %s\n" "$APP_DIR"
printf "Mode: %s\n" "$([ "$FIX_MODE" -eq 1 ] && printf fix || printf check)"

section "1. Required files"
run_check "dashboard directory exists" test -d "$DASHBOARD_DIR"
run_check "virtualenv python exists" test -x "${VENV_DIR}/bin/python"
run_check "env file exists" sudo test -f "$ENV_FILE"

if [ "$FAILURES" -gt 0 ]; then
    printf "\nCannot continue because required install files are missing.\n"
    exit 1
fi

section "2. Environment values"
DB_NAME="$(env_value DB_NAME)"
DB_USER="$(env_value DB_USER)"
DB_PASSWORD="$(env_value DB_PASSWORD)"
DB_HOST="$(env_value DB_HOST)"
DB_PORT="$(env_value DB_PORT)"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

[ -n "$DB_NAME" ] && ok "DB_NAME=$DB_NAME" || fail "DB_NAME is missing"
[ -n "$DB_USER" ] && ok "DB_USER=$DB_USER" || fail "DB_USER is missing"
[ -n "$DB_PASSWORD" ] && ok "DB_PASSWORD is present" || fail "DB_PASSWORD is missing"
[ -n "$DB_HOST" ] && ok "DB_HOST=$DB_HOST" || fail "DB_HOST is missing"
[ -n "$DB_PORT" ] && ok "DB_PORT=$DB_PORT" || fail "DB_PORT is missing"
run_check "env file has no CRLF endings" bash -c "! sudo grep -q \$'\\r' '$ENV_FILE'"

section "3. Platform folders"
for path in logs projects backups deployments; do
    run_check "${APP_DIR}/${path} exists" sudo test -d "${APP_DIR}/${path}"
    run_check "${APP_USER} can write ${path}" sudo -u "$APP_USER" test -w "${APP_DIR}/${path}"
done

section "4. PostgreSQL"
run_check "postgresql service is active" systemctl is-active --quiet postgresql

if [ "$FIX_MODE" -eq 1 ]; then
    run_check "database role password matches .env" \
        sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
fi

run_check "psql login works for ${DB_USER}" \
    sudo env PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "select current_user;"

section "5. Django"
cd "$DASHBOARD_DIR" || exit 1

run_check "Django database connection works" \
    sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings.production DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" \
    "${VENV_DIR}/bin/python" manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('django db ok')"

run_check "Django system check passes" \
    sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings.production DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" \
    "${VENV_DIR}/bin/python" manage.py check

run_check "Django migrations are applied" \
    sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings.production DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" \
    "${VENV_DIR}/bin/python" manage.py migrate --check

run_check "staticfiles directory exists" test -d "${DASHBOARD_DIR}/staticfiles"
run_check "staticfiles directory is not empty" bash -c "find '${DASHBOARD_DIR}/staticfiles' -type f | head -n 1 | grep -q ."

section "6. Celery Beat task names"
run_check "Celery Beat task names are registered names" \
    sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings.production DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" \
    "${VENV_DIR}/bin/python" manage.py shell -c "from django_celery_beat.models import PeriodicTask; bad=PeriodicTask.objects.filter(task__startswith='apps.').values_list('name','task'); bad=list(bad); print(bad); raise SystemExit(1 if bad else 0)"

section "7. Services"
for service in "${APP_NAME}-dashboard" "${APP_NAME}-celery" "${APP_NAME}-celery-beat"; do
    if [ "$FIX_MODE" -eq 1 ]; then
        run_check "restart ${service}" sudo systemctl restart "$service"
    fi
    run_check "${service} is active" systemctl is-active --quiet "$service"
    run_check "${service} is enabled" systemctl is-enabled --quiet "$service"
done

section "8. Nginx"
run_check "nginx config test passes" sudo nginx -t
run_check "nginx service is active" systemctl is-active --quiet nginx
run_check "ekafydj nginx site is enabled" test -L "/etc/nginx/sites-enabled/${APP_NAME}"

section "9. HTTP checks"
run_check "Gunicorn login page renders with GET" \
    curl -fsS -o /tmp/ekafydj-login-gunicorn.html "http://127.0.0.1:8000/account/login/?next=/"
run_check "Nginx login page renders with GET" \
    curl -fsS -o /tmp/ekafydj-login-nginx.html "http://127.0.0.1/account/login/?next=/"

if [ -n "${APP_PUBLIC_HOST:-}" ]; then
    run_check "Nginx login page renders with Host ${APP_PUBLIC_HOST}" \
        curl -fsS -H "Host: ${APP_PUBLIC_HOST}" -o /tmp/ekafydj-login-public-host.html "http://127.0.0.1/account/login/?next=/"
fi

section "10. Fresh service errors"
if sudo journalctl -u "${APP_NAME}-dashboard" --since "$VERIFY_SINCE" --no-pager -p err | grep -q .; then
    fail "fresh dashboard errors exist; inspect with: sudo journalctl -u ${APP_NAME}-dashboard --since '${VERIFY_SINCE}' --no-pager -l"
else
    ok "no fresh dashboard errors at journal priority err"
fi

if sudo journalctl -u "${APP_NAME}-celery" --since "$VERIFY_SINCE" --no-pager -p err | grep -q .; then
    fail "fresh celery errors exist; inspect with: sudo journalctl -u ${APP_NAME}-celery --since '${VERIFY_SINCE}' --no-pager -l"
else
    ok "no fresh celery errors at journal priority err"
fi

section "Result"
if [ "$FAILURES" -eq 0 ]; then
    printf "EKAFY setup verification finished successfully.\n"
    printf "Open: http://SERVER_IP/account/login/\n"
    exit 0
fi

printf "EKAFY setup verification found %s failed check(s).\n" "$FAILURES"
printf "Run with --fix for safe automatic repairs: sudo bash %s/dashboard/scripts/verify_install.sh --fix\n" "$APP_DIR"
exit 1
