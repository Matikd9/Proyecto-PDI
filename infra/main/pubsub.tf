# Bus de eventos: la API publica cada cambio de estado; notificaciones lo recibe por push autenticado.
resource "google_pubsub_topic" "eventos" {
  name       = "solicitud-eventos"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic_iam_member" "api_publica" {
  topic  = google_pubsub_topic.eventos.id
  role   = "roles/pubsub.publisher"
  member = google_service_account.api.member
}

resource "google_service_account" "notificaciones" {
  account_id   = "sa-notificaciones"
  display_name = "Servicio de notificaciones"
}

resource "google_service_account" "pubsub_push" {
  account_id   = "sa-pubsub-push"
  display_name = "Identidad de la suscripción push"
}

resource "google_project_iam_member" "notificaciones_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.notificaciones.member
}

resource "google_pubsub_subscription" "notificaciones" {
  name                       = "notificaciones-push"
  topic                      = google_pubsub_topic.eventos.id
  ack_deadline_seconds       = 20
  message_retention_duration = "86400s"
  push_config {
    push_endpoint = google_cloud_run_v2_service.notificaciones.uri
    oidc_token { service_account_email = google_service_account.pubsub_push.email }
  }
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}
