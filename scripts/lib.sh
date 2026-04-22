#!/usr/bin/env bash
# Utilidades compartidas por scripts de lifecycle AWS

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$PROJECT_ROOT/terraform"
SSH_KEY="$HOME/.ssh/apuestas-key.pem"
REGION="us-east-1"

# Colores log
c_blue()  { printf "\033[34m%s\033[0m\n" "$*"; }
c_green() { printf "\033[32m%s\033[0m\n" "$*"; }
c_red()   { printf "\033[31m%s\033[0m\n" "$*" >&2; }

log()  { c_blue  "==> $*"; }
ok()   { c_green "✓ $*"; }
die()  { c_red   "✗ $*"; exit 1; }

require_tool() {
  command -v "$1" >/dev/null 2>&1 || die "Falta herramienta: $1"
}

tf() {
  ( cd "$TF_DIR" && terraform "$@" )
}

tf_output() {
  tf output -raw "$1" 2>/dev/null
}

ec2_ip()         { tf_output ec2_public_ip; }
ec2_id()         { tf_output ec2_instance_id; }
rds_id()         { echo "apuestas-dev-postgres"; }
ecr_repo()       { tf_output ecr_repository_url; }
ssm_param_name() { tf_output postgres_uri_parameter; }

ssh_ec2() {
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      ec2-user@"$(ec2_ip)" "$@"
}

scp_ec2() {
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      "$@"
}

require_stack_up() {
  if [ -z "$(ec2_id 2>/dev/null)" ]; then
    die "Stack no existe — corre ./scripts/deploy.sh primero"
  fi
}

wait_for_ssh() {
  log "Esperando SSH en $(ec2_ip)..."
  for i in $(seq 1 60); do
    if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
        -o UserKnownHostsFile=/dev/null ec2-user@"$(ec2_ip)" true 2>/dev/null; then
      ok "SSH listo"
      return 0
    fi
    sleep 5
  done
  die "Timeout esperando SSH"
}

wait_for_rds() {
  log "Esperando RDS disponible..."
  aws rds wait db-instance-available \
    --db-instance-identifier "$(rds_id)" --region "$REGION"
  ok "RDS disponible"
}

# Detecta IP publica actual, compara con tfvars, actualiza SGs si cambio
fix_my_ip() {
  local tfvars="$TF_DIR/terraform.tfvars"
  local current
  current="$(curl -s --max-time 5 ifconfig.me)" || die "No pude obtener IP publica"
  local current_cidr="${current}/32"
  local tfvars_cidr
  tfvars_cidr="$(grep -E '^allowed_ssh_cidr' "$tfvars" | sed -E 's/.*"([^"]+)".*/\1/')"

  if [ "$current_cidr" = "$tfvars_cidr" ]; then
    ok "IP sin cambios ($current)"
    return 0
  fi

  log "IP cambio: $tfvars_cidr -> $current_cidr, actualizando SG..."
  sed -i "s|allowed_ssh_cidr  = \".*\"|allowed_ssh_cidr  = \"$current_cidr\"|" "$tfvars"
  tf apply -auto-approve \
    -target=aws_security_group.app \
    -target=aws_security_group_rule.db_ingress_from_me >/dev/null
  ok "SG actualizado a $current"
}
