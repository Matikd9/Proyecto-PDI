resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "identitytoolkit.googleapis.com",
    "apikeys.googleapis.com",
    "logging.googleapis.com",
    "aiplatform.googleapis.com", # Gemini (lectura de documentos)
  ])
  service            = each.value
  disable_on_destroy = false
}
