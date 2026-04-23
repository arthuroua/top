#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.production"
BACKUP_DIR="${ROOT_DIR}/deploy/backups/postgres"

if [ ! -f "${ENV_FILE}" ]; then
  echo ".env.production not found. Copy .env.production.example first."
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a

mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%Y%m%d-%H%M%S)"
FILE_NAME="${POSTGRES_DB}-${STAMP}.sql.gz"
TARGET_FILE="${BACKUP_DIR}/${FILE_NAME}"

docker compose -f "${ROOT_DIR}/docker-compose.prod.yml" --env-file "${ENV_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-privileges \
  | gzip -9 > "${TARGET_FILE}"

find "${BACKUP_DIR}" -type f -name '*.sql.gz' -mtime +14 -delete

echo "Backup created: ${TARGET_FILE}"
