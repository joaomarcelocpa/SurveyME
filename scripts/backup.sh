#!/usr/bin/env bash
# Backup agendado. Le as variaveis de ~/.survey-backup.env (permissao 600):
#   DATABASE_URL_RO=...   SURVEY_BACKUP_DIR=...   SURVEY_BACKUP_MIRROR=...
set -euo pipefail
ENV_FILE="${SURVEY_BACKUP_ENV:-$HOME/.survey-backup.env}"
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
AQUI="$(cd "$(dirname "$0")" && pwd)"
PY="$AQUI/../dashboard/.venv/bin/python"
[ -x "$PY" ] || PY=python3
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
"$PY" "$AQUI/backup.py"
