from conftest import cabecera


def test_health_y_catalogo(client):
    assert client.get("/api/v1/health").json() == {"estado": "ok"}
    codigos = [t["codigo"] for t in client.get("/api/v1/tramites").json()]
    assert codigos == ["CERT_VIAJES", "VIGENCIA_PD"]
    assert client.get("/api/v1/tramites/NO_EXISTE").status_code == 404


def test_sin_token_401(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/solicitudes").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_primer_acceso_crea_ciudadano(client):
    r = client.get("/api/v1/me", headers=cabecera("nuevo", "Nuevo@Ficticio.cl"))
    assert r.status_code == 200
    assert r.json()["rol"] == "ciudadano"
    assert r.json()["email"] == "nuevo@ficticio.cl"


def test_no_se_puede_inyectar_rol_al_crear_solicitud(client, ciudadano):
    r = client.post("/api/v1/solicitudes", headers=ciudadano,
                    json={"tramite_codigo": "CERT_VIAJES", "rol": "administrador"})
    assert r.status_code == 422  # extra='forbid'
    r = client.post("/api/v1/solicitudes", headers=ciudadano,
                    json={"tramite_codigo": "CERT_VIAJES", "estado": "EMITIDA"})
    assert r.status_code == 422
    assert client.get("/api/v1/me", headers=ciudadano).json()["rol"] == "ciudadano"


def test_verificar_codigo_inexistente(client):
    assert client.get("/api/v1/certificados/verificar/NOEXISTE").json() == {
        "valido": False, "folio": None, "tramite": None, "titular": None, "emitido_en": None}
