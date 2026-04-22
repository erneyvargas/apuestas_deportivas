data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_app" {
  name               = "${local.name_prefix}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# SSM Session Manager (conectarse sin llave SSH si quieres)
resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.ec2_app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Pull ECR
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Leer el parámetro SSM (URI DB)
data "aws_iam_policy_document" "ssm_read_uri" {
  statement {
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = [aws_ssm_parameter.postgres_uri.arn]
  }

  statement {
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "ssm_read_uri" {
  name   = "${local.name_prefix}-ssm-read-uri"
  policy = data.aws_iam_policy_document.ssm_read_uri.json
}

resource "aws_iam_role_policy_attachment" "ssm_read_uri" {
  role       = aws_iam_role.ec2_app.name
  policy_arn = aws_iam_policy.ssm_read_uri.arn
}

resource "aws_iam_instance_profile" "ec2_app" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2_app.name
}
