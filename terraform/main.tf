# Restricao AWS Academy: NAO criar recursos IAM. A role LabRole ja existe.
data "aws_caller_identity" "current" {}

locals {
  lab_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "tag:kubernetes.io/role/internal-elb"
    values = ["1"]
  }
}

resource "aws_security_group" "lambda_auth" {
  name        = "pytstop-lambda-auth"
  description = "Saida da Lambda de autenticacao para o RDS"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "lambda_postgres" {
  security_group_id = aws_security_group.lambda_auth.id
  description       = "PostgreSQL na VPC default"
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
  cidr_ipv4         = data.aws_vpc.default.cidr_block
}

resource "aws_security_group" "vpc_link" {
  name        = "pytstop-vpc-link"
  description = "Saida do VPC Link para a API no NLB interno"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "vpc_link_app" {
  security_group_id = aws_security_group.vpc_link.id
  description       = "API PytStop na VPC default"
  from_port         = 8000
  to_port           = 8000
  ip_protocol       = "tcp"
  cidr_ipv4         = data.aws_vpc.default.cidr_block
}

# Pacote da function: rode `make build` antes do apply -- ele instala as
# dependencias (wheels linux x86_64) e copia src/ para build/lambda/.
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda"
  output_path = "${path.module}/../build/autenticacao_cpf.zip"
}

resource "aws_lambda_function" "autenticacao_cpf" {
  function_name    = "pytstop-autenticacao-cpf"
  role             = local.lab_role_arn
  runtime          = "python3.13"
  handler          = "src.autenticacao_cpf.handler.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 10
  memory_size      = 256

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_auth.id]
  }

  environment {
    variables = {
      DATABASE_URL           = var.database_url
      JWT_SECRET             = var.jwt_secret
      ENCRYPTION_KEY         = var.encryption_key
      JWT_EXPIRATION_MINUTES = "30"
    }
  }
}

resource "aws_lambda_function" "authorizer" {
  function_name    = "pytstop-autenticacao-authorizer"
  role             = local.lab_role_arn
  runtime          = "python3.13"
  handler          = "src.autenticacao_cpf.authorizer.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 5
  memory_size      = 128

  environment {
    variables = {
      # So JWT_SECRET: o authorizer apenas valida JWT (importa token, nao
      # hashing) -- ENCRYPTION_KEY nao e exigida no cold start.
      JWT_SECRET = var.jwt_secret
    }
  }
}

resource "aws_apigatewayv2_api" "http" {
  name          = "pytstop-autenticacao"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "auth" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.autenticacao_cpf.invoke_arn
  payload_format_version = "2.0"
}

# Rota publica de autenticacao (sem authorizer, por definicao).
resource "aws_apigatewayv2_route" "post_auth" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /auth"
  target    = "integrations/${aws_apigatewayv2_integration.auth.id}"
}

# Lambda authorizer (payload v2, simple response) para rotas protegidas.
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id                            = aws_apigatewayv2_api.http.id
  name                              = "pytstop-lambda-authorizer"
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.authorizer.invoke_arn
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  identity_sources                  = ["$request.header.Authorization"]
}

resource "aws_apigatewayv2_vpc_link" "app" {
  name               = "pytstop-app"
  security_group_ids = [aws_security_group.vpc_link.id]
  subnet_ids         = data.aws_subnets.private.ids

  lifecycle {
    precondition {
      condition     = length(data.aws_subnets.private.ids) == 2
      error_message = "A VPC deve conter as duas subnets privadas do PytStop."
    }
  }
}

resource "aws_apigatewayv2_integration" "minhas_ordens" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "GET"
  integration_uri        = var.app_listener_arn
  connection_type        = "VPC_LINK"
  connection_id          = aws_apigatewayv2_vpc_link.app.id
  payload_format_version = "1.0"

  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}

resource "aws_apigatewayv2_route" "listar_minhas_ordens" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /api/v1/minhas-ordens"
  target             = "integrations/${aws_apigatewayv2_integration.minhas_ordens.id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "obter_minha_ordem" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /api/v1/minhas-ordens/{ordem_id}"
  target             = "integrations/${aws_apigatewayv2_integration.minhas_ordens.id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# aws_lambda_permission e resource-based policy da function (nao e recurso IAM
# da conta) -- permitido no AWS Academy.
resource "aws_lambda_permission" "apigw_auth" {
  statement_id  = "AllowAPIGatewayInvokeAuth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.autenticacao_cpf.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_authorizer" {
  statement_id  = "AllowAPIGatewayInvokeAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/authorizers/${aws_apigatewayv2_authorizer.jwt.id}"
}

resource "aws_apigatewayv2_stage" "homolog" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "homolog"
  auto_deploy = true
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "prod"
  auto_deploy = true
}
