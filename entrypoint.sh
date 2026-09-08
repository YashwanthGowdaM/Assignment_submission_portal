#!/bin/sh
set -e

echo "========================================="
echo "Running database migrations..."
echo "========================================="
flask db upgrade

echo "========================================="
echo "Seeding database..."
echo "========================================="
python /app/seed.py

echo "========================================="
echo "Starting Gunicorn..."
echo "========================================="

exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --timeout 120 \
  run:app
