# scripts/ — Lifecycle AWS

Wrappers Bash sobre Terraform + AWS CLI + Docker para manejar el stack día a día.

## Scripts

| Script        | Qué hace                                                                  |
|---------------|---------------------------------------------------------------------------|
| `deploy.sh`   | `terraform apply` + dump local → schema + data a RDS + push imagen + restart app. Idempotente. |
| `destroy.sh`  | Backup RDS → `terraform destroy`. Costo AWS = $0 después.                  |
| `stop.sh`     | Para EC2 + RDS (preserva data). Gratis salvo ~$0.10/mes EBS residual.     |
| `start.sh`    | Enciende EC2 + RDS, refresca IP si cambió, restart app.                   |
| `backup.sh`   | `pg_dump` RDS → archivo local `rds_backup_<timestamp>.sql`.               |
| `logs.sh`     | `journalctl -u apuestas-app -f` via SSH.                                  |

## Primer uso

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

## Workflow típico

**Terminas el día de pruebas**
```bash
./scripts/stop.sh     # preserva data, corta costo
```

**Retomas al día siguiente**
```bash
./scripts/start.sh    # enciende + restart app
```

**Terminas la semana / vacaciones largas**
```bash
./scripts/destroy.sh  # saca backup y destruye todo
```

**Vuelves**
```bash
./scripts/deploy.sh   # recrea todo desde cero + re-carga data del local postgres18
```

## Fuente de datos

`deploy.sh` usa el container local `postgres18` (de `docker-compose.yaml`) como source of truth. Si paraste Docker, primero:

```bash
docker compose up -d postgres
```

Si quieres restaurar desde un backup RDS anterior en vez del local:

```bash
# Edita deploy.sh paso 3: cambia `docker exec pg_dump ...` por `cp /tmp/rds_backup_XXX.sql /tmp/apuestas_schema_data.sql`
```

## Requisitos

- `terraform` ≥ 1.6
- `aws` CLI v2 configurado
- `docker` con container `postgres18` corriendo (solo para `deploy.sh`)
- Llave SSH en `~/.ssh/apuestas-key.pem`
