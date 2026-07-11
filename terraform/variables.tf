variable "aws_profile" {
  description = "Perfil AWS local (credenciais do AWS Academy)"
  type        = string
  default     = "academy"
}

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
