# Costos de la prueba de concepto

Precios de lista en `southamerica-west1` (Santiago), consultados en la página oficial de precios de GCP el
23-11-2026. Son estimaciones: el gasto real se revisa en la consola (Facturación → Informes).

## Recursos desplegados

| Recurso | Precio | Encendido 24/7 | Pausado | ¿Cobra sin tráfico? |
|---|---|---|---|---|
| Cloud SQL `db-f1-micro` (Enterprise, zonal) | USD 0,0147/h | USD 10,73/mes | USD 0 | **Sí** |
| Disco Cloud SQL 10 GB SSD | USD 0,000326/GiB-h | USD 2,38/mes | USD 2,38/mes | **Sí, siempre** |
| Respaldos Cloud SQL | desactivados | 0 | 0 | — |
| Cloud Run (api, web, notificaciones, jobs) | nivel 2, escala a cero | ≈ 0 (nivel gratuito) | 0 | No |
| VPC, subred, Private Services Access, Direct VPC egress | sin cargo | 0 | 0 | No |
| Artifact Registry (~1 GB de imágenes) | 0,5 GB gratis, luego ~USD 0,10/GB | ≈ 0,10 | ≈ 0,10 | Mínimo |
| Cloud Build | 2.500 min/mes gratis | 0 | 0 | No |
| Secret Manager, Pub/Sub, Cloud Logging, Identity Platform | niveles gratuitos | 0 | 0 | No |
| Cloud Storage (documentos, estado, fuente de builds) | < 1 GB | < 0,05 | < 0,05 | Mínimo |
| **Total** | | **≈ USD 13,3/mes** (≈ USD 0,44/día) | **≈ USD 2,5/mes** | |

## Controles de gasto

- Alerta de presupuesto de USD 25 con avisos al 40 %, 80 % y 100 % (D-11). **Solo notifica, no detiene el gasto.**
- Cloud Run: mínimo 0 instancias y máximo 2 (1 para notificaciones).
- Sin balanceador, Cloud Armor, NAT ni VPN (son los recursos que cobran aunque no haya tráfico).

## Pausar, reanudar y eliminar

```powershell
cd infra/main
terraform apply "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>" "-var=sql_activa=NEVER"    # pausar Cloud SQL
terraform apply "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>" "-var=sql_activa=ALWAYS"   # reanudar
terraform destroy "-var-file=../envs/dev.tfvars" "-var=image_tag=<tag>"                          # eliminar todo lo de main
```

Con Cloud SQL pausado, el portal carga pero la API responde con error en las operaciones con datos.
