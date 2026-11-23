"""Regla LECTURA_DOCUMENTO con Gemini simulado (las pruebas nunca llaman a Vertex AI)."""
import pytest
from conftest import crear_y_enviar, rut

from app.config import get_settings
from app.servicios import lectura_documentos
from app.servicios.lectura_documentos import Lectura


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_modelo", "modelo-de-prueba")
    respuesta = {}

    def consultar(contenido, mime):
        assert contenido.startswith(b"%PDF") and mime == "application/pdf"
        if isinstance(respuesta.get("r"), Exception):
            raise respuesta["r"]
        return respuesta["r"]

    monkeypatch.setattr(lectura_documentos, "_consultar", consultar)
    return respuesta


def _lectura(client, funcionario, sid):
    det = client.get(f"/api/v1/backoffice/solicitudes/{sid}", headers=funcionario).json()
    return det["estado_interno"], next(v for v in det["validaciones"] if v["regla"] == "LECTURA_DOCUMENTO")


def test_desactivada_por_defecto(client, ciudadano, funcionario):
    sid = crear_y_enviar(client, ciudadano, rut("12345678"))["id"]
    det = client.get(f"/api/v1/backoffice/solicitudes/{sid}", headers=funcionario).json()
    assert "LECTURA_DOCUMENTO" not in {v["regla"] for v in det["validaciones"]}


def test_numero_coincide(client, ciudadano, funcionario, gemini):
    gemini["r"] = Lectura(legible=True, numero_documento="12.345.678-5", nombre_completo="Ana Ficticia")
    sid = crear_y_enviar(client, ciudadano, rut("12345678"))["id"]
    estado, v = _lectura(client, funcionario, sid)
    assert estado == "PREAPROBADA" and v["resultado"] == "OK"


@pytest.mark.parametrize("r", [
    Lectura(legible=True, numero_documento="99.999.999-9"),
    Lectura(legible=False),
    RuntimeError("Vertex AI no responde"),
])
def test_sin_confirmar_va_a_revision_en_silencio(client, ciudadano, funcionario, gemini, r):
    gemini["r"] = r
    sol = crear_y_enviar(client, ciudadano, rut("12345678"))
    assert sol["estado"] == "EN_REVISION" and sol["ultima_observacion"] is None
    estado, v = _lectura(client, funcionario, sol["id"])
    assert estado == "EN_REVISION" and v["resultado"] == "ALERTA" and v["detalle"]["motivo"]
