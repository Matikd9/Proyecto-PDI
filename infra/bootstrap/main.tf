# Bootstrap: lo mínimo que debe existir antes del resto (estado local, se aplica una vez).
# Crea el bucket del estado remoto, Artifact Registry y la identidad de Cloud Build.

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "southamerica-west1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "tfstate" {
  name                        = "${var.project_id}-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # PoC: permite destruir todo; en producción sería false
  versioning { enabled = true }
  lifecycle_rule {
    condition { num_newer_versions = 10 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.apis]
}

# Código fuente que sube `gcloud builds submit` (se borra a los 7 días).
resource "google_storage_bucket" "build" {
  name                        = "${var.project_id}-build"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  lifecycle_rule {
    condition { age = 7 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.apis]
}

resource "google_artifact_registry_repository" "imagenes" {
  repository_id = "imagenes"
  location      = var.region
  format        = "DOCKER"
  description   = "Imágenes de la PoC (api, web, notificaciones)"

  # Conserva las 5 versiones más recientes de cada imagen; borra el resto tras 1 día.
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "conservar-recientes"
    action = "KEEP"
    most_recent_versions { keep_count = 5 }
  }
  cleanup_policies {
    id     = "borrar-antiguas"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "86400s"
    }
  }
  depends_on = [google_project_service.apis]
}

# Identidad propia para Cloud Build (privilegio mínimo, en vez de la cuenta por defecto).
resource "google_service_account" "build" {
  account_id   = "sa-build"
  display_name = "Cloud Build (imágenes de la PoC)"
  depends_on   = [google_project_service.apis]
}

resource "google_artifact_registry_repository_iam_member" "build_escribe" {
  repository = google_artifact_registry_repository.imagenes.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.build.member
}

resource "google_storage_bucket_iam_member" "build_lee_fuente" {
  bucket = google_storage_bucket.build.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.build.member
}

resource "google_project_iam_member" "build_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.build.member
}

output "tfstate_bucket" { value = google_storage_bucket.tfstate.name }
output "build_bucket" { value = google_storage_bucket.build.name }
output "build_service_account" { value = google_service_account.build.email }
output "registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.imagenes.repository_id}"
}
