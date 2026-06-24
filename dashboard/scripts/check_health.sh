#!/usr/bin/env bash
# =============================================================================
# EKAFY — check_health.sh
# HTTP health check for a managed project. Returns JSON.
#
# Usage:
#   check_health.sh <url> [<timeout_seconds>]
# =============================================================================
set -euo pipefail

URL="${1:?URL required}"
TIMEOUT="${2:-10}"

HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" --max-time "$TIMEOUT" "$URL" || echo "000")
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" --max-time "$TIMEOUT" "$URL" 2>/dev/null || echo "0")

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
  STATUS="healthy"
else
  STATUS="unhealthy"
fi

echo "{\"status\":\"$STATUS\",\"http_code\":$HTTP_CODE,\"response_time_seconds\":$RESPONSE_TIME,\"url\":\"$URL\"}"
