# Pruebas realizadas

Registro de lo que se probó, cómo y con qué resultado. Solo se anota lo que efectivamente se ejecutó.

## Pruebas automáticas de la API (`app/api/tests`)

| Fecha | Base de datos | Resultado |
|---|---|---|
| 23-11-2026 | SQLite en memoria | 42 pasan |
| 23-11-2026 | PostgreSQL 16 (Docker) | 42 pasan |

Cubren roles y permisos (incluido 404 ante recursos ajenos), validación de archivos, máquina de estados,
validación simulada, administración de usuarios, `bootstrap-admin` y el bloqueo del modo `dev` en Cloud Run.

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

## Datos ficticios para la validación simulada

| RUT | Resultado |
|---|---|
| `12345678-5` | Validación correcta → revisión del funcionario |
| `11222000-3` | Alerta simulada (Interpol) → "En revisión", sin motivo visible |
| `15999999-8` | Identidad no coincide (Registro Civil simulado) → "En revisión" |
| `44555111-2` | Sin registros de viaje → "Observada", pide respaldo |
| `12345678-0` | RUT inválido → "Observada" |
