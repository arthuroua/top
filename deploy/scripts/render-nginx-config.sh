#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.production"
TEMPLATE_FILE="${ROOT_DIR}/deploy/nginx/conf.d/site.conf.template"
OUTPUT_FILE="${ROOT_DIR}/deploy/nginx/conf.d/site.conf"

if [ ! -f "${ENV_FILE}" ]; then
  echo ".env.production not found. Copy .env.production.example first."
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a

envsubst '${PUBLIC_WEB_DOMAIN} ${PUBLIC_API_DOMAIN}' < "${TEMPLATE_FILE}" > "${OUTPUT_FILE}"
echo "Rendered ${OUTPUT_FILE}"
