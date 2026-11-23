# Despliega la versión actual del repositorio: compila las imágenes, aplica Terraform y migra la base de datos.
# Requiere haber aplicado infra/bootstrap una vez (ver docs/03-despliegue.md).
#   ./scripts/deploy.ps1                       # proyecto por defecto
#   ./scripts/deploy.ps1 -ProjectId otro-id
param(
    [string]$ProjectId = "lab3-pdi-vpm",
    [string]$Region = "southamerica-west1"
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

$tag = git rev-parse --short HEAD
if (git status --porcelain) { Write-Warning "Hay cambios sin commit: la imagen $tag no incluirá exactamente lo que ve." }
$registro = "$Region-docker.pkg.dev/$ProjectId/imagenes"
$sa = "projects/$ProjectId/serviceAccounts/sa-build@$ProjectId.iam.gserviceaccount.com"

Write-Host "== 1/3 Compilando imágenes ($tag) con Cloud Build"
$builds = foreach ($s in "api", "web", "notificaciones") {
    gcloud builds submit "app/$s" --project $ProjectId --region $Region --config cloudbuild.yaml `
        --substitutions "_IMAGEN=$registro/${s}:$tag" --service-account $sa `
        --gcs-source-staging-dir "gs://$ProjectId-build/fuente" --async --format "value(id)"
}
foreach ($id in $builds) {
    # Los logs van solo a Cloud Logging, así que se espera consultando el estado.
    do {
        Start-Sleep 10
        $estado = gcloud builds describe $id --project $ProjectId --region $Region --format "value(status)"
    } while ($estado -in "QUEUED", "WORKING", "PENDING")
    if ($estado -ne "SUCCESS") { throw "La compilación $id terminó en $estado" }
}

Write-Host "== 2/3 Aplicando Terraform"
Push-Location infra/main
terraform init -input=false "-backend-config=bucket=$ProjectId-tfstate" | Out-Null
terraform apply -input=false -auto-approve "-var-file=../envs/dev.tfvars" "-var=image_tag=$tag"
if ($LASTEXITCODE -ne 0) { throw "terraform apply falló" }
$portal = terraform output -raw url_portal
Pop-Location

Write-Host "== 3/3 Migrando la base de datos"
gcloud run jobs execute migrate --project $ProjectId --region $Region --wait
if ($LASTEXITCODE -ne 0) { throw "La migración falló (ver logs del job 'migrate')" }

Write-Host "`nListo. Portal: $portal"
