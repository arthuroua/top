#!/bin/sh
set -e

MESSAGE="$1"
if [ -z "$MESSAGE" ]; then
  echo "Usage: ./scripts/create-migration.sh \"migration message\""
  exit 1
fi

cd "$(dirname "$0")/.."
alembic revision --autogenerate -m "$MESSAGE"
