resource "aws_ecr_repository" "app" {
  name                 = "${local.name_prefix}-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Free tier ECR = 500 MB/mes. Mantener solo 3 imagenes.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Mantener ultimas 3 imagenes"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = { type = "expire" }
      }
    ]
  })
}
