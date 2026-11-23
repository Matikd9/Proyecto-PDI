variable "project_id" {
  type        = string
  description = "ID del proyecto GCP (debe existir y tener facturación asociada)."
}

variable "region" {
  type    = string
  default = "southamerica-west1"
}

variable "image_tag" {
  type        = string
  description = "Etiqueta de las imágenes en Artifact Registry (SHA corto de git)."
}

variable "sql_activa" {
  type        = string
  description = "ALWAYS = Cloud SQL encendido; NEVER = pausado (solo se cobra el disco)."
  default     = "ALWAYS"
  validation {
    condition     = contains(["ALWAYS", "NEVER"], var.sql_activa)
    error_message = "Debe ser ALWAYS o NEVER."
  }
}

variable "dominios_web" {
  type        = list(string)
  description = "Dominios desde los que el portal puede usar Identity Platform y su API key."
  default     = ["localhost"]
}

variable "gemini_modelo" {
  description = "Modelo de Gemini para leer el documento de identidad (vacío = desactivado). Usa el endpoint global."
  type        = string
  default     = "gemini-3.1-flash-lite"
}
