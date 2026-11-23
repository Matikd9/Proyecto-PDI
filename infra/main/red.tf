# VPC privada: la API sale a ella con Direct VPC egress y llega a Cloud SQL por IP privada.
resource "google_compute_network" "vpc" {
  name                    = "vpc-pdi-dev"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "negocio" {
  name                     = "snet-negocio"
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = "10.10.2.0/24"
  region                   = var.region
  private_ip_google_access = true
}

# Rango reservado para los servicios administrados de Google (Private Services Access).
resource "google_compute_global_address" "psa" {
  name          = "psa-servicios-google"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa.name]
  deletion_policy         = "ABANDON" # evita el error conocido al destruir mientras Cloud SQL se elimina
}
