# Registro de decisiones — Laboratorio 3 (Grupo VPM)

Cada decisión indica el contexto, lo decidido y su impacto. Se actualiza a medida que avanza el proyecto.

## D-01 · Alcance: un solo ambiente DEV
- **Contexto:** el Lab 2 define DEV, QA y PROD como proyectos separados. El presupuesto es de ~USD 150 en créditos.
- **Decisión:** se despliega solo DEV. El código Terraform queda parametrizado por `.tfvars`, de modo que QA y PROD serían otro proyecto con el mismo código.
- **Impacto:** se demuestra el principio "mismo código, distinto tamaño" sin triplicar costos.

## D-02 · Stack
- React + Vite + TypeScript (frontend estático servido por nginx en Cloud Run).
- Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic (API).
- PostgreSQL 16 en Cloud SQL (edición **Enterprise**, `db-f1-micro`).
- Terraform para toda la infraestructura; Cloud Build + Artifact Registry para imágenes.

## D-03 · Cloud SQL Enterprise + db-f1-micro
- **Contexto:** en PostgreSQL 16+ la edición por defecto es Enterprise Plus, que no admite máquinas de núcleo compartido.
- **Decisión:** fijar `edition = "ENTERPRISE"` y `tier = "db-f1-micro"` (USD 0,0147/h en Santiago, verificado nov-2026). Sin SLA: aceptable para una PoC.
- **Impacto:** máximo 25 conexiones → pool de 3+2 por instancia y máximo 2 instancias de Cloud Run.

## D-04 · Los roles viven en la base de datos
- **Contexto:** se exige que los roles privilegiados no puedan asignarse desde el frontend ni por registro público.
- **Decisión:** Identity Platform solo autentica (quién es). El rol está en `usuarios.rol` y la API lo consulta en cada petición. Todo usuario nuevo nace `ciudadano`. El primer administrador se crea con el Cloud Run Job `bootstrap-admin` (protegido por IAM de GCP); los siguientes, solo vía `PATCH /admin/usuarios/{id}`.
- **Impacto:** un cambio o revocación de rol tiene efecto inmediato; no depende de custom claims del token.
- **Revocación de sesiones:** las rutas `/admin/*` comprueban en Identity Platform si el token fue revocado
  (probado: 401 tras revocar). El resto de las rutas no lo hace, para no consultar Identity Platform en cada
  petición; para bloquear a alguien de inmediato en toda la API se usa `activo = false`.

## D-05 · Acceso a recursos ajenos devuelve 404
- Un ciudadano que pide una solicitud o documento ajeno recibe 404 (no 403), para no revelar su existencia. Los identificadores son UUID.

## D-06 · Documentos solo a través de la API
- Bucket privado con prevención de acceso público. No se usan URLs firmadas: la API valida permisos y entrega el archivo. Se valida el tipo por la firma binaria (PDF/PNG/JPEG), tamaño máximo 5 MB, máximo 6 por solicitud, nombres de objeto `solicitudes/{uuid}/{uuid}`.

## D-07 · Validación automática síncrona con simuladores deterministas
- **Contexto:** no hay acceso a Registro Civil, Migraciones, Sistema Central PDI ni Interpol.
- **Decisión:** módulo `simuladores` con reglas deterministas sobre números de documento ficticios (ver `docs/04-pruebas.md`). Una alerta deriva a `EN_REVISION` sin informar el motivo al ciudadano ni rechazar (regla del Lab 1). Cloud Workflows queda fuera de alcance; la orquestación vive en la API.

## D-08 · Migración inicial basada en los modelos
- La migración `0001` crea el esquema a partir de los modelos SQLAlchemy y carga el catálogo de trámites. Las migraciones posteriores usarán operaciones Alembic explícitas. Se ejecuta con el Cloud Run Job `migrate`, nunca al arrancar la API (evita carreras entre instancias).

## D-09 · Eventos sin outbox
- Tras confirmar cada transacción la API publica el evento en Pub/Sub. Si la publicación falla se registra el error, pero la solicitud no se revierte. Un patrón *outbox* sería lo correcto en producción; queda documentado como limitación.

## D-10 · Modo de autenticación de desarrollo
- Para desarrollo y pruebas locales existe `AUTH_MODE=dev` (token `dev|uid|email`). La aplicación **se niega a arrancar** en ese modo (o con `ENTORNO=local`) si detecta que corre en Cloud Run (`K_SERVICE` o `CLOUD_RUN_JOB`), por lo que no puede activarse en la nube por error.

