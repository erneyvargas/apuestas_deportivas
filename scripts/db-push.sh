#!/usr/bin/env bash
# Dump Postgres local -> restore en RDS (endpoint publico, SG restringido a tu IP).
# Usa docker run postgres:18 para no requerir cliente postgres en el host.
#
# Uso:
#   ./scripts/db-push.sh                       # schema + data, con --clean
#   ./scripts/db-push.sh --data-only           # solo datos (schema ya existe)
#   ./scripts/db-push.sh --schema-only         # solo schema
#   ./scripts/db-push.sh --table leagues       # solo una tabla
#   ./scripts/db-push.sh --fix-ip              # auto-actualiza SG con tu IP actual antes del push
#
# Env override:
#   LOCAL_HOST   (default localhost)
#   LOCAL_PORT   (default 5432)
#   LOCAL_USER   (default postgres)
#   LOCAL_PASS   (default postgres)
#   LOCAL_DB     (default apuestas_deportivas)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

LOCAL_HOST="${LOCAL_HOST:-localhost}"
LOCAL_PORT="${LOCAL_PORT:-5432}"
LOCAL_USER="${LOCAL_USER:-postgres}"
LOCAL_PASS="${LOCAL_PASS:-postgres}"
LOCAL_DB="${LOCAL_DB:-apuestas_deportivas}"

PG_IMAGE="postgres:18"
DUMP_DIR="$(mktemp -d -t apuestas_dump_XXXXXX)"
DUMP_FILE="$DUMP_DIR/db.dump"

cleanup() {
  [ -d "$DUMP_DIR" ] && rm -rf "$DUMP_DIR"
}
trap cleanup EXIT

require_tool docker
require_tool aws
require_tool terraform
require_stack_up

MODE="full"
TABLE=""
FIX_IP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --data-only)   MODE="data-only" ;;
    --schema-only) MODE="schema-only" ;;
    --table)       TABLE="$2"; shift ;;
    --fix-ip)      FIX_IP=1 ;;
    -h|--help)     grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)             die "Arg desconocido: $1" ;;
  esac
  shift
done

[ "$FIX_IP" = "1" ] && fix_my_ip

pg_run_env() {
  local pass="$1"; shift
  docker run --rm --network host \
    -e PGPASSWORD="$pass" \
    -e PGSSLMODE="${PGSSLMODE:-prefer}" \
    -e PGCONNECT_TIMEOUT=10 \
    -v "$DUMP_DIR":/dump "$PG_IMAGE" "$@"
}

log "Descargando imagen $PG_IMAGE si falta..."
docker image inspect "$PG_IMAGE" >/dev/null 2>&1 || docker pull "$PG_IMAGE" >/dev/null
ok "Imagen lista"

log "Verificando Postgres local..."
pg_run_env "$LOCAL_PASS" psql -h "$LOCAL_HOST" -p "$LOCAL_PORT" -U "$LOCAL_USER" \
  -d "$LOCAL_DB" -c "select 1" >/dev/null || die "No puedo conectar a Postgres local"
ok "Local OK"

RDS_HOST="$(tf_output rds_endpoint)"
RDS_PORT="$(tf_output rds_port)"

log "Leyendo credenciales RDS..."
RDS_URI="$(aws ssm get-parameter \
  --name "$(ssm_param_name)" \
  --with-decryption \
  --region "$REGION" \
  --query Parameter.Value --output text)"

RDS_USER="$(echo "$RDS_URI" | sed -E 's|.*://([^:]+):.*|\1|')"
RDS_PASS="$(echo "$RDS_URI" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')"
RDS_DB="$(echo "$RDS_URI" | sed -E 's|.*/([^?]+)(\?.*)?$|\1|')"

log "Probando conexion directa a RDS $RDS_HOST:$RDS_PORT..."
PGSSLMODE=require pg_run_env "$RDS_PASS" psql \
  -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" -d "$RDS_DB" \
  -c "select 1" >/dev/null || die "No puedo conectar a RDS (verifica IP en SG y que RDS sea public)"
ok "RDS accesible"

log "Dump local ($LOCAL_DB) -> $DUMP_FILE"
DUMP_ARGS=(-h "$LOCAL_HOST" -p "$LOCAL_PORT" -U "$LOCAL_USER" -d "$LOCAL_DB"
           --format=custom --no-owner --no-privileges --verbose -f /dump/db.dump)
[ "$MODE" = "data-only" ]   && DUMP_ARGS+=(--data-only)
[ "$MODE" = "schema-only" ] && DUMP_ARGS+=(--schema-only)
[ -n "$TABLE" ]             && DUMP_ARGS+=(--table="$TABLE")

pg_run_env "$LOCAL_PASS" pg_dump "${DUMP_ARGS[@]}" 2> >(grep -E "^(pg_dump:|ERROR)" >&2 || true)
DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
ok "Dump $DUMP_SIZE"

RESTORE_ARGS=(-h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" -d "$RDS_DB"
              --no-owner --no-privileges --verbose /dump/db.dump)
[ "$MODE" = "full" ] && RESTORE_ARGS=(--clean --if-exists "${RESTORE_ARGS[@]}")

log "Restore en RDS ($RDS_DB)..."
PGSSLMODE=require pg_run_env "$RDS_PASS" pg_restore "${RESTORE_ARGS[@]}" 2> >(grep -E "^(pg_restore:|ERROR)" >&2 || true) || {
  c_red "pg_restore termino con warnings (revisa arriba)"
}

log "Verificando tablas en RDS..."
PGSSLMODE=require pg_run_env "$RDS_PASS" psql \
  -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" -d "$RDS_DB" -c "\dt"

ok "Push completado"
