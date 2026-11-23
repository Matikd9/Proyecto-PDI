"""Autorización: cada rol accede solo a lo suyo."""
from conftest import crear_y_enviar, rut


def test_ciudadano_no_ve_solicitudes_ajenas(client, ciudadano, otro_ciudadano):
    sol = crear_y_enviar(client, ciudadano, rut("12345678"))
    sid, doc_id = sol["id"], sol["documentos"][0]["id"]
    # 404 (no 403) para no revelar que existe.
    assert client.get(f"/api/v1/solicitudes/{sid}", headers=otro_ciudadano).status_code == 404
    assert client.get(f"/api/v1/solicitudes/{sid}/historial", headers=otro_ciudadano).status_code == 404
    assert client.get(f"/api/v1/documentos/{doc_id}/contenido", headers=otro_ciudadano).status_code == 404
    assert client.get("/api/v1/solicitudes", headers=otro_ciudadano).json() == []


def test_ciudadano_sin_acceso_a_backoffice_ni_admin(client, ciudadano):
    assert client.get("/api/v1/backoffice/solicitudes", headers=ciudadano).status_code == 403
    assert client.get("/api/v1/admin/usuarios", headers=ciudadano).status_code == 403


def test_funcionario_sin_acceso_a_admin_ni_a_crear(client, funcionario):
    assert client.get("/api/v1/admin/usuarios", headers=funcionario).status_code == 403
    assert client.post("/api/v1/solicitudes", headers=funcionario,
                       json={"tramite_codigo": "CERT_VIAJES"}).status_code == 403


def test_admin_sin_acceso_a_solicitudes(client, admin, ciudadano):
    doc = crear_y_enviar(client, ciudadano, rut("12345678"))["documentos"][0]["id"]
    assert client.get("/api/v1/backoffice/solicitudes", headers=admin).status_code == 403
    assert client.get(f"/api/v1/documentos/{doc}/contenido", headers=admin).status_code == 404


def test_funcionario_no_ve_borradores(client, ciudadano, funcionario):
    sid = client.post("/api/v1/solicitudes", headers=ciudadano,
                      json={"tramite_codigo": "CERT_VIAJES"}).json()["id"]
    assert client.get(f"/api/v1/backoffice/solicitudes/{sid}", headers=funcionario).status_code == 404
    assert client.get("/api/v1/backoffice/solicitudes", headers=funcionario).json()["total"] == 0


def test_transicion_no_permitida_409(client, ciudadano, funcionario):
    sid = crear_y_enviar(client, ciudadano, rut("11222000"))["id"]  # EN_REVISION
    r = client.post(f"/api/v1/backoffice/solicitudes/{sid}/transiciones", headers=funcionario,
                    json={"estado_nuevo": "EMITIDA"})
    assert r.status_code == 409  # debe pasar antes por PREAPROBADA


def test_rechazo_exige_comentario(client, ciudadano, funcionario):
    sid = crear_y_enviar(client, ciudadano, rut("11222000"))["id"]
    url = f"/api/v1/backoffice/solicitudes/{sid}/transiciones"
    assert client.post(url, headers=funcionario, json={"estado_nuevo": "RECHAZADA"}).status_code == 422
    r = client.post(url, headers=funcionario,
                    json={"estado_nuevo": "RECHAZADA", "comentario": "Documento adulterado (ficticio)"})
    assert r.status_code == 200
    assert client.get(f"/api/v1/solicitudes/{sid}", headers=ciudadano).json()["estado"] == "RECHAZADA"


def test_funcionario_descarga_documento_y_queda_auditado(client, ciudadano, funcionario, admin):
    doc = crear_y_enviar(client, ciudadano, rut("12345678"))["documentos"][0]["id"]
    r = client.get(f"/api/v1/documentos/{doc}/contenido", headers=funcionario)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert r.headers["content-disposition"].startswith("attachment")
    acciones = [a["accion"] for a in client.get("/api/v1/admin/auditoria", headers=admin).json()]
    assert "DOCUMENTO_DESCARGADO" in acciones


def test_bandeja_filtra_y_resume(client, ciudadano, funcionario):
    crear_y_enviar(client, ciudadano, rut("12345678"))
    crear_y_enviar(client, ciudadano, rut("11222000"))
    pagina = client.get("/api/v1/backoffice/solicitudes?estado=EN_REVISION", headers=funcionario).json()
    assert pagina["total"] == 1
    resumen = client.get("/api/v1/backoffice/resumen", headers=funcionario).json()
    assert resumen["EN_REVISION"] == 1 and resumen["PREAPROBADA"] == 1
