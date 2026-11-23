# Cloud SQL PostgreSQL 16. La edición ENTERPRISE es obligatoria: Enterprise Plus (por defecto en PG16+)
# no admite db-f1-micro. Costo en Santiago: USD 0,0147/h + disco (ver docs/05-costos.md).
# GCP reserva el nombre de una instancia borrada por días: el sufijo permite destruir y recrear.
resource "random_id" "sufijo" {
  byte_length = 2
}

resource "google_sql_database_instance" "pg" {
  name                = "pg-tramites-${random_id.sufijo.hex}"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = false # PoC: permite terraform destroy

  settings {
    edition           = "ENTERPRISE"
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = false
    activation_policy = var.sql_activa

    ip_configuration {
      ipv4_enabled    = false # sin IP pública
      private_network = google_compute_network.vpc.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
    backup_configuration { enabled = false } # PoC con datos ficticios: se ahorra el costo de respaldos
  }
  depends_on = [google_service_networking_connection.psa]
}

resource "google_sql_database" "tramites" {
  name            = "tramites"
  instance        = google_sql_database_instance.pg.name
  deletion_policy = "ABANDON" # se borra con la instancia; así destroy funciona aunque esté pausada
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_user" "app" {
  name            = "tramites"
  instance        = google_sql_database_instance.pg.name
  password        = random_password.db.result
  deletion_policy = "ABANDON"
}
