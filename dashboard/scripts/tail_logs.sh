#!/usr/bin/env bash
# =============================================================================
# EKAFY — tail_logs.sh
# Tail journalctl for a managed project service.
#
# Usage:
#   tail_logs.sh <service_name> [<lines>]
# =============================================================================
set -euo pipefail

SERVICE_NAME="${1:?SERVICE_NAME required}"
LINES="${2:-100}"

exec sudo journalctl -u "$SERVICE_NAME" -n "$LINES" --no-pager --output=short-iso
