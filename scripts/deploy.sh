#!/usr/bin/env bash
# Despliega stack completo: terraform apply + schema + data + imagen + start app.
# Idempotente: si stack existe, actualiza. Si no, crea.

source "$(dirname "$0")/lib.sh"

require_tool terraform
require_tool aws
require_tool docker

log "1/7 Terraform apply"
tf init -upgrade >/dev/null
tf apply -auto-approve

REPO=$(ecr_repo)
IP=$(ec2_ip)
PARAM=$(ssm_param_name)

log "2/7 Esperando RDS + SSH"
wait_for_rds
wait_for_ssh

log "3/7 Dump Postgres local"
if docker ps --format '{{.Names}}' | grep -q '^postgres18$'; then
  docker exec postgres18 pg_dump -U postgres -d apuestas_deportivas \
    --no-owner --no-acl > /tmp/apuestas_schema_data.sql
  ok "Dump generado ($(du -h /tmp/apuestas_schema_data.sql | cut -f1))"
else
  die "Container local 'postgres18' no corre. Levanta con: docker compose up -d postgres"
fi

log "4/7 Copiando schema + data a EC2"
scp_ec2 "$PROJECT_ROOT/infrastructure/persistence/schema.sql" \
        ec2-user@"$IP":/tmp/schema.sql
scp_ec2 /tmp/apuestas_schema_data.sql ec2-user@"$IP":/tmp/data.sql

log "5/7 Cargando schema + data en RDS"
ssh_ec2 bash -s <<'REMOTE'
set -e
sudo dnf install -y postgresql17 >/dev/null 2>&1
URI=$(aws ssm get-parameter --name /apuestas-dev/postgres_uri --with-decryption \
      --region us-east-1 --query Parameter.Value --output text)
psql "$URI" -f /tmp/schema.sql >/dev/null 2>&1 || true
psql "$URI" -f /tmp/data.sql   2>&1 | grep -E '(ERROR|COPY|setval)' | head -20 || true
REMOTE

log "6/7 Build + push imagen Docker"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${REPO%/*}" >/dev/null
docker build -t "$REPO:latest" "$PROJECT_ROOT" >/dev/null
docker push "$REPO:latest" | tail -3

log "7/7 Restart app en EC2"
ssh_ec2 bash -s <<REMOTE
set -e
aws ecr get-login-password --region $REGION \
  | sudo docker login --username AWS --password-stdin ${REPO%/*} >/dev/null
sudo docker pull $REPO:latest >/dev/null
sudo systemctl restart apuestas-app
sleep 3
sudo systemctl status apuestas-app --no-pager | head -15
REMOTE

ok "Deploy completo"
echo ""
echo "IP EC2: $IP"
echo "SSH:    ssh -i $SSH_KEY ec2-user@$IP"
echo "Logs:   ssh -i $SSH_KEY ec2-user@$IP 'sudo journalctl -u apuestas-app -f'"
