mock_provider "aws" {}
mock_provider "archive" {}

variables {
  jwt_secret       = "01234567890123456789012345678901"
  encryption_key   = "01234567890123456789012345678901"
  database_url     = "postgresql://user:pass@db.internal:5432/pytstop"
  app_listener_arn = "arn:aws:elasticloadbalancing:us-east-1:924563550535:listener/net/pytstop/0000000000000000/1111111111111111"
}

run "private_proxy" {
  command = plan

  override_data {
    target = data.aws_caller_identity.current
    values = { account_id = "924563550535" }
  }

  override_data {
    target = data.aws_vpc.default
    values = { id = "vpc-00000000000000000", cidr_block = "172.31.0.0/16" }
  }

  override_data {
    target = data.aws_subnets.default
    values = { ids = ["subnet-public"] }
  }

  override_data {
    target = data.aws_subnets.private
    values = { ids = ["subnet-private-a", "subnet-private-b"] }
  }

  assert {
    condition     = aws_apigatewayv2_integration.minhas_ordens.connection_type == "VPC_LINK"
    error_message = "As rotas de cliente devem usar VPC Link."
  }

  assert {
    condition     = aws_apigatewayv2_integration.minhas_ordens.integration_uri == var.app_listener_arn
    error_message = "A integracao deve apontar para o listener do NLB."
  }

  assert {
    condition = (
      aws_apigatewayv2_integration.minhas_ordens.request_parameters["overwrite:path"]
      == "$request.path"
    )
    error_message = "O prefixo do stage deve ser removido antes do FastAPI."
  }

  assert {
    condition = (
      aws_vpc_security_group_egress_rule.vpc_link_app.from_port == 8000 &&
      aws_vpc_security_group_egress_rule.vpc_link_app.to_port == 8000
    )
    error_message = "O VPC Link deve sair somente pela porta da API."
  }

  assert {
    condition = contains([
      for filter in data.aws_subnets.default.filter :
      "${filter.name}:${join(",", filter.values)}"
    ], "default-for-az:true")
    error_message = "A Lambda de autenticacao deve usar somente subnets publicas."
  }
}
