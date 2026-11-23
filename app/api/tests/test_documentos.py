"""Validación de archivos: tipo real, tamaño, cantidad, nombres y estado."""
from pathlib import Path

from conftest import PDF, PNG, crear_y_enviar, rut

from app.config import get_settings


def _borrador(client, h) -> str:
    return client.post("/api/v1/solicitudes", headers=h, json={"tramite_codigo": "CERT_VIAJES"}).json()["id"]


def _subir(client, h, sid, contenido, nombre="doc.pdf", tipo="identidad", ctype="application/pdf"):
    return client.post(f"/api/v1/solicitudes/{sid}/documentos", headers=h,
                       data={"tipo": tipo}, files={"archivo": (nombre, contenido, ctype)})


def test_rechaza_ejecutable_disfrazado_de_pdf(client, ciudadano):
    sid = _borrador(client, ciudadano)
    r = _subir(client, ciudadano, sid, b"MZ\x90\x00 ejecutable", nombre="cv.pdf")
    assert r.status_code == 415


def test_tipo_se_decide_por_contenido(client, ciudadano):
    sid = _borrador(client, ciudadano)
    r = _subir(client, ciudadano, sid, PNG, nombre="foto.pdf", ctype="application/pdf")
    assert r.status_code == 201
    assert r.json()["content_type"] == "image/png"


def test_rechaza_archivo_grande_y_vacio(client, ciudadano):
    sid = _borrador(client, ciudadano)
    grande = PDF + b"0" * (get_settings().max_archivo_mb * 1024 * 1024)
    assert _subir(client, ciudadano, sid, grande).status_code == 413
    assert _subir(client, ciudadano, sid, b"").status_code == 422


def test_maximo_de_documentos(client, ciudadano):
    sid = _borrador(client, ciudadano)
    for _ in range(get_settings().max_documentos):
        assert _subir(client, ciudadano, sid, PDF).status_code == 201
    assert _subir(client, ciudadano, sid, PDF).status_code == 409


def test_tipo_de_documento_invalido(client, ciudadano):
    sid = _borrador(client, ciudadano)
    assert _subir(client, ciudadano, sid, PDF, tipo="malicioso").status_code == 422


def test_nombre_de_objeto_no_predecible_y_nombre_limpio(client, ciudadano):
    sid = _borrador(client, ciudadano)
    r = _subir(client, ciudadano, sid, PDF, nombre="../../etc/pasaporte<script>.pdf")
    assert r.status_code == 201
    assert r.json()["nombre_original"] == "pasaporte_script_.pdf"
    raiz = Path(get_settings().local_storage_dir)
    guardados = [p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file()]
    assert f"solicitudes/{sid}/{r.json()['id']}" in guardados


def test_no_se_sube_ni_borra_tras_enviar(client, ciudadano):
    sol = crear_y_enviar(client, ciudadano, rut("12345678"))
    sid, doc = sol["id"], sol["documentos"][0]["id"]
    assert _subir(client, ciudadano, sid, PDF).status_code == 409
    assert client.delete(f"/api/v1/solicitudes/{sid}/documentos/{doc}", headers=ciudadano).status_code == 409


def test_dueno_descarga_y_elimina_en_borrador(client, ciudadano):
    sid = _borrador(client, ciudadano)
    doc = _subir(client, ciudadano, sid, PDF, nombre="pasaporte ñandú.pdf").json()
    r = client.get(f"/api/v1/documentos/{doc['id']}/contenido", headers=ciudadano)
    assert r.status_code == 200 and r.content == PDF
    assert "filename*=UTF-8''pasaporte%20%C3%B1and%C3%BA.pdf" in r.headers["content-disposition"]
    assert client.delete(f"/api/v1/solicitudes/{sid}/documentos/{doc['id']}",
                         headers=ciudadano).status_code == 204
    assert client.get(f"/api/v1/documentos/{doc['id']}/contenido", headers=ciudadano).status_code == 404
