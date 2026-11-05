#!/bin/sh
set -eu

python - <<'PY'
import os
import subprocess
import psycopg

connection = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=30)
try:
    connection.execute('SELECT pg_advisory_lock(748391205)')
    subprocess.run(['python', 'manage.py', 'migrate', '--noinput'], check=True)
finally:
    try:
        connection.execute('SELECT pg_advisory_unlock(748391205)')
    finally:
        connection.close()
PY
python manage.py collectstatic --noinput
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}" --timeout 90 --access-logfile - --error-logfile -
