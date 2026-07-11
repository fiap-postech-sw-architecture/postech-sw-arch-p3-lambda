terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  profile = var.aws_profile
  region  = "us-east-1"

  default_tags {
    tags = {
      Projeto       = "pytstop"
      Fase          = "3"
      Componente    = "autenticacao-cpf"
      GerenciadoPor = "terraform"
    }
  }
}
