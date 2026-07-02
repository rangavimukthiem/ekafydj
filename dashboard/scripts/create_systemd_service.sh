#!/usr/bin/env bash
# =============================================================================
# EKAFY — create_systemd_service.sh
# Generates and installs a gunicorn systemd socket + service unit.
#
# Usage:
#   create_systemd_service.sh <slug> <service_name> <venv_path> <repo_path> \
#                             <wsgi_module> <settings_module> <workers> <bind>
# =============================================================================
set -euo pipefail

SLUG="${1:?SLUG required}"
SERVICE_NAME="${2:-ekafy-$SLUG.service}"
VENV_PATH="${3:?VENV_PATH required}"
REPO_PATH="${4:?REPO_PATH required}"
WSGI_MODULE="${5:-config.wsgi:application}"
SETTINGS_MODULE="${6:-config.settings.production}"
WORKERS="${7:-3}"
BIND="${8:-unix:/run/gunicorn/$SLUG.sock}"

SOCKET_NAME="ekafy-$SLUG.socket"
GUNICORN="$VENV_PATH/bin/gunicorn"
EKAFY_BASE_DIR="${EKAFY_BASE_DIR:-/srv/ekafydj}"
EKAFY_LOGS_DIR="${EKAFY_LOGS_DIR:-$EKAFY_BASE_DIR/logs}"
mkdir -p "$EKAFY_LOGS_DIR"

echo "=== [EKAFY] Creating systemd units for: $SLUG ==="

# ── Socket unit ───────────────────────────────────────────────────────────────
cat > "/etc/systemd/system/$SOCKET_NAME" <<EOF
[Unit]
Description=EKAFY Gunicorn Socket — $SLUG

[Socket]
ListenStream=$BIND

[Install]
WantedBy=sockets.target
EOF
echo "✓ Socket unit written: /etc/systemd/system/$SOCKET_NAME"

# ── Service unit ──────────────────────────────────────────────────────────────
cat > "/etc/systemd/system/$SERVICE_NAME" <<EOF
[Unit]
Description=EKAFY Gunicorn Service — $SLUG
Requires=$SOCKET_NAME
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$REPO_PATH
ExecStart=$GUNICORN \\
    --workers $WORKERS \\
    --worker-class sync \\
    --timeout 120 \\
    --bind $BIND \\
    --log-level info \\
    --access-logfile $EKAFY_LOGS_DIR/${SLUG}_access.log \\
    --error-logfile $EKAFY_LOGS_DIR/${SLUG}_error.log \\
    $WSGI_MODULE
Environment=DJANGO_SETTINGS_MODULE=$SETTINGS_MODULE
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
echo "✓ Service unit written: /etc/systemd/system/$SERVICE_NAME"

# ── Enable and start ──────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable "$SOCKET_NAME"
systemctl enable "$SERVICE_NAME"
systemctl start "$SOCKET_NAME"

echo "✓ Systemd units enabled"
echo "=== Done. Start with: systemctl start $SERVICE_NAME ==="
