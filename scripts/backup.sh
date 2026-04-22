#!/usr/bin/env bash
# Backup RDS Postgres -> archivo local con timestamp.
# Uso: ./backup.sh [ruta_destino]

source "$(dirname "$0")/lib.sh"

require_stack_up

DEST="${1:-/tmp/rds_backup_$(date +%Y%m%d_%H%M%S).sql}"

log "Dump RDS a EC2 (tmp remoto via docker postgres:18)"
ssh_ec2 bash -s <<'REMOTE'
set -e
URI=$(aws ssm get-parameter --name /apuestas-dev/postgres_uri --with-decryption \
      --region us-east-1 --query Parameter.Value --output text)
sudo docker run --rm -e PGURI="$URI" postgres:18 \
  sh -c 'pg_dump "$PGURI" --no-owner --no-acl' > /tmp/rds_backup.sql
ls -lh /tmp/rds_backup.sql
REMOTE

log "Descargando a $DEST"
scp_ec2 ec2-user@"$(ec2_ip)":/tmp/rds_backup.sql "$DEST"
ssh_ec2 "rm /tmp/rds_backup.sql"

ok "Backup guardado en $DEST ($(du -h "$DEST" | cut -f1))"
