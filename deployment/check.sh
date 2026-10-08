#!/usr/bin/env bash
set -euo pipefail
TASK_DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$TASK_DEPLOY_DIR/../.venv/bin/python" "$TASK_DEPLOY_DIR/control.py" check "$@"
