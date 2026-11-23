"""Administración de roles y creación segura del primer administrador."""
import pytest
from conftest import cabecera
from sqlalchemy import select

from app import cli
from app.config import Settings
from app.db import get_sessionmaker
from app.modelos import Usuario


def _id(client, h) -> str:
    return client.get("/api/v1/me", headers=h).json()["id"]


def test_admin_promueve_a_funcionario(client, admin, ciudadano):
    uid = _id(client, ciudadano)
    r = client.patch(f"/api/v1/admin/usuarios/{uid}", headers=admin, json={"rol": "funcionario"})
    assert r.status_code == 200 and r.json()["rol"] == "funcionario"
    # Efecto inmediato: ya puede usar el backoffice.
    assert client.get("/api/v1/backoffice/solicitudes", headers=ciudadano).status_code == 200
    acciones = client.get("/api/v1/admin/auditoria", headers=admin).json()
    assert acciones[0]["accion"] == "ROL_CAMBIADO"


def test_desactivar_usuario_bloquea_acceso(client, admin, ciudadano):
    uid = _id(client, ciudadano)
    client.patch(f"/api/v1/admin/usuarios/{uid}", headers=admin, json={"activo": False})
    assert client.get("/api/v1/me", headers=ciudadano).status_code == 403


def test_admin_no_se_modifica_a_si_mismo(client, admin):
    uid = _id(client, admin)
    assert client.patch(f"/api/v1/admin/usuarios/{uid}", headers=admin,
                        json={"rol": "ciudadano"}).status_code == 409


def test_siempre_queda_un_admin(client, admin):
    otro = cabecera("adm2")
    client.get("/api/v1/me", headers=otro)
    oid = _id(client, otro)
    client.patch(f"/api/v1/admin/usuarios/{oid}", headers=admin, json={"rol": "administrador"})
    # Hay 2 admins: se puede degradar al otro.
    assert client.patch(f"/api/v1/admin/usuarios/{oid}", headers=admin,
                        json={"rol": "ciudadano"}).status_code == 200


def test_campos_extra_rechazados(client, admin, ciudadano):
    uid = _id(client, ciudadano)
    assert client.patch(f"/api/v1/admin/usuarios/{uid}", headers=admin,
                        json={"email": "x@x.cl"}).status_code == 422


def test_bootstrap_admin_por_cli(client):
    h = cabecera("jefa", "jefa@ficticio.cl")
    client.get("/api/v1/me", headers=h)
    assert cli.main(["bootstrap-admin", "--email", "JEFA@ficticio.cl"]) == 0
    assert client.get("/api/v1/me", headers=h).json()["rol"] == "administrador"
    assert cli.main(["bootstrap-admin", "--email", "nadie@ficticio.cl"]) == 1
    with get_sessionmaker()() as db:
        assert db.scalar(select(Usuario).where(Usuario.email == "nadie@ficticio.cl")) is None


def test_modo_dev_prohibido_en_cloud_run(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "api")
    with pytest.raises(RuntimeError):
        Settings(auth_mode="dev", entorno="dev").validar_seguridad()
    with pytest.raises(RuntimeError):
        Settings(auth_mode="firebase", entorno="local").validar_seguridad()
    Settings(auth_mode="firebase", entorno="dev").validar_seguridad()  # configuración válida
