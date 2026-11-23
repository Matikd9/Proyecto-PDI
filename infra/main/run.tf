data "google_project" "actual" {}

locals {
  registro = "${var.region}-docker.pkg.dev/${var.project_id}/imagenes"
  # La URL de Cloud Run es determinista; calcularla evita un ciclo entre el portal y la API key.
  url_web = "https://web-${data.google_project.actual.number}.${var.region}.run.app"
  url_api = "https://api-${data.google_project.actual.number}.${var.region}.run.app"

  env_api = {
    ENTORNO       = "dev"
    AUTH_MODE     = "firebase"
    GCP_PROJECT   = var.project_id
    DB_HOST       = google_sql_database_instance.pg.private_ip_address
    DB_NAME       = google_sql_database.tramites.name
    DB_USER       = google_sql_user.app.name
    DB_SSLMODE    = "require"
    STORAGE_MODE  = "gcs"
    GCS_BUCKET    = google_storage_bucket.documentos.name
    EVENTS_MODE   = "pubsub"
    PUBSUB_TOPIC  = google_pubsub_topic.eventos.name
    CORS_ORIGINS  = local.url_web
    WEB_URL       = local.url_web
    GEMINI_MODELO = var.gemini_modelo
  }
}

# ---------- API ----------
resource "google_cloud_run_v2_service" "api" {
  name                = "api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2 # techo de costo y de conexiones (db-f1-micro admite 25)
    }
    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.negocio.id
      }
    }
    containers {
      image = "${local.registro}/api:${var.image_tag}"
      resources {
        limits            = { cpu = "1", memory = "512Mi" }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      dynamic "env" {
        for_each = local.env_api
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      startup_probe {
        http_get { path = "/api/v1/health" }
        initial_delay_seconds = 2
        period_seconds        = 5
        failure_threshold     = 10
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.api_lee_clave, google_secret_manager_secret_version.db_password]
}

# ---------- Portal ----------
resource "google_cloud_run_v2_service" "web" {
  name                = "web"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.web.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = "${local.registro}/web:${var.image_tag}"
      resources {
        limits   = { cpu = "1", memory = "256Mi" }
        cpu_idle = true
      }
      env {
        name  = "API_URL"
        value = local.url_api
      }
      env {
        name  = "AUTH_MODE"
        value = "firebase"
      }
      env {
        name  = "FIREBASE_API_KEY"
        value = google_apikeys_key.web.key_string
      }
      env {
        name  = "FIREBASE_AUTH_DOMAIN"
        value = "${var.project_id}.firebaseapp.com"
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }
    }
  }
}

# ---------- Notificaciones (solo Pub/Sub puede invocarlo) ----------
resource "google_cloud_run_v2_service" "notificaciones" {
  name                = "notificaciones"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false

  template {
    service_account = google_service_account.notificaciones.email
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image = "${local.registro}/notificaciones:${var.image_tag}"
      resources {
        limits   = { cpu = "1", memory = "256Mi" }
        cpu_idle = true
      }
    }
  }
}

# Portal y API son públicos (la API exige token en todo salvo health, catálogo y verificación).
resource "google_cloud_run_v2_service_iam_member" "publico" {
  for_each = { api = google_cloud_run_v2_service.api.name, web = google_cloud_run_v2_service.web.name }
  name     = each.value
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invoca" {
  name     = google_cloud_run_v2_service.notificaciones.name
  location = var.region
  role     = "roles/run.invoker"
  member   = google_service_account.pubsub_push.member
}

# ---------- Jobs administrativos (misma imagen que la API) ----------
resource "google_cloud_run_v2_job" "tareas" {
  for_each            = { migrate = ["migrate"], bootstrap-admin = ["bootstrap-admin", "--email", "definir@al-ejecutar.cl"] }
  name                = each.key
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.api.email
      max_retries     = 0
      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"
        network_interfaces {
          network    = google_compute_network.vpc.id
          subnetwork = google_compute_subnetwork.negocio.id
        }
      }
      containers {
        image   = "${local.registro}/api:${var.image_tag}"
        command = ["python", "-m", "app.cli"]
        args    = each.value
        dynamic "env" {
          for_each = local.env_api
          content {
            name  = env.key
            value = env.value
          }
        }
        env {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.api_lee_clave, google_secret_manager_secret_version.db_password]
}
