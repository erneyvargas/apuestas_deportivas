# Terraform — Apuestas Deportivas AWS (Free Tier)

Stack mínimo costo para pruebas. **Asume cuenta AWS nueva con Free Tier activo (primeros 12 meses).**

## Servicios y costo

| Recurso              | Config                  | Costo Free Tier                |
|----------------------|-------------------------|--------------------------------|
| EC2 `t3.micro`       | 1 instancia 24/7        | 750 h/mes gratis (12 meses)    |
| RDS `db.t3.micro`    | Single-AZ, 20 GB gp2    | 750 h + 20 GB gratis (12 meses)|
| EBS gp3 20 GB (EC2)  | —                       | 30 GB gp2/gp3 gratis           |
| ECR                  | 3 imágenes              | 500 MB gratis (siempre)        |
| SSM Parameter Store  | 1 SecureString Standard | Gratis                         |
| VPC / IGW / SG       | —                       | Gratis                         |
| Data transfer out    | —                       | 100 GB/mes gratis              |
| **Total estimado**   |                         | **$0** dentro de free tier     |

**Fuera del free tier** (después de 12 meses): ~$20–25/mes.

## Lo que NO incluye (para ahorrar)

- ❌ NAT Gateway ($32/mes) → EC2 va en subnet pública con IGW directo
- ❌ Fargate (sin free tier) → reemplazado por EC2 t3.micro + Docker
- ❌ Secrets Manager ($0.40/secret) → SSM Parameter Store Standard (gratis)
- ❌ Multi-AZ, Performance Insights, Enhanced Monitoring, backups de pago
- ❌ Graviton (`t4g`) → Free tier x86 solo (`t3`)

## Layout

```
main.tf              provider, locals
variables.tf
vpc.tf               VPC, 2 subnets públicas (EC2), 2 privadas (RDS), IGW
security_groups.tf   EC2 SG (SSH tu IP), DB SG (5432 desde EC2)
rds.tf               Postgres 18, db.t3.micro Single-AZ
ssm.tf               SecureString con POSTGRES_URI
ec2.tf               t3.micro + user_data (instala Docker, corre app)
ecr.tf               repo con 3 imágenes max
iam.tf               instance profile EC2 (SSM Session Manager + ECR + param read)
outputs.tf
```

## Pasos

### 1. Prereqs

```bash
# En AWS Console -> EC2 -> Key Pairs -> Create key pair
# Descargar .pem, mover a ~/.ssh/, chmod 400
chmod 400 ~/.ssh/mi-llave.pem

# Tu IP pública
curl ifconfig.me

cp terraform.tfvars.example terraform.tfvars
# editar ssh_key_name y allowed_ssh_cidr
```

### 2. Init + apply (primera vez)

```bash
terraform init
terraform apply
```

Primer apply: EC2 falla al pull imagen (ECR aún vacía). Normal.

### 3. Build + push imagen (desde tu máquina)

```bash
REPO=$(terraform output -raw ecr_repository_url)
REGION=$(terraform output -raw rds_endpoint >/dev/null 2>&1; awk -F\" '/aws_region/{print $4; exit}' terraform.tfvars || echo us-east-1)

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${REPO%/*}"

# Build x86_64 (t3.micro es x86)
docker build --platform linux/amd64 -t "$REPO:latest" ..
docker push "$REPO:latest"
```

### 4. Cargar schema en RDS

RDS es privada. Opción más simple: ejecutar `psql` desde la EC2 vía SSM Session Manager.

```bash
INSTANCE=$(terraform output -raw ec2_instance_id)
aws ssm start-session --target "$INSTANCE"

# dentro de la EC2:
sudo dnf install -y postgresql17
URI=$(aws ssm get-parameter --name /apuestas-dev/postgres_uri --with-decryption --query Parameter.Value --output text)
# copia schema.sql (scp antes, o pega inline)
psql "$URI" -f schema.sql
```

O con scp desde tu máquina:

```bash
IP=$(terraform output -raw ec2_public_ip)
scp -i ~/.ssh/mi-llave.pem ../infrastructure/persistence/schema.sql ec2-user@"$IP":/tmp/
ssh -i ~/.ssh/mi-llave.pem ec2-user@"$IP" 'sudo dnf install -y postgresql17 && URI=$(aws ssm get-parameter --name /apuestas-dev/postgres_uri --with-decryption --query Parameter.Value --output text) && psql "$URI" -f /tmp/schema.sql'
```

### 5. Arrancar app

```bash
INSTANCE=$(terraform output -raw ec2_instance_id)
aws ssm start-session --target "$INSTANCE"
# dentro de EC2:
sudo systemctl restart apuestas-app
sudo journalctl -u apuestas-app -f
```

## Redesplegar nueva imagen

```bash
docker build --platform linux/amd64 -t "$REPO:latest" ..
docker push "$REPO:latest"

# en EC2 (SSM):
sudo docker pull "$REPO:latest" && sudo systemctl restart apuestas-app
```

## Apagar cuando no uses (ahorrar horas)

```bash
# apagar EC2 (no cuenta horas cuando está stopped, pero EBS sigue cobrando mínimo)
aws ec2 stop-instances --instance-ids $(terraform output -raw ec2_instance_id)

# RDS también se puede stop (máx 7 días, luego se auto-enciende)
aws rds stop-db-instance --db-instance-identifier apuestas-dev-postgres
```

## Destroy

```bash
terraform destroy
```

## Credenciales DB

Generadas por Terraform (`random_password`). Ver:

```bash
aws ssm get-parameter --name /apuestas-dev/postgres_uri --with-decryption --query Parameter.Value --output text
```

El URI queda como env var `POSTGRES_URI` dentro del container (systemd unit `apuestas-app.service`). `postgres_config.py` lo lee sin cambios.
