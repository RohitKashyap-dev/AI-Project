#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv311"
if [[ ! -d "${VENV_DIR}" ]]; then
  VENV_DIR="${ROOT_DIR}/.venv"
fi

if [[ ! -x "${VENV_DIR}/bin/celery" ]]; then
  echo "No compatible virtualenv found. Expected ${VENV_DIR}." >&2
  exit 1
fi

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  . "${ROOT_DIR}/.env"
  set +a
fi

exec "${VENV_DIR}/bin/celery" -A backend.core.celery_app worker --loglevel=info
