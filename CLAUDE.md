# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto

Laboratorio 3 de Arquitectura Cloud (UAI, Grupo VPM): prueba de concepto de una plataforma para solicitar,
validar y emitir dos certificados migratorios de la PDI (Certificado de Viajes y Vigencia de Permanencia
Definitiva), desplegada en GCP `southamerica-west1` con Terraform. Es un trabajo académico: **no es un servicio
oficial de la PDI**, se usan solo datos ficticios y no se debe usar el logotipo de la PDI
(el portal usa la marca ficticia "DPI", en texto con tipografía propia; ver D-14). Las integraciones
institucionales (Clave Única, Registro Civil, Migraciones, Interpol) están **simuladas**, nunca se fingen reales.

Todo (código, identificadores, mensajes, documentación) está en español.

## Forma de trabajo acordada con el grupo

- Se avanza por etapas; al terminar una se presentan resultados y se espera aprobación antes de la siguiente.
- Antes de crear recursos GCP con costo relevante (Cloud SQL, balanceador, Cloud Armor, NAT) se informa el
  costo estimado y se pide aprobación. Presupuesto total ≈ USD 150 en créditos.
- No afirmar que algo funciona sin haberlo probado; no inventar URLs, costos ni resultados.
- Los commits **no llevan** línea `Co-Authored-By` ni atribución a Claude.
- Las decisiones técnicas se registran en `docs/06-decisiones.md` (D-01 a D-14). El informe final está en
  `docs/00-informe-final.md` (con capturas en `docs/img/`) y los documentos ficticios para la demo en `docs/demo/`.

## Comandos

API (`app/api`, Python 3.12+):

```powershell
cd app/api
pip install -e ".[dev]"
pytest                                             # todas las pruebas (SQLite en memoria)
pytest tests/test_flujo.py::test_alerta_simulada_deriva_en_silencio   # una prueba
$env:TEST_DATABASE_URL="postgresql+psycopg://tramites:tramites-local@localhost:5432/tramites"; pytest  # contra Postgres
python -m app.cli migrate                          # aplica migraciones (usa DATABASE_URL o DB_*)
python -m app.cli bootstrap-admin --email x@y.cl   # promueve el primer administrador
```

Frontend (`app/web`, React 19 + Vite 8 + TypeScript 7):

```powershell
cd app/web
npm run dev     # http://localhost:5173, lee public/config.json (authMode dev, API en :8080)
npm run build   # tsc -b + vite build; es la única verificación de tipos (no hay pruebas de frontend)
```

Entorno local completo (Postgres 16 + migración + API en :8080 + portal nginx en :8081):

```powershell
docker compose up --build
docker compose exec api python -m app.cli bootstrap-admin --email admin@ficticio.cl
```

En local la autenticación usa `AUTH_MODE=dev` con tokens `Authorization: Bearer dev|<uid>|<email>`.
No hay linter configurado todavía.

## Arquitectura de la API

FastAPI + SQLAlchemy 2 + Alembic. Rutas bajo `/api/v1`, documentación en `/api/docs`.

- **Autenticación vs. autorización** (`seguridad.py`): Identity Platform (firebase-admin) solo prueba la
  identidad. El rol vive en `usuarios.rol` y se consulta en cada petición; todo usuario nuevo se crea como
  `ciudadano` en su primer acceso. Los roles privilegiados solo cambian vía `PATCH /admin/usuarios/{id}` o el
  comando `bootstrap-admin`. Dependencias: `solo_ciudadano`, `solo_funcionario`, `solo_admin`, `usuario_actual`.
- **Separación estricta de roles**: el administrador no gestiona solicitudes y el funcionario no administra
  usuarios. Un recurso ajeno responde **404, no 403**. Los esquemas de entrada usan `extra="forbid"`, así que
  un campo inesperado (`rol`, `estado`) devuelve 422.
- **Máquina de estados** (`estados.py`): las transiciones permitidas se definen por actor (ciudadano, sistema,
  funcionario) y se validan en el servidor (409 si no corresponde). `PREAPROBADA` se muestra al ciudadano como
  `EN_REVISION` (`estado_publico`), para que no pueda deducir si hubo una alerta. Las salidas del ciudadano y
  del funcionario se construyen por separado en `serializar.py`; los resultados de validación y el historial
  completo solo se exponen en el backoffice.
