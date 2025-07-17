#!/bin/bash
# start.sh
set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENVIRONMENT=production

echo "Initializing MySQL database..."
python -m app.db.init_db

echo "Starting production server..."
exec gunicorn app.main:app \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload \
    --access-logfile - \
    --error-logfile -