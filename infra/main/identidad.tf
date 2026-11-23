locals {
  dominios = concat(var.dominios_web, [trimprefix(local.url_web, "https://")])
}

# Identity Platform no se puede desactivar: destroy solo lo quita del estado. Al recrear, se adopta la existente.
import {
  to = google_identity_platform_config.auth
  id = "projects/${var.project_id}/config"
}

# Identity Platform: registro e inicio de sesión con correo y contraseña (gratis bajo 50.000 MAU).
resource "google_identity_platform_config" "auth" {
  authorized_domains = local.dominios
  sign_in {
    allow_duplicate_emails = false
    email {
      enabled           = true
      password_required = true
    }
    phone_number { enabled = false } # la API lo devuelve siempre; declararlo evita drift
  }
  depends_on = [google_project_service.apis]
}

# API key del navegador: es pública por diseño; se limita a las APIs de autenticación y a los dominios del portal.
resource "google_apikeys_key" "web" {
  name         = "portal-web-${random_id.sufijo.hex}" # las keys borradas reservan su nombre 30 días
  display_name = "Portal web (Identity Platform)"
  restrictions {
    api_targets { service = "identitytoolkit.googleapis.com" }
    api_targets { service = "securetoken.googleapis.com" }
    browser_key_restrictions {
      allowed_referrers = flatten([for d in local.dominios : ["http://${d}:*/*", "https://${d}/*"]])
    }
  }
  depends_on = [google_project_service.apis]
}
