# Una cuenta de servicio por servicio, con roles sobre el recurso concreto cuando se puede.
# Los permisos sobre Secret Manager y Pub/Sub se agregan junto con esos recursos (T8).

resource "google_service_account" "api" {
  account_id   = "sa-api"
  display_name = "API de Trámites (Cloud Run y jobs)"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "web" {
  account_id   = "sa-web"
  display_name = "Portal web (sin permisos)"
  depends_on   = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "api_documentos" {
  bucket = google_storage_bucket.documentos.name
  role   = "roles/storage.objectUser"
  member = google_service_account.api.member
}

resource "google_project_iam_member" "api" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/firebaseauth.viewer", # revocación de tokens y búsqueda por email (bootstrap-admin)
  ])
  project = var.project_id
  role    = each.value
  member  = google_service_account.api.member
}