- **Validación automática** (`servicios/solicitudes.py::validar`): se ejecuta de forma síncrona al enviar. Una
  `ALERTA` lleva a `EN_REVISION` sin motivo visible; un `FALTANTE` lleva a `OBSERVADA` con motivo visible.
  Nunca rechaza automáticamente (regla del Lab 1). Los sistemas externos están en `servicios/simuladores.py`,
  con reglas deterministas según la terminación del número de documento (`000`, `999`, `111`; ver README).
- **Eventos** (`Transiciones` + `servicios/eventos.py`): cada cambio de estado agrega una fila en
  `historial_estados` y acumula un evento que se publica en Pub/Sub **después** del commit. No hay outbox (D-09).
- **Documentos** (`servicios/almacenamiento.py`): el backend es GCS o una carpeta local (`STORAGE_MODE`). El
  tipo se detecta por la firma binaria, no por la extensión; los objetos se nombran
  `solicitudes/{uuid}/{uuid}`. Las descargas pasan siempre por la API (sin URLs firmadas) y las de funcionarios
  se auditan.
- **Configuración** (`config.py`): todo se lee de variables de entorno. `validar_seguridad()` impide arrancar con
  `AUTH_MODE=dev` o `ENTORNO=local` dentro de Cloud Run (`K_SERVICE` / `CLOUD_RUN_JOB`).
- **Modelos portables**: los enums se guardan como texto con CHECK, y los tipos JSON/BIGINT tienen variantes
  para que las mismas pruebas corran en SQLite y en Postgres. La migración `0001` crea el esquema desde los
  modelos (D-08); las siguientes deben usar operaciones Alembic explícitas. Las migraciones corren como Cloud
  Run Job, nunca al arrancar la API.
- El pool de conexiones es de 3 + 2 porque `db-f1-micro` admite solo 25 conexiones.
- **Lectura con Gemini** (`servicios/lectura_documentos.py`, D-13): regla `LECTURA_DOCUMENTO` que compara el número
  del documento de identidad con el formulario usando Vertex AI (endpoint `global`, porque Gemini no está en
  Santiago). Se activa con `GEMINI_MODELO` (vacío por defecto, así las pruebas y el entorno local no llaman a
  Vertex AI). Si no confirma el número, o Gemini falla, es una `ALERTA`: va a revisión humana, nunca rechaza.
- **Certificado PDF** (`servicios/certificados.py`): reportlab, generado al vuelo; usa la fuente Alfa Slab One
  (`app/fuentes/`, licencia OFL, incluida como package-data) para el logo DPI.

## Arquitectura del frontend

- **Configuración en tiempo de ejecución**: `src/lib/config.ts` carga `/config.json` antes de montar React. En
  desarrollo es `public/config.json`; en el contenedor lo genera `nginx.conf.template` desde variables de
  entorno (`API_URL`, `AUTH_MODE`, `FIREBASE_*`), y el mismo template arma el CSP con `API_URL`. Así la misma
  imagen sirve para cualquier ambiente. En nginx todas las cabeceras van a nivel de `server`, porque un
  `add_header` dentro de un `location` anula las heredadas.
- **Sesión** (`src/lib/auth.tsx`): en modo `dev` guarda un token `dev|email|email` en sessionStorage; en modo
  `firebase` usa Identity Platform, cargando el SDK solo cuando se necesita. El rol siempre se obtiene de
  `GET /me`. `Protegida` en `componentes/Layout.tsx` solo controla la navegación (si el rol no corresponde, redirige
  al inicio de ese rol, `INICIO_POR_ROL`); la autorización real es la de la API.
- `src/lib/api.ts` agrega el token y convierte los errores de FastAPI (texto, `{mensaje, campos}` o la lista
  de validación de Pydantic) en un `ErrorApi`. Las descargas protegidas usan `api.descargar` (blob + token).
