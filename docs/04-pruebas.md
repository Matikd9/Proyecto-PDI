# Pruebas realizadas

Registro de lo que se probó, cómo y con qué resultado. Solo se anota lo que efectivamente se ejecutó.

## Pruebas automáticas de la API (`app/api/tests`)

| Fecha | Base de datos | Resultado |
|---|---|---|
| 23-11-2026 | SQLite en memoria | 42 pasan |
| 23-11-2026 | PostgreSQL 16 (Docker) | 42 pasan |
| 24-11-2026 | SQLite en memoria (con la lectura de documentos y el certificado con logo) | 47 pasan, 2 omitidas (integración con GCS, requieren bucket real) |

Cubren roles y permisos (incluido 404 ante recursos ajenos), validación de archivos, máquina de estados,
validación simulada, lectura del documento con Gemini (simulado), administración de usuarios, `bootstrap-admin`
y el bloqueo del modo `dev` en Cloud Run.

## Flujo completo en navegador (local, modo `dev`, 23-11-2026)

Entorno: `docker compose` (Postgres 16 + API) y el portal servido por Vite y por la imagen nginx.

1. El ciudadano elige un trámite, ingresa, completa el formulario, adjunta un PDF ficticio y envía. Ve
   "En revisión" (el estado interno `PREAPROBADA` queda oculto).
2. `bootstrap-admin` dentro del contenedor promueve al primer administrador, que asigna el rol de funcionario
   desde la interfaz. Queda `ROL_CAMBIADO` en la auditoría.
3. El funcionario ve las 5 reglas en OK y aprueba. La solicitud queda emitida y asignada a él.
4. El ciudadano descarga el certificado PDF; otra cuenta recibe 404 al pedir esa solicitud.
5. La página pública `/verificar/<código>` confirma el certificado con el titular enmascarado.
6. En vista móvil (375 px) no hay desplazamiento horizontal y el menú se colapsa.

## Identity Platform real (local contra GCP, 23-11-2026)

Entorno: la API en el puerto 8090 con `AUTH_MODE=firebase` y el portal (misma imagen nginx) con
`AUTH_MODE=firebase` y la API key creada por Terraform.

| Prueba | Resultado |
|---|---|
| Registro de una cuenta ficticia desde el portal | Identity Platform crea la cuenta y la API verifica el token real. El usuario nace `ciudadano`. |
| API key con un referer de otro dominio | 403 |
| `bootstrap-admin` con una cuenta registrada | Promovida a administrador |
| `bootstrap-admin` con un email inexistente | Consulta Identity Platform, no crea nada y termina con código 1 |
| Panel de administración (comprueba revocación del token) | 200 |
| Revocar las sesiones de la cuenta y repetir con el mismo token | `/admin/*` → **401**; `/me` → 200 hasta que el token expire (≤ 1 h). Comportamiento esperado (ver D-04). |

Las cuentas de prueba se eliminaron de Identity Platform al terminar.

## Cloud Storage real (23-11-2026)

Prueba de integración `app/api/tests/test_gcs_integracion.py`, contra el bucket `lab3-pdi-vpm-documentos`.
Se omite en la suite normal; para ejecutarla:

```powershell
cd app/api
$env:TEST_GCS_BUCKET="lab3-pdi-vpm-documentos"; pytest tests/test_gcs_integracion.py
```

| Prueba | Resultado |
|---|---|
| Guardar, leer y eliminar un objeto; el tipo de contenido se conserva | ✅ |
| Intentar sobrescribir un documento existente | ✅ Rechazado (`if_generation_match=0`) |
| Flujo por la API: el ciudadano sube, el documento queda en `solicitudes/{uuid}/{uuid}`, el funcionario lo descarga, otra cuenta recibe 404 | ✅ |
| Lectura anónima por `https://storage.googleapis.com/...` | ✅ 403 |
| Otorgar `allUsers` sobre el bucket (incluso como dueño del proyecto) | ✅ Rechazado con 412 por la prevención de acceso público forzada |

Acceso al bucket: `sa-api` (`roles/storage.objectUser`) y los roles heredados por defecto del proyecto
(dueños, editores y lectores). Los objetos de prueba se eliminaron.

## Despliegue en GCP: flujo de punta a punta (23-11-2026)

URL: https://web-636986210007.southamerica-west1.run.app · imágenes `1625e74`.

| Paso | Componente probado | Resultado |
|---|---|---|
| Cloud Run `api` arranca | Sonda `/api/v1/health` (`SELECT 1` por IP privada y TLS a Cloud SQL) | ✅ |
| Job `migrate` | Alembic en Cloud SQL; el catálogo responde con 2 trámites | ✅ |
| El ciudadano se registra desde el portal | Identity Platform + `GET /me` (nace `ciudadano`) | ✅ |
| Crea la solicitud, adjunta un PDF y envía | Cloud SQL + Cloud Storage (`solicitudes/{uuid}/{uuid}`) | ✅ Ve "En revisión" |
| Job `bootstrap-admin --email admin-demo@ficticio.cl` | Cloud Run Job con IAM | ✅ |
| El admin promueve a `funcionario-demo@ficticio.cl` | `PATCH /admin/usuarios/{id}` (comprueba revocación) | ✅ |
| El funcionario descarga el documento y aprueba | Lectura desde GCS + transición a `EMITIDA` | ✅ |
| Notificaciones | Pub/Sub → push OIDC → Cloud Run interno → Cloud Logging: "recibida", "en revisión" y "emitida" | ✅ |
| El ciudadano descarga el certificado | PDF de 2,5 KB | ✅ |
| Verificación pública del código | `/verificar/<código>` → válido, titular enmascarado | ✅ |
| Llamar a `notificaciones` desde internet | Ingreso interno | ✅ 404 |
| `terraform plan` después del despliegue | Sin drift | ✅ "No changes" |

