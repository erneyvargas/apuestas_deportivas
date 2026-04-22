resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-app-sg"
  description = "EC2 app host"
  vpc_id      = aws_vpc.main.id

  # SSH solo desde tu IP (var.allowed_ssh_cidr)
  ingress {
    description = "SSH desde mi IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  egress {
    description = "all egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-app-sg" }
}

resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-db-sg"
  description = "RDS Postgres - solo app puede conectarse"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-db-sg" }
}

resource "aws_security_group_rule" "db_ingress_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app.id
  security_group_id        = aws_security_group.db.id
  description              = "Postgres desde EC2 app"
}

resource "aws_security_group_rule" "db_ingress_from_me" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = [var.allowed_ssh_cidr]
  security_group_id = aws_security_group.db.id
  description       = "Postgres desde mi IP publica"
}
