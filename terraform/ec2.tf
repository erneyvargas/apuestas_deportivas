# Amazon Linux 2023 AMI (x86_64, free tier compatible con t3.micro)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

locals {
  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    dnf update -y
    dnf install -y docker jq
    systemctl enable --now docker
    usermod -aG docker ec2-user

    REGION="${var.aws_region}"
    ACCOUNT_ID="${data.aws_caller_identity.current.account_id}"
    REPO="${aws_ecr_repository.app.repository_url}"
    PARAM="${aws_ssm_parameter.postgres_uri.name}"

    # Login ECR
    aws ecr get-login-password --region "$REGION" \
      | docker login --username AWS --password-stdin "$${REPO%/*}"

    # Leer URI Postgres desde SSM
    POSTGRES_URI=$(aws ssm get-parameter --name "$PARAM" --with-decryption \
      --region "$REGION" --query Parameter.Value --output text)

    # Pull + run (reinicia si el contenedor falla)
    docker pull "$REPO:${var.container_image_tag}" || true

    # Env file (evita que systemd interprete % en el URI)
    umask 077
    cat >/etc/apuestas-app.env <<ENV
    POSTGRES_URI=$POSTGRES_URI
    ENV
    chmod 600 /etc/apuestas-app.env

    cat >/etc/systemd/system/apuestas-app.service <<'UNIT'
    [Unit]
    Description=Apuestas app container
    After=docker.service
    Requires=docker.service

    [Service]
    Restart=always
    RestartSec=10
    ExecStartPre=-/usr/bin/docker rm -f apuestas-app
    ExecStart=/usr/bin/docker run --rm --name apuestas-app \
      --env-file /etc/apuestas-app.env \
      -p 8001:8001 \
      IMAGE_PLACEHOLDER
    ExecStop=/usr/bin/docker stop apuestas-app

    [Install]
    WantedBy=multi-user.target
    UNIT

    sed -i "s|IMAGE_PLACEHOLDER|$REPO:${var.container_image_tag}|" /etc/systemd/system/apuestas-app.service

    systemctl daemon-reload
    systemctl enable --now apuestas-app.service || true
  EOF
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_app.name
  associate_public_ip_address = true
  key_name                    = var.ssh_key_name

  user_data                   = local.user_data
  user_data_replace_on_change = false

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${local.name_prefix}-app" }

  # No recrear si cambia solo user_data (re-ejecutar manualmente con SSM si hace falta)
  lifecycle {
    ignore_changes = [user_data]
  }
}
