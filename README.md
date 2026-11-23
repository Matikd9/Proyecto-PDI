# Trámites Migratorios · Prototipo — Laboratorio 3 (Grupo VPM, UAI)

> **Prueba de concepto académica.** No es un servicio oficial de la Policía de Investigaciones de Chile.
> Usa solo datos ficticios.

Integrantes: Vicente Vásquez · Matías Medina · Pascal Jorquera — Profesor: Nicolás Riderelli.

Plataforma para solicitar, validar y emitir el **Certificado de Viajes** y el **Certificado de Vigencia
de Permanencia Definitiva**, desplegada en Google Cloud (`southamerica-west1`) mediante Terraform.

## Estado del desarrollo

| Componente | Estado |
|---|---|
| API (FastAPI) | ✅ Implementada · 42 pruebas automáticas pasan (SQLite y PostgreSQL 16) |
| Frontend (React) | ✅ Implementado · flujo completo probado en navegador contra la API local |
| Autenticación real (Identity Platform) | ✅ Registro, login, roles y revocación probados contra GCP (ver `docs/04-pruebas.md`) |
| Documentos en Cloud Storage | ✅ Bucket privado probado (subida, descarga, no sobrescritura, acceso anónimo bloqueado) |
| Infraestructura (Terraform) | 🟡 Bootstrap y base aplicados en `lab3-pdi-vpm` (ver `docs/03-despliegue.md`); faltan red, Cloud SQL y Cloud Run |
| Despliegue en GCP | ⏳ Pendiente |

## Estructura

```
app/api/            API de Trámites (FastAPI + SQLAlchemy + Alembic)
app/web/            Portal web (React + Vite, servido por nginx)
app/notificaciones/ Servicio de notificaciones (Pub/Sub) — pendiente
infra/              Terraform: bootstrap/ (estado local) y main/ (estado en GCS)
docs/               Documentación y registro de decisiones
```

## Ejecutar la API en local

Requisitos: Python 3.12+ (o Docker).

```powershell
cd app/api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest                      # pruebas automáticas (SQLite en memoria)
```

Entorno completo con PostgreSQL 16 real (requiere Docker Desktop encendido), desde la raíz del repositorio:

```powershell
docker compose up --build   # portal http://localhost:8081 · API http://localhost:8080/api/docs
```

Frontend en modo desarrollo (recarga en caliente, usa la API de `docker compose` en el puerto 8080):

```powershell
cd app/web
npm install
npm run dev                 # http://localhost:5173
```

Primer administrador en local (la cuenta debe haber ingresado antes al portal):

```powershell
docker compose exec api python -m app.cli bootstrap-admin --email admin@ficticio.cl
```

En modo local la autenticación usa tokens de desarrollo (`Authorization: Bearer dev|<uid>|<email>`).
Ese modo **no puede activarse en Cloud Run**: la API se niega a arrancar (ver `docs/06-decisiones.md`, D-10).

## Datos de prueba de la validación simulada

Las consultas a Registro Civil, Migraciones, Sistema Central PDI e Interpol están **simuladas**
(`app/api/src/app/servicios/simuladores.py`). El resultado depende de cómo termina el número de documento
(sin dígito verificador en el caso del RUT):

| RUT ficticio | Resultado esperado |
|---|---|
| `12345678-5` | Validación correcta → pasa a revisión del funcionario |
| `11222000-3` | Alerta simulada (Interpol) → "En revisión", sin informar el motivo |
| `15999999-8` | Identidad no coincide (Registro Civil simulado) → "En revisión" |
| `44555111-2` | Sin registros de viaje → "Observada", pide adjuntar un respaldo de viaje |
| `12345678-0` | RUT inválido (dígito verificador) → "Observada" |
