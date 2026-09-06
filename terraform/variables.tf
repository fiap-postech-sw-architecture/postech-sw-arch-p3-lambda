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

variable "app_base_url" {
  description = "URL publica do LoadBalancer da aplicacao no EKS, sem barra final"
  type        = string

  validation {
    condition     = can(regex("^https?://[A-Za-z0-9.-]+(:[0-9]+)?$", var.app_base_url))
    error_message = "app_base_url deve ser uma URL HTTP(S) sem caminho ou barra final."
  }
}
