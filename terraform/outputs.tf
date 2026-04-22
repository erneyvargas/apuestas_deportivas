output "vpc_id" {
  value = aws_vpc.main.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "postgres_uri_parameter" {
  value       = aws_ssm_parameter.postgres_uri.name
  description = "Nombre del parametro SSM con el URI Postgres"
}

output "ec2_public_ip" {
  value = aws_instance.app.public_ip
}

output "ec2_instance_id" {
  value = aws_instance.app.id
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ec2-user@${aws_instance.app.public_ip}"
}

output "gha_deploy_role_arn" {
  value       = aws_iam_role.gha_deploy.arn
  description = "Rol IAM que GitHub Actions asume via OIDC"
}

output "ecr_repository_name" {
  value = aws_ecr_repository.app.name
}
