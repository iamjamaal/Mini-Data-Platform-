#!/bin/bash
set -e

echo ">>> Waiting for PostgreSQL to be ready..."
until airflow db check; do
  echo "    PostgreSQL not ready yet — retrying in 5s..."
  sleep 5
done

echo ">>> Running database migrations..."
airflow db upgrade

echo ">>> Creating admin user (if not exists)..."
airflow users create \
  --username "${AIRFLOW_ADMIN_USER:-admin}" \
  --password "${AIRFLOW_ADMIN_PASSWORD:-admin}" \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com 2>/dev/null || echo "    Admin user already exists, skipping."


echo ">>> Starting Airflow scheduler in background..."
airflow scheduler &

echo ">>> Starting Airflow webserver on port 8080..."
exec airflow webserver --port 8080
