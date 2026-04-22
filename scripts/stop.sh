#!/usr/bin/env bash
# Para EC2 + RDS (preserva data, corta casi todo el costo).
# RDS stopped auto-enciende en 7 días (limite AWS).

source "$(dirname "$0")/lib.sh"

require_stack_up

INSTANCE=$(ec2_id)
DB=$(rds_id)

log "Stop EC2 $INSTANCE"
aws ec2 stop-instances --instance-ids "$INSTANCE" --region "$REGION" >/dev/null
ok "EC2 parando"

log "Stop RDS $DB"
if aws rds describe-db-instances --db-instance-identifier "$DB" \
   --region "$REGION" --query 'DBInstances[0].DBInstanceStatus' --output text \
   | grep -q available; then
  aws rds stop-db-instance --db-instance-identifier "$DB" --region "$REGION" >/dev/null
  ok "RDS parando"
else
  log "RDS ya parada o en transición — skip"
fi

ok "Stack pausado. Data preservada. RDS se auto-enciende en 7 días."
