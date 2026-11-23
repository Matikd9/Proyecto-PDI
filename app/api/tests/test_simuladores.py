from app.modelos import ResultadoRegla as R
from app.modelos import TipoDocumentoIdentidad as T
from app.servicios import simuladores as s


def test_digito_verificador_rut():
    assert s.rut_valido("12.345.678-5")
    assert s.rut_valido("11111111-1")
    assert not s.rut_valido("12345678-0")
    assert not s.rut_valido("abc")


def test_reglas_por_terminacion():
    assert s.alertas_interpol(T.PASAPORTE, "AB123000").resultado == R.ALERTA
    assert s.alertas_interpol(T.PASAPORTE, "AB123456").resultado == R.OK
    assert s.registro_civil(T.PASAPORTE, "XY999").resultado == R.ALERTA
    assert s.migraciones_viajes(T.PASAPORTE, "P111", None, None).resultado == R.FALTANTE
