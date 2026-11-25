# Despliegue en GCP desde cero

Procedimiento para replicar la infraestructura en un proyecto propio. Los comandos son para PowerShell.
En PowerShell, los argumentos `-var-file=...` y `-out=...` de Terraform **deben ir entre comillas**.

> Estado: todos los pasos están implementados y probados en `lab3-pdi-vpm`, incluida la recreación desde cero
> (23-11-2026; última versión desplegada el 24-11-2026).
> URL de ejemplo: **https://web-636986210007.southamerica-west1.run.app**

## Requisitos

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) y [Terraform ≥ 1.6](https://developer.hashicorp.com/terraform/install)
  (en Windows: `winget install --id Google.CloudSDK -e` y `winget install --id Hashicorp.Terraform -e`).
- Una cuenta de facturación con créditos.

## 1. Autenticación

```powershell
gcloud auth login
gcloud auth application-default login
```

## 2. Proyecto, facturación y alerta de presupuesto

```powershell
gcloud projects create lab3-pdi-vpm --name="Lab3 PDI VPM"
gcloud billing projects link lab3-pdi-vpm --billing-account=<ID_CUENTA_FACTURACION>
gcloud config set project lab3-pdi-vpm
gcloud auth application-default set-quota-project lab3-pdi-vpm
gcloud services enable billingbudgets.googleapis.com
gcloud billing budgets create --billing-account=<ID_CUENTA_FACTURACION> --display-name=lab3-pdi-vpm --budget-amount=25USD --filter-projects=projects/lab3-pdi-vpm --threshold-rule=percent=0.4 --threshold-rule=percent=0.8 --threshold-rule=percent=1.0
```

Si el ID `lab3-pdi-vpm` ya existe (los ID son globales), use otro y ajústelo en todos los pasos.
La alerta solo notifica por correo: no detiene el gasto. Justo después de crear el proyecto, `budgets create`
puede fallar por permisos durante ~1 minuto; basta con reintentar.

## 3. Bootstrap (estado local)

Crea el bucket del estado de Terraform, el bucket de código fuente para Cloud Build, Artifact Registry y la
cuenta de servicio `sa-build`.

```powershell
cd infra/bootstrap
terraform init
terraform apply "-var=project_id=lab3-pdi-vpm"
```

Resultado esperado: 13 recursos creados.

| Salida | Valor en nuestro proyecto |
|---|---|
| `tfstate_bucket` | `lab3-pdi-vpm-tfstate` |
| `build_bucket` | `lab3-pdi-vpm-build` |
| `registry` | `southamerica-west1-docker.pkg.dev/lab3-pdi-vpm/imagenes` |
| `build_service_account` | `sa-build@lab3-pdi-vpm.iam.gserviceaccount.com` |

## 4. Imágenes, infraestructura principal y migración (un comando)

```powershell
Copy-Item infra/envs/dev.tfvars.example infra/envs/dev.tfvars   # editar project_id si corresponde
./scripts/deploy.ps1                                            # o: ./scripts/deploy.ps1 -ProjectId <id>
```

El script hace tres cosas:

1. **Compila** las imágenes `api`, `web` y `notificaciones` con Cloud Build (región Santiago, cuenta `sa-build`)
   y las publica en Artifact Registry con la etiqueta = SHA corto de git.
2. **Aplica** `infra/main` con esa etiqueta (estado remoto en `<project_id>-tfstate`). La primera vez crea 46
   recursos y tarda ~8 minutos (Cloud SQL ~5 min).
3. **Migra** la base de datos ejecutando el Cloud Run Job `migrate`.

El script no pasa `sql_activa`, así que deja Cloud SQL **encendido** (`ALWAYS`) aunque estuviera pausado.
La primera vez, la lectura con Gemini puede fallar unos minutos con `PERMISSION_DENIED` mientras se propaga
el rol `aiplatform.user`; esas solicitudes pasan a revisión humana y luego funciona sin cambios.

Al final muestra la URL del portal. Equivalente manual:

```powershell
gcloud builds submit app/api --config cloudbuild.yaml --region southamerica-west1 --substitutions "_IMAGEN=southamerica-west1-docker.pkg.dev/lab3-pdi-vpm/imagenes/api:<tag>" --service-account projects/lab3-pdi-vpm/serviceAccounts/sa-build@lab3-pdi-vpm.iam.gserviceaccount.com --gcs-source-staging-dir gs://lab3-pdi-vpm-build/fuente
#   (repetir con app/web y app/notificaciones)
cd infra/main
terraform init "-backend-config=bucket=lab3-pdi-vpm-tfstate"
terraform apply "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>"
gcloud run jobs execute migrate --region southamerica-west1 --wait
```

### Qué crea `infra/main`

| Archivo | Recursos |
|---|---|
| `apis.tf` | APIs de Cloud Run, Cloud SQL, Compute, Service Networking, Secret Manager, Pub/Sub, Identity Toolkit, API Keys, Logging y Vertex AI (Gemini) |
| `red.tf` | VPC `vpc-pdi-dev`, subred `snet-negocio` 10.10.2.0/24, rango y conexión de Private Services Access |
| `sql.tf` | Cloud SQL PostgreSQL 16, edición Enterprise, `db-f1-micro`, solo IP privada y TLS obligatorio; base y usuario `tramites` |
| `secretos.tf` | Clave aleatoria de la base de datos en Secret Manager (réplica en Santiago), legible solo por `sa-api` |
| `storage.tf` | Bucket privado de documentos |
| `pubsub.tf` | Tema `solicitud-eventos` y suscripción push autenticada (OIDC) hacia notificaciones |
| `run.tf` | Servicios `api` (Direct VPC egress), `web` y `notificaciones` (ingreso interno), y Jobs `migrate` y `bootstrap-admin` |
| `iam.tf` | Cuentas `sa-api`, `sa-web`, `sa-notificaciones` y `sa-pubsub-push`, con roles sobre el recurso concreto (salvo `aiplatform.user`, que solo existe a nivel de proyecto) |
| `identidad.tf` | Identity Platform (correo y contraseña) y API key restringida a autenticación y al dominio del portal |

## 5. Primer administrador

1. Registrarse en el portal con el correo que será administrador.
2. Promover la cuenta con el job (solo puede hacerlo alguien con permisos IAM en el proyecto):

```powershell
gcloud run jobs execute bootstrap-admin --region southamerica-west1 --args "bootstrap-admin,--email,<correo>" --wait
```

3. Desde **Administración**, ese usuario puede asignar el rol de funcionario a otras cuentas.

## Comprobaciones realizadas

- Un segundo `terraform plan` en `bootstrap` y en `main` responde "No changes".
- Flujo completo en la URL pública (ver `docs/04-pruebas.md`).

## Costos

Ver `docs/05-costos.md`. Lo único con costo fijo es Cloud SQL: ≈ USD 0,44/día encendido. Para pausarlo:

```powershell
cd infra/main
terraform apply "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>" "-var=sql_activa=NEVER"
```

## Eliminar todo

```powershell
cd infra/main;      terraform destroy "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>"
cd ../bootstrap;    terraform destroy "-var=project_id=lab3-pdi-vpm"
```

O, de forma definitiva: `gcloud projects delete lab3-pdi-vpm`.

Identity Platform no se puede desactivar: `destroy` solo lo quita del estado y las cuentas registradas se
conservan. Al volver a desplegar, un bloque `import` adopta la configuración existente (D-12). Para borrar
también las cuentas hay que eliminar el proyecto.

**Al destruir `infra/main`, la subred puede tardar en liberarse.** Cloud Run reserva IPs en la subred para
Direct VPC egress y Google las libera entre minutos y ~2 horas después de borrar los servicios. Mientras tanto
`terraform destroy` falla con `resourceInUseByAnotherResource` en `snet-negocio`. Basta con volver a
ejecutarlo más tarde: Cloud SQL y todo lo que tiene costo ya se habrá eliminado en el primer intento.
En nuestra prueba (23-11-2026) la subred se liberó ~1 h 30 min después (19.º reintento, cada 5 minutos).
