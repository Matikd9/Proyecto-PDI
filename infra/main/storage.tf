# Documentos de las solicitudes: privado, solo accesible por la cuenta de servicio de la API.
resource "google_storage_bucket" "documentos" {
  name                        = "${var.project_id}-documentos"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # PoC con datos ficticios: permite terraform destroy
  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}