## D-11 · Proyecto GCP y control de gasto
- **Proyecto:** `lab3-pdi-vpm` (sin organización), creado el 23-11-2026 con `gcloud projects create`.
- **Facturación:** asociado a la "Cuenta de facturación para educación" (créditos del curso), no a una cuenta personal.
- **Presupuesto:** alerta de USD 25 filtrada al proyecto, con avisos al 40 % (USD 10), 80 % y 100 %. La alerta
  solo notifica por correo; **no detiene el gasto**. Para cortar costos hay que pausar Cloud SQL o ejecutar
  `terraform destroy`.
- Comandos para reproducir en otra cuenta:
  `gcloud projects create <id>` → `gcloud billing projects link <id> --billing-account=<cuenta>` →
  `gcloud billing budgets create --billing-account=<cuenta> --budget-amount=25USD --filter-projects=projects/<id> --threshold-rule=percent=0.4 --threshold-rule=percent=0.8 --threshold-rule=percent=1.0`.

## D-12 · Infraestructura destruible y recreable
- **Contexto:** la prueba de reproducibilidad (destruir y recrear) mostró tres obstáculos de GCP.
- **Decisiones:**
  - Sufijo aleatorio (`random_id`) en el nombre de la instancia de Cloud SQL y de la API key, porque GCP
    reserva por días o semanas los nombres de esos recursos después de borrarlos.
  - `deletion_policy = "ABANDON"` en la base y el usuario de Cloud SQL: se eliminan con la instancia, y así
    `destroy` funciona aunque la instancia esté pausada.
  - La subred de Direct VPC egress tarda en liberarse: se documenta que hay que reintentar `destroy`.
  - Identity Platform no se puede desactivar: `destroy` solo lo quita del estado (los usuarios registrados
    se conservan). Un bloque `import` en `identidad.tf` adopta la configuración existente al recrear.

## D-13 · Lectura del documento de identidad con Gemini (T10)
- **Contexto:** la arquitectura del Lab 2 incluye Gemini para leer documentos. Es la única integración
  **real** de IA; las demás siguen simuladas.
- **Decisión:** al enviar una solicitud, Gemini 3.1 Flash-Lite (Vertex AI) lee el documento de identidad
  adjunto y extrae el número y el nombre. Si el número coincide con el formulario, la regla
  `LECTURA_DOCUMENTO` queda en OK. Si no coincide, es ilegible o Gemini falla, queda en ALERTA y la solicitud
  va a revisión humana sin motivo visible. **Nunca rechaza ni observa** (regla del Lab 1). Se activa con
  `GEMINI_MODELO` (variable `gemini_modelo` de Terraform); si está vacía, la regla no se ejecuta.
- **Región:** Gemini no está disponible en `southamerica-west1`, así que se usa el endpoint `global`: el
  documento se procesa fuera de Chile. Se acepta porque todos los datos son ficticios; con datos reales
  habría que evaluarlo frente a la Ley 19.628.
- **Riesgos:** un documento podría contener texto que intente manipular al modelo (*prompt injection*). Por
  eso Gemini solo devuelve campos estructurados, la comparación la hace el código y un OK de Gemini no
  salta ninguna otra regla ni la revisión del funcionario. El rol `aiplatform.user` es a nivel de proyecto
  porque no existe un permiso por modelo.
- **Costo:** USD 0,25 por millón de tokens de entrada y USD 0,75 por millón de salida; sin costo fijo.

## D-14 · Marca ficticia "DPI" y botón de ClaveÚnica
- **Marca:** el encabezado muestra "DPI" en amarillo sobre azul, con la tipografía Alfa Slab One (Google
  Fonts). Por decisión del grupo, el nombre se altera a propósito para que se entienda que el diseño está
  pensado para la PDI sin usar su nombre ni su logotipo oficial. El 25-11-2026 el grupo decidió quitar la franja
  amarilla de aviso del encabezado. El carácter de prototipo sigue indicado bajo el logo ("Prototipo ·
  Arquitectura Cloud"), en la verificación pública ("prototipo académico, sin validez legal") y en el
  certificado PDF (marca de agua "DOCUMENTO FICTICIO" y leyenda de que no es oficial).
- **ClaveÚnica:** el botón usa el formato del kit oficial "Botón Oficial de ClaveÚnica" v2.0 (colores,
  Roboto, ícono `cu-blanco.svg`), pero sigue **deshabilitado** y rotulado como simulado: no hay integración
  real con ClaveÚnica.
