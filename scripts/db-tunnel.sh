#!/usr/bin/env bash
# Tunel SSH local -> RDS Postgres via EC2 bastion.
# Uso: ./scripts/db-tunnel.sh [puerto_local]   (default 5433)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

LOCAL_PORT="${1:-5433}"

require_tool ssh
require_tool aws
require_tool terraform
require_stack_up

RDS_HOST="$(tf_output rds_endpoint)"
RDS_PORT="$(tf_output rds_port)"
EC2_IP="$(ec2_ip)"
DB_NAME="apuestas_deportivas"
DB_USER="apuestas_admin"

log "Leyendo credenciales desde SSM..."
URI="$(aws ssm get-parameter \
  --name "$(ssm_param_name)" \
  --with-decryption \
  --region "$REGION" \
  --query Parameter.Value --output text)"

DB_PASS="$(echo "$URI" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')"

cat <<INFO

$(c_green "=== Conexion DB ===")
  Host:     localhost
  Port:     $LOCAL_PORT
  Database: $DB_NAME
  User:     $DB_USER
  Password: $DB_PASS
  SSL:      require

$(c_blue "Tunel:") $EC2_IP -> $RDS_HOST:$RDS_PORT
$(c_blue "Ctrl+C para cerrar")

INFO

exec ssh -i "$SSH_KEY" \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=60 \
  -N \
  -L "${LOCAL_PORT}:${RDS_HOST}:${RDS_PORT}" \
  ec2-user@"$EC2_IP"
