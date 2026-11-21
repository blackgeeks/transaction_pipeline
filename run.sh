#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg not found. Install it with: brew install ffmpeg"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate
[ -f .env ] && export $(grep -v '^#' .env | xargs)

uvicorn app.main:app --host 0.0.0.0 --port 8000
