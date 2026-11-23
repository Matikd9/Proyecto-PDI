# Despliegue en GCP desde cero

Procedimiento para replicar la infraestructura en un proyecto propio. Los comandos son para PowerShell.
En PowerShell, los argumentos `-var-file=...` y `-out=...` de Terraform **deben ir entre comillas**.

> Estado: los pasos 1 a 4 están implementados y probados (23-11-2026). Las imágenes, la red, Cloud SQL y
> Cloud Run se agregarán en T8.

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

## 4. Infraestructura principal (estado remoto en GCS)

```powershell
cd ../main
Copy-Item ../envs/dev.tfvars.example ../envs/dev.tfvars   # editar project_id si corresponde
terraform init "-backend-config=bucket=lab3-pdi-vpm-tfstate"
terraform apply "-var-file=../envs/dev.tfvars"
```

Con lo implementado hasta ahora crea 18 recursos: las APIs, el bucket privado de documentos, las cuentas de
servicio `sa-api` y `sa-web` con sus roles, Identity Platform (correo y contraseña) y la API key del portal,
restringida a las APIs de autenticación y a los dominios de `dominios_web`.

**Comprobaciones realizadas:**

- Un segundo `terraform plan` en `bootstrap` y en `main` responde "No changes".
- Se registró una cuenta ficticia con la API key enviando como referer `localhost`, y luego se eliminó.
- Con un referer de otro dominio, la API key responde 403.

## Costos de lo creado hasta ahora

Ninguno de estos recursos tiene costo fijo. Los buckets vacíos, el registro sin imágenes, las APIs, las
cuentas de servicio e Identity Platform (bajo 50.000 usuarios activos al mes) cuestan ≈ USD 0.

## Eliminar todo

```powershell
cd infra/main;      terraform destroy "-var-file=../envs/dev.tfvars"
cd ../bootstrap;    terraform destroy "-var=project_id=lab3-pdi-vpm"
```

O, de forma definitiva: `gcloud projects delete lab3-pdi-vpm`.
