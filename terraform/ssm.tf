# SSM Parameter Store SecureString (Standard tier = gratis)
# Reemplaza Secrets Manager para minimizar costos.

resource "aws_ssm_parameter" "postgres_uri" {
  name        = "/${local.name_prefix}/postgres_uri"
  description = "URI completo Postgres con sslmode=require"
  type        = "SecureString"
  tier        = "Standard"

  value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.db_name}?sslmode=require"
}
