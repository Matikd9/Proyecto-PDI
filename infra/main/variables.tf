variable "project_id" {
  type        = string
  description = "ID del proyecto GCP (debe existir y tener facturación asociada)."
}

variable "region" {
  type    = string
  default = "southamerica-west1"
}

variable "dominios_web" {
  type        = list(string)
  description = "Dominios desde los que el portal puede usar Identity Platform y su API key."
  default     = ["localhost"]
}
