"""Integración con Cloud Storage real. Se omite salvo que se indique el bucket:

    $env:TEST_GCS_BUCKET="lab3-pdi-vpm-documentos"; pytest tests/test_gcs_integracion.py

Usa las credenciales locales (gcloud auth application-default login).
"""
import os
import uuid

import pytest
from conftest import PDF, crear_y_enviar, rut

from app.servicios import almacenamiento

BUCKET = os.environ.get("TEST_GCS_BUCKET")
pytestmark = pytest.mark.skipif(not BUCKET, reason="definir TEST_GCS_BUCKET para probar contra GCS")


@pytest.fixture
def gcs(monkeypatch):
    almacen = almacenamiento.AlmacenGCS(BUCKET)
    monkeypatch.setattr(almacenamiento, "get_almacen", lambda: almacen)
    return almacen


def test_guardar_leer_no_sobrescribir_eliminar(gcs):
    objeto = almacenamiento.nombre_objeto(uuid.uuid4(), uuid.uuid4())
    gcs.guardar(objeto, PDF, "application/pdf")
    try:
        assert gcs.leer(objeto) == PDF
        assert gcs.bucket.get_blob(objeto).content_type == "application/pdf"
        with pytest.raises(Exception):  # if_generation_match=0: nunca se sobrescribe un documento
            gcs.guardar(objeto, b"%PDF-otro", "application/pdf")
    finally:
        gcs.eliminar(objeto)
    assert gcs.bucket.get_blob(objeto) is None
    gcs.eliminar(objeto)  # eliminar dos veces no falla


def test_flujo_api_con_gcs(client, ciudadano, funcionario, otro_ciudadano, gcs):
    sol = crear_y_enviar(client, ciudadano, rut("12345678"))
    doc = sol["documentos"][0]
    objeto = f"solicitudes/{sol['id']}/{doc['id']}"
    try:
        assert gcs.bucket.get_blob(objeto) is not None  # quedó en el bucket con nombre no predecible
        r = client.get(f"/api/v1/documentos/{doc['id']}/contenido", headers=funcionario)
        assert r.status_code == 200 and r.content == PDF
        assert client.get(f"/api/v1/documentos/{doc['id']}/contenido", headers=otro_ciudadano).status_code == 404
    finally:
        gcs.eliminar(objeto)
