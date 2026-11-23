terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
  # El bucket se indica al inicializar: terraform init -backend-config="bucket=<project_id>-tfstate"
  backend "gcs" {
    prefix = "main"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  # Identity Toolkit y API Keys exigen un proyecto de cuota al usar credenciales de usuario (ADC).
  user_project_override = true
  billing_project       = var.project_id
}
