output "documentos_bucket" { value = google_storage_bucket.documentos.name }
output "sa_api" { value = google_service_account.api.email }
output "sa_web" { value = google_service_account.web.email }

# Configuración pública del portal (la API key web no es secreta; ver identidad.tf).
output "firebase_config" {
  value = {
    apiKey     = nonsensitive(google_apikeys_key.web.key_string)
    authDomain = "${var.project_id}.firebaseapp.com"
    projectId  = var.project_id
  }
}
