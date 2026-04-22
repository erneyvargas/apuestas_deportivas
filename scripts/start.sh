#!/usr/bin/env bash
# Enciende EC2 + RDS tras stop.sh. Re-arranca app.

source "$(dirname "$0")/lib.sh"

require_stack_up

INSTANCE=$(ec2_id)
DB=$(rds_id)

log "Start RDS $DB"
STATUS=$(aws rds describe-db-instances --db-instance-identifier "$DB" \
  --region "$REGION" --query 'DBInstances[0].DBInstanceStatus' --output text)
if [ "$STATUS" = "stopped" ]; then
  aws rds start-db-instance --db-instance-identifier "$DB" --region "$REGION" >/dev/null
fi

log "Start EC2 $INSTANCE"
aws ec2 start-instances --instance-ids "$INSTANCE" --region "$REGION" >/dev/null
aws ec2 wait instance-running --instance-ids "$INSTANCE" --region "$REGION"

# IP puede cambiar tras start si no hay EIP
NEW_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE" --region "$REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
log "EC2 running en IP $NEW_IP"
log "Refrescando terraform state..."
tf apply -refresh-only -auto-approve >/dev/null

wait_for_rds
wait_for_ssh

log "Restart app"
ssh_ec2 'sudo systemctl restart apuestas-app && sleep 2 && sudo systemctl status apuestas-app --no-pager | head -10'

ok "Stack activo. IP: $(ec2_ip)"