- `FormSolicitud.tsx` atiende dos rutas (`/solicitudes/nueva?tramite=X` y `/solicitudes/:id/editar`). Al crear
  el borrador cambia de ruta y el componente se vuelve a montar, por eso el paso actual viaja en el estado de
  navegación.
- Los estilos están en un solo archivo, `src/estilos.css`, con variables de color en `:root`.

## Infraestructura

Proyecto GCP `lab3-pdi-vpm`, asociado a la cuenta de facturación de educación, con una alerta de presupuesto
de USD 25 (D-11). El procedimiento paso a paso está en `docs/03-despliegue.md`.

```powershell
cd infra/main
terraform init "-backend-config=bucket=lab3-pdi-vpm-tfstate"
terraform plan "-var-file=../envs/dev.tfvars"    # en PowerShell, -var-file y -out van entre comillas
```

Se desplegó y probó de punta a punta en https://web-636986210007.southamerica-west1.run.app, pero el 25-11-2026, tras la
presentación, se destruyó todo (`infra/main` e `infra/bootstrap`) para no consumir créditos: hoy no hay nada
desplegado. Para recrearlo, seguir `docs/03-despliegue.md` (bootstrap primero). Para desplegar una versión nueva: `./scripts/deploy.ps1` (Cloud Build → `terraform apply` con `image_tag` = SHA
corto → job `migrate`).

- `infra/bootstrap` (estado local, solo en la PC de quien lo aplicó): bucket del estado, bucket de build,
  Artifact Registry y `sa-build`. `infra/main` (estado en GCS): todo lo demás.
- El proveedor usa `user_project_override`/`billing_project`, porque Identity Toolkit y API Keys exigen un
  proyecto de cuota cuando se usan credenciales de usuario.
- Cloud Run expone dos URLs por servicio. CORS, `WEB_URL`, los dominios de Identity Platform y la API key usan
  la URL **determinista** (`<servicio>-<número de proyecto>.<región>.run.app`), calculada en `run.tf`
  (`local.url_web`/`url_api`). Eso también evita el ciclo portal ↔ API key. Las salidas `url_portal`/`url_api`
  muestran esas URLs.
- Cloud Build usa `cloudbuild.yaml` con `logging: CLOUD_LOGGING_ONLY` (la cuenta `sa-build` no tiene bucket
  de logs), por eso `gcloud builds submit` no muestra los logs en la terminal.
- Cloud SQL es lo único con costo fijo (≈ USD 0,44/día). Se pausa con `-var=sql_activa=NEVER`.
- Diseño acordado (referencia):

- **Cloud Run**: `web` (React + Vite + nginx, configuración inyectada al arrancar el contenedor), `api`
  (Direct VPC egress) y `notificaciones` (ingreso interno, alimentado por un push de Pub/Sub con OIDC).
  Además los Jobs `migrate` y `bootstrap-admin`, que usan la imagen de la api.
- **Cloud SQL** PostgreSQL 16, **`edition = "ENTERPRISE"`** (obligatorio: la edición por defecto Enterprise
  Plus no admite `db-f1-micro`), `db-f1-micro`, solo IP privada vía Private Services Access, TLS obligatorio,
  `deletion_protection = false`.
- Secret Manager con réplica en Santiago (clave de la base de datos), bucket privado con prevención de acceso
  público, una cuenta de servicio por servicio con roles a nivel de recurso, Identity Platform con correo y
  contraseña.
- **Terraform** dividido en `infra/bootstrap` (estado local: bucket de estado, Artifact Registry, cuenta de
  servicio de build) e `infra/main` (backend GCS, imágenes por variable `image_tag` = SHA de git). El
  balanceador y Cloud Armor **no se implementaron**: se evaluaron en T10 y se descartaron por costo
  (≈ USD 26/mes fijos).
- **Estilo del frontend** (ya implementado): inspirado en pdichile.cl (azul `#00234C`, fondo `#EFEFEF`,
  amarillo `#FFD100`, Oswald y Open Sans, botones píldora de 25px, tarjetas de esquinas rectas). La franja amarilla de aviso se
  quitó por decisión del grupo (D-14); el carácter de prototipo queda bajo el logo, en la verificación y en el PDF.
