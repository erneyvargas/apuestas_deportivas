#!/bin/bash

# Configuración
DB_NAME="geolocalizacion_db"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="$(dirname "$0")"
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}.dump"

export PGPASSWORD="$DB_PASSWORD"

pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  --exclude-table=eventData \
  --format=custom \
  --file="$BACKUP_FILE" \
  "$DB_NAME"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completado: $BACKUP_FILE"
