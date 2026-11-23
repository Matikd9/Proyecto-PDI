"""Flujo de punta a punta: ciudadano → validación → funcionario → certificado."""
from conftest import PDF, crear_y_enviar, rut


def test_flujo_completo_hasta_certificado(client, ciudadano, funcionario):
    sol = crear_y_enviar(client, ciudadano, rut("12345678"))
    # PREAPROBADA se muestra al ciudadano como EN_REVISION.
    assert sol["estado"] == "EN_REVISION"
    sid = sol["id"]

    det = client.get(f"/api/v1/backoffice/solicitudes/{sid}", headers=funcionario).json()
    assert det["estado_interno"] == "PREAPROBADA"
    assert {v["regla"] for v in det["validaciones"]} >= {"DOCUMENTOS_OBLIGATORIOS", "MIGRACIONES_SIM"}

    r = client.post(f"/api/v1/backoffice/solicitudes/{sid}/transiciones", headers=funcionario,
                    json={"estado_nuevo": "EMITIDA", "comentario": "Todo en orden"})
    assert r.status_code == 200, r.text
    assert r.json()["asignado_a_email"] == "fun1@ficticio.cl"

    vista = client.get(f"/api/v1/solicitudes/{sid}", headers=ciudadano).json()
    assert vista["estado"] == "EMITIDA" and vista["certificado_disponible"]

    pdf = client.get(f"/api/v1/solicitudes/{sid}/certificado", headers=ciudadano)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    historial = client.get(f"/api/v1/solicitudes/{sid}/historial", headers=ciudadano).json()
    estados_vistos = [h["estado_nuevo"] for h in historial]
    assert estados_vistos == ["BORRADOR", "RECIBIDA", "EN_VALIDACION", "EN_REVISION", "EMITIDA"]
    assert "PREAPROBADA" not in str(historial)


def test_verificacion_publica_del_certificado(client, ciudadano, funcionario):
    sid = crear_y_enviar(client, ciudadano, rut("22333444"))["id"]
    client.post(f"/api/v1/backoffice/solicitudes/{sid}/transiciones", headers=funcionario,
                json={"estado_nuevo": "EMITIDA"})
    from app.db import get_sessionmaker
    from app.modelos import Certificado

    with get_sessionmaker()() as db:
        codigo = db.query(Certificado).one().codigo_verificacion
    v = client.get(f"/api/v1/certificados/verificar/{codigo.lower()}").json()
    assert v["valido"] is True
    assert v["titular"] == "A** M**** P**** F*******"  # enmascarado


def test_alerta_simulada_deriva_en_silencio(client, ciudadano, funcionario):
    sol = crear_y_enviar(client, ciudadano, rut("11222000"))  # cuerpo termina en 000
    assert sol["estado"] == "EN_REVISION"
    assert sol["ultima_observacion"] is None
    historial = client.get(f"/api/v1/solicitudes/{sol['id']}/historial", headers=ciudadano).json()
    assert all("alerta" not in (h["comentario"] or "").lower() for h in historial)

    det = client.get(f"/api/v1/backoffice/solicitudes/{sol['id']}", headers=funcionario).json()
    assert det["estado_interno"] == "EN_REVISION"
    alertas = [v for v in det["validaciones"] if v["resultado"] == "ALERTA"]
    assert alertas and alertas[0]["regla"] == "ALERTAS_INTERPOL_SIM"


def test_observada_corregir_y_reenviar(client, ciudadano):
    # VIGENCIA_PD exige identidad + resolución: falta la resolución.
    sol = crear_y_enviar(client, ciudadano, rut("33444555"), tramite="VIGENCIA_PD",
                         documentos=("identidad",))
    assert sol["estado"] == "OBSERVADA"
    assert "resolucion_pd" in sol["ultima_observacion"]
    assert sol["editable"] is True

    sid = sol["id"]
    r = client.post(f"/api/v1/solicitudes/{sid}/documentos", headers=ciudadano,
                    data={"tipo": "resolucion_pd"}, files={"archivo": ("res.pdf", PDF, "application/pdf")})
    assert r.status_code == 201
    r = client.post(f"/api/v1/solicitudes/{sid}/enviar", headers=ciudadano)
    assert r.json()["estado"] == "EN_REVISION"  # PREAPROBADA, vista pública


def test_sin_viajes_pide_respaldo(client, ciudadano):
    sol = crear_y_enviar(client, ciudadano, rut("44555111"))
    assert sol["estado"] == "OBSERVADA"
    assert "respaldo de viaje" in sol["ultima_observacion"]


def test_rut_invalido_queda_observada(client, ciudadano):
    sol = crear_y_enviar(client, ciudadano, "12345678-0")
    assert sol["estado"] == "OBSERVADA"
    assert "RUT" in sol["ultima_observacion"]


def test_enviar_incompleta_422(client, ciudadano):
    sid = client.post("/api/v1/solicitudes", headers=ciudadano,
                      json={"tramite_codigo": "CERT_VIAJES"}).json()["id"]
    r = client.post(f"/api/v1/solicitudes/{sid}/enviar", headers=ciudadano)
    assert r.status_code == 422
    assert "Nombres" in r.json()["detail"]["campos"]


def test_no_se_edita_ni_reenvia_tras_enviar(client, ciudadano):
    sid = crear_y_enviar(client, ciudadano, rut("55666777"))["id"]
    assert client.patch(f"/api/v1/solicitudes/{sid}", headers=ciudadano,
                        json={"nombres": "Otro"}).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{sid}/enviar", headers=ciudadano).status_code == 409


def test_limite_de_solicitudes_activas(client, ciudadano):
    for _ in range(3):
        assert client.post("/api/v1/solicitudes", headers=ciudadano,
                           json={"tramite_codigo": "CERT_VIAJES"}).status_code == 201
    r = client.post("/api/v1/solicitudes", headers=ciudadano, json={"tramite_codigo": "CERT_VIAJES"})
    assert r.status_code == 429


def test_fechas_de_viaje_invalidas(client, ciudadano):
    r = client.post("/api/v1/solicitudes", headers=ciudadano, json={
        "tramite_codigo": "CERT_VIAJES",
        "datos_tramite": {"fecha_desde": "2025-12-31", "fecha_hasta": "2025-01-01"}})
    assert r.status_code == 422


def test_duplicado_de_otra_cuenta_va_a_revision(client, ciudadano, otro_ciudadano, funcionario):
    numero = rut("66777888")
    crear_y_enviar(client, ciudadano, numero)
    sol = crear_y_enviar(client, otro_ciudadano, numero)
    assert sol["estado"] == "EN_REVISION"
    det = client.get(f"/api/v1/backoffice/solicitudes/{sol['id']}", headers=funcionario).json()
    dup = [v for v in det["validaciones"] if v["regla"] == "DUPLICADOS"][0]
    assert dup["resultado"] == "ALERTA"
