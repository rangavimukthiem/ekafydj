#!/usr/bin/env bash
# =============================================================================
# EKAFY — create_nginx_conf.sh
# Generates and enables an nginx server block for a managed project.
#
# Usage:
#   create_nginx_conf.sh <slug> <domain> <conf_path> <gunicorn_bind>
# =============================================================================
set -euo pipefail

SLUG="${1:?SLUG required}"
DOMAIN="${2:?DOMAIN required}"
CONF_PATH="${3:-/etc/nginx/sites-available/ekafy-$SLUG}"
BIND="${4:-unix:/run/gunicorn/$SLUG.sock}"
STATIC_ROOT="/srv/ekafy/projects/$SLUG/repo/staticfiles"
MEDIA_ROOT="/srv/ekafy/projects/$SLUG/media"
ENABLED_PATH="/etc/nginx/sites-enabled/ekafy-$SLUG"

echo "=== [EKAFY] Creating nginx config for: $DOMAIN ($SLUG) ==="

cat > "$CONF_PATH" <<EOF
# EKAFY — nginx config for $SLUG
# Generated: $(date)

upstream ekafy_${SLUG}_upstream {
    server $BIND fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 100M;
    keepalive_timeout 70;

    access_log /var/log/nginx/ekafy-${SLUG}-access.log;
    error_log  /var/log/nginx/ekafy-${SLUG}-error.log warn;

    location /static/ {
        alias $STATIC_ROOT/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $MEDIA_ROOT/;
        expires 7d;
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_buffering on;
        proxy_pass http://ekafy_${SLUG}_upstream;
    }
}
EOF

echo "✓ Config written: $CONF_PATH"

# Enable (symlink into sites-enabled)
if [ ! -L "$ENABLED_PATH" ]; then
  ln -s "$CONF_PATH" "$ENABLED_PATH"
  echo "✓ Enabled: $ENABLED_PATH"
fi

# Test and reload nginx
nginx -t && systemctl reload nginx
echo "✓ Nginx reloaded"
echo ""
echo "=== [EKAFY] Nginx config for '$DOMAIN' installed ==="
echo "    Run certbot to enable HTTPS:"
echo "    certbot --nginx -d $DOMAIN -d www.$DOMAIN"
