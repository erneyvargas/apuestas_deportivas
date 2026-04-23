variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "apuestas"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

# --- DB ---
variable "db_name" {
  type    = string
  default = "apuestas_deportivas"
}

variable "db_username" {
  type    = string
  default = "apuestas_admin"
}

variable "db_password" {
  type        = string
  sensitive   = true
  nullable    = false
  description = "Password RDS. Pasar via TF_VAR_db_password para no commitear."
}

# Free Tier: db.t3.micro (x86). NO usar t4g (Graviton) si quieres cubrir free tier.
variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

# Free Tier: hasta 20 GB gp2
variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_engine_version" {
  type    = string
  default = "18.0"
}

# --- EC2 ---
# Free Tier: t3.micro (750h/mes primer año)
variable "ec2_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "ssh_key_name" {
  type        = string
  description = "Nombre de un EC2 key pair ya creado en la consola"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "Tu IP/32 para SSH (ej: 190.xx.xx.xx/32)"
}

variable "container_image_tag" {
  type    = string
  default = "latest"
}

# --- GitHub Actions OIDC ---
variable "github_repo" {
  type        = string
  description = "owner/repo al que se permite asumir el rol GHA (ej: erneyvargas/apuestas_deportivas)"
}
