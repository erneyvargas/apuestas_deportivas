#!/usr/bin/env bash
# Tail logs de la app en EC2.

source "$(dirname "$0")/lib.sh"

require_stack_up
ssh_ec2 'sudo journalctl -u apuestas-app -f --no-pager'
