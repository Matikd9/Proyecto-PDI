"""Configuración de pruebas.

Por defecto usan SQLite en memoria. Para probar contra PostgreSQL real:
    TEST_DATABASE_URL=postgresql+psycopg://tramites:tramites@localhost:5432/tramites pytest
"""
import os
import tempfile

os.environ.update({
    "ENTORNO": "local",
    "AUTH_MODE": "dev",
    "STORAGE_MODE": "local",
    "LOCAL_STORAGE_DIR": tempfile.mkdtemp(prefix="docs-pruebas-"),
    "EVENTS_MODE": "log",
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"),
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.catalogo import cargar_catalogo  # noqa: E402
from app.db import Base, get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.modelos import Rol, Usuario  # noqa: E402

PDF = b"%PDF-1.4\n% documento ficticio\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def rut(cuerpo: str) -> str:
    """RUT ficticio con dígito verificador correcto."""
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    dv = {11: "0", 10: "K"}.get(11 - suma % 11, str(11 - suma % 11))
    return f"{cuerpo}-{dv}"


@pytest.fixture(autouse=True)
def base_de_datos():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with get_sessionmaker()() as db:
        cargar_catalogo(db)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def cabecera(uid: str, email: str | None = None) -> dict:
    return {"Authorization": f"Bearer dev|{uid}|{email or uid + '@ficticio.cl'}"}


def asignar_rol(uid: str, rol: Rol) -> None:
    with get_sessionmaker()() as db:
        u = db.scalar(select(Usuario).where(Usuario.firebase_uid == uid))
        u.rol = rol
        db.commit()


@pytest.fixture
def ciudadano(client):
    h = cabecera("ciu1")
    assert client.get("/api/v1/me", headers=h).status_code == 200
    return h


@pytest.fixture
def otro_ciudadano(client):
    h = cabecera("ciu2")
    client.get("/api/v1/me", headers=h)
    return h


@pytest.fixture
def funcionario(client):
    h = cabecera("fun1")
    client.get("/api/v1/me", headers=h)
    asignar_rol("fun1", Rol.FUNCIONARIO)
    return h


@pytest.fixture
def admin(client):
    h = cabecera("adm1")
    client.get("/api/v1/me", headers=h)
    asignar_rol("adm1", Rol.ADMINISTRADOR)
    return h


DATOS_VIAJES = {
    "nombres": "Ana María",
    "apellidos": "Pérez Ficticia",
    "tipo_documento": "RUT",
    "nacionalidad": "Peruana",
    "fecha_nacimiento": "1990-05-10",
    "email_contacto": "ana@ficticio.cl",
    "datos_tramite": {"fecha_desde": "2025-01-01", "fecha_hasta": "2025-12-31",
                      "motivo": "Trámite de visa"},
}


def crear_y_enviar(client, h, numero: str, tramite="CERT_VIAJES", documentos=("identidad",)) -> dict:
    datos = {**DATOS_VIAJES, "tramite_codigo": tramite, "numero_documento": numero}
    if tramite == "VIGENCIA_PD":
        datos["datos_tramite"] = {"numero_resolucion": "RES-0001-FICTICIA"}
    r = client.post("/api/v1/solicitudes", json=datos, headers=h)
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    for tipo in documentos:
        r = client.post(f"/api/v1/solicitudes/{sid}/documentos", headers=h,
                        data={"tipo": tipo}, files={"archivo": ("doc.pdf", PDF, "application/pdf")})
        assert r.status_code == 201, r.text
    r = client.post(f"/api/v1/solicitudes/{sid}/enviar", headers=h)
    assert r.status_code == 200, r.text
    return r.json()
