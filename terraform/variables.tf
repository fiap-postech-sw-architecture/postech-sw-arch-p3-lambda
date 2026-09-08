variable "jwt_secret" {
  description = "Segredo HS256 compartilhado com o app principal (mesmo JWT_SECRET)"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "ENCRYPTION_KEY do app principal (deriva a chave HMAC do documento_hash)"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "URL PostgreSQL do banco do app (postgresql://user:pass@host:5432/db)"
  type        = string
  sensitive   = true
}

variable "app_listener_arn" {
  description = "ARN do listener TCP 8000 do NLB interno da aplicacao"
  type        = string

  validation {
    condition = can(regex(
      "^arn:aws:elasticloadbalancing:us-east-1:[0-9]{12}:listener/net/.+$",
      var.app_listener_arn,
    ))
    error_message = "app_listener_arn deve ser um ARN de listener NLB em us-east-1."
  }
}
