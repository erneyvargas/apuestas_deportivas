#!/usr/bin/env bash
# Destruye TODO el stack AWS (VPC, RDS, EC2, ECR, etc.)
# Antes de destruir, saca backup RDS -> local.

source "$(dirname "$0")/lib.sh"

require_tool terraform
require_tool aws

if [ -z "$(ec2_id 2>/dev/null)" ]; then
  log "Stack no existe — nada que destruir"
  exit 0
fi

read -p "⚠ Destruirá VPC, RDS, EC2, ECR. ¿Hacer backup antes? [Y/n] " backup
if [[ "${backup,,}" != "n" ]]; then
  log "Backup RDS -> /tmp/rds_backup_$(date +%Y%m%d_%H%M%S).sql"
  "$(dirname "$0")/backup.sh"
fi

read -p "Confirma destroy escribiendo 'destroy': " confirm
[ "$confirm" = "destroy" ] || die "Cancelado"

log "terraform destroy"
tf destroy -auto-approve

ok "Stack destruido. Costo AWS = 0"
