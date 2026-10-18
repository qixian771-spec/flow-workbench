#!/bin/bash
# Explicit local configuration; do not guess a Python environment or project.
set -euo pipefail
FLOWKIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$FLOWKIT_ROOT"
if [[ ! -f .env ]]; then
  echo 'Missing .env: copy .env.example and fill in FLOWKIT_PYTHON and FLOW_PROJECT_ID.' >&2
  exit 1
fi
set -a
source .env
set +a
: "${FLOWKIT_PYTHON:?Set FLOWKIT_PYTHON in .env}"
: "${FLOW_PROJECT_ID:?Set FLOW_PROJECT_ID in .env}"
if [[ ! -x "$FLOWKIT_PYTHON" ]]; then
  echo "FLOWKIT_PYTHON is not executable: $FLOWKIT_PYTHON" >&2
  exit 1
fi
"$FLOWKIT_PYTHON" -c 'import os, sys, uuid; value = os.environ["FLOW_PROJECT_ID"]; sys.exit(0 if str(uuid.UUID(value)) == value else "FLOW_PROJECT_ID must be a canonical UUID")'
export FLOW_AGENT_DIR="$FLOWKIT_ROOT"
export API_HOST=127.0.0.1 WS_HOST=127.0.0.1
export API_PORT=8100 WS_PORT=9222
export DEFAULT_PROVIDER=flow
export FLOW_ALLOW_DEGRADED=0 MUSE2API_ALLOW_DEGRADED=0
exec "$FLOWKIT_PYTHON" -m agent.main
