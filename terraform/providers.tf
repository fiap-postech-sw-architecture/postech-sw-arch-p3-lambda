terraform {
  required_version = ">= 1.10"

  backend "s3" {
    bucket       = "pytstop-terraform-state-924563550535"
    key          = "lambda/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

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
  region = "us-east-1"

  default_tags {
    tags = {
      Projeto       = "pytstop"
      Fase          = "3"
      Componente    = "autenticacao-cpf"
      GerenciadoPor = "terraform"
    }
  }
}