Cuentas ficticias de demostración (Identity Platform): `ciudadano-demo@ficticio.cl`,
`funcionario-demo@ficticio.cl` y `admin-demo@ficticio.cl`. La contraseña no se publica en el repositorio.

## Reproducibilidad: destruir y recrear (T11, 23-11-2026)

Se destruyó `infra/main` por completo y se recreó siguiendo solo `docs/03-despliegue.md`.

| Paso | Resultado |
|---|---|
| `terraform destroy` | Cloud SQL y todo lo con costo se eliminó en el primer intento. La subred `snet-negocio` se liberó ~1 h 30 min después (19 reintentos) |
| Primer `./scripts/deploy.ps1` | ❌ Falló al final: Identity Platform no se puede desactivar y ya existía. Se agregó un bloque `import` (D-12) |
| Segundo `./scripts/deploy.ps1` (commit `338b25d`) | ✅ Imágenes, 45 recursos, migración. Nueva instancia `pg-tramites-ffcd` |
| Health, catálogo, portal | ✅ `{"estado":"ok"}`, 2 trámites, portal 200; `notificaciones` desde internet → 404 |
| Usuarios | Las cuentas de Identity Platform se conservan; la base es nueva, así que entran como `ciudadano` en su primer `/me` |
| Job `bootstrap-admin` + `PATCH` del admin | ✅ admin → `administrador`, funcionario → `funcionario`; un ciudadano en `/admin` → 403 |
| Flujo vía API (`12345678-5`) | ✅ borrador → documento en GCS (`solicitudes/{uuid}/{uuid}`) → enviada (el ciudadano ve `EN_REVISION`, el backoffice `PREAPROBADA`) → `EMITIDA` → PDF de 2,5 KB |
| Notificaciones | ✅ 3 registros en Cloud Logging (recibida, en revisión, emitida) |
| Verificación pública | ✅ código del PDF → `valido: true`, titular enmascarado; código inventado → `valido: false` |
| `terraform plan` | ✅ "No changes" |
| Pausa de Cloud SQL | ✅ `sql_activa=NEVER` → instancia `STOPPED` |

## Lectura del documento con Gemini (T10, 23-11-2026)

Documento ficticio: un PDF de una página generado con reportlab, con "RUN: 12.345.678-5" y "ANA PRUEBA FICTICIA".

| Prueba | Resultado |
|---|---|
| Pruebas automáticas (`test_lectura_documentos.py`, Gemini simulado) | ✅ 5 casos: desactivada por defecto, coincide, número distinto, ilegible y error de Vertex AI |
| Llamada real desde local (`gemini-3.1-flash-lite`, endpoint global) | ✅ `numero_documento='12.345.678-5'`, `nombre_completo='ANA PRUEBA FICTICIA'`; 697 + 51 tokens |
| Primer intento en GCP justo después del despliegue | ❌ `PERMISSION_DENIED` (el rol `aiplatform.user` aún no se propagaba). Unos minutos después funcionó sin cambios |
| GCP, formulario con el mismo RUT | ✅ `LECTURA_DOCUMENTO=OK`, "Coincide: ANA PRUEBA FICTICIA" |
| GCP, formulario con otro RUT (`22333444-K`) | ✅ `ALERTA` → `EN_REVISION`; el ciudadano no ve el motivo, el funcionario sí: "El documento dice 12.345.678-5; el formulario, 22333444K" |

## Ajustes de interfaz y certificado (24-11-2026)

| Prueba | Resultado |
|---|---|
| Marca DPI y botón de ClaveÚnica (deshabilitado) en la URL pública | ✅ Sin errores en la consola del navegador; se ve bien en escritorio y en móvil |
| Admin que entra por "Ingreso de funcionarios" (local) | ✅ Redirige a `/admin` en vez de mostrar "No tiene permisos"; el funcionario llega a `/backoffice` |
| Certificado PDF con el logo DPI, descargado desde GCP | ✅ 16,5 KB, con la fuente Alfa Slab One incrustada |
| Documentos ficticios de `docs/demo/` leídos por Gemini (local) | ✅ Ambos números de RUT y nombres extraídos correctamente |

## Datos ficticios para la validación simulada

| RUT | Resultado |
|---|---|
| `12345678-5` | Validación correcta → revisión del funcionario |
| `11222000-3` | Alerta simulada (Interpol) → "En revisión", sin motivo visible |
| `15999999-8` | Identidad no coincide (Registro Civil simulado) → "En revisión" |
| `44555111-2` | Sin registros de viaje → "Observada", pide respaldo |
| `12345678-0` | RUT inválido → "Observada" |
