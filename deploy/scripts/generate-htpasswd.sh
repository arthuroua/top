#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.production"
OUTPUT_FILE="${ROOT_DIR}/deploy/nginx/.htpasswd"

if [ ! -f "${ENV_FILE}" ]; then
  echo ".env.production not found. Copy .env.production.example first."
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a

if [ -z "${BASIC_AUTH_USER:-}" ] || [ -z "${BASIC_AUTH_PASSWORD:-}" ]; then
  echo "BASIC_AUTH_USER or BASIC_AUTH_PASSWORD is empty."
  exit 1
fi

HASH="$(openssl passwd -apr1 "${BASIC_AUTH_PASSWORD}")"
printf "%s:%s\n" "${BASIC_AUTH_USER}" "${HASH}" > "${OUTPUT_FILE}"
echo "Generated ${OUTPUT_FILE}"
