# Restricao AWS Academy: NAO criar recursos IAM. A role LabRole ja existe na
# conta e e referenciada via data source (unica opcao permitida no laboratorio).
data "aws_iam_role" "lab_role" {
  name = "LabRole"
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
  role             = data.aws_iam_role.lab_role.arn
  runtime          = "python3.13"
  handler          = "src.autenticacao_cpf.handler.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 10
  memory_size      = 256

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
  role             = data.aws_iam_role.lab_role.arn
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

# Exemplo de rota protegida pelo authorizer. Na integracao final as rotas
# protegidas apontam para o app no EKS (integracao HTTP_PROXY); aqui a rota
# de exemplo reusa a integracao da lambda apenas para demonstrar o fluxo.
resource "aws_apigatewayv2_route" "exemplo_protegido" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /auth/exemplo-protegido"
  target             = "integrations/${aws_apigatewayv2_integration.auth.id}"
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
