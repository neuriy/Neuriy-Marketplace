#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
cd "${ROOT}/src/api"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
: "${TURSO_DATABASE_URL:=libsql://neuriymp-ericksonholding.aws-eu-west-1.turso.io}"
export TURSO_DATABASE_URL
exec python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
