"""SIMULADORES de sistemas externos. NO se conectan a ningún sistema real.

En la arquitectura del Lab 2 estas consultas pasan por la capa de integración
(adaptadores + Cloud VPN). Aquí se reemplazan por reglas deterministas sobre
números de documento FICTICIOS, para que la demostración sea repetible.
Se evalúa el "cuerpo" del documento (RUT sin dígito verificador, o el pasaporte completo):

| Cuerpo termina en | Sistema simulado           | Resultado                                  |
|-------------------|----------------------------|--------------------------------------------|
| 000               | Sistema Central / Interpol | ALERTA   -> deriva a revisión (en silencio)|
| 999               | Registro Civil             | ALERTA   -> identidad no coincide          |
| 111               | Migraciones (viajes)       | FALTANTE -> sin registros de viaje         |
| otro              | —                          | OK                                         |
"""
from dataclasses import dataclass, field

from app.modelos import ResultadoRegla, TipoDocumentoIdentidad


@dataclass
class Respuesta:
    resultado: ResultadoRegla
    detalle: dict = field(default_factory=dict)


def normalizar(numero: str) -> str:
    return "".join(c for c in numero.upper() if c.isalnum())


def cuerpo(tipo: TipoDocumentoIdentidad, numero: str) -> str:
    n = normalizar(numero)
    return n[:-1] if tipo == TipoDocumentoIdentidad.RUT else n


def rut_valido(rut: str) -> bool:
    """Algoritmo real del dígito verificador (módulo 11). Es cálculo local, no una consulta."""
    rut = normalizar(rut)
    if len(rut) < 2 or not rut[:-1].isdigit():
        return False
    suma, factor = 0, 2
    for d in reversed(rut[:-1]):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    esperado = 11 - suma % 11
    return rut[-1] == {11: "0", 10: "K"}.get(esperado, str(esperado))


def registro_civil(tipo: TipoDocumentoIdentidad, numero: str) -> Respuesta:
    if tipo == TipoDocumentoIdentidad.RUT and not rut_valido(numero):
        return Respuesta(ResultadoRegla.FALTANTE, {
            "motivo": "El RUT ingresado no es válido (dígito verificador).", "visible": True})
    if cuerpo(tipo, numero).endswith("999"):
        return Respuesta(ResultadoRegla.ALERTA, {"motivo": "Identidad no coincide (simulado)"})
    return Respuesta(ResultadoRegla.OK, {"fuente": "simulador_registro_civil"})


def migraciones_viajes(tipo: TipoDocumentoIdentidad, numero: str,
                       fecha_desde: str | None, fecha_hasta: str | None) -> Respuesta:
    if cuerpo(tipo, numero).endswith("111"):
        return Respuesta(ResultadoRegla.FALTANTE, {
            "motivo": "No se encontraron registros de viaje en el período indicado. "
                      "Adjunte un respaldo de viaje (pasaje o timbre de pasaporte).",
            "visible": True})
    return Respuesta(ResultadoRegla.OK, {"fuente": "simulador_migraciones",
                                         "periodo": [fecha_desde, fecha_hasta]})


def alertas_interpol(tipo: TipoDocumentoIdentidad, numero: str) -> Respuesta:
    if cuerpo(tipo, numero).endswith("000"):
        # Nunca se informa al ciudadano ni se rechaza automáticamente (Lab 1, sección 2.2).
        return Respuesta(ResultadoRegla.ALERTA, {"motivo": "Coincidencia en alertas (simulado)"})
    return Respuesta(ResultadoRegla.OK, {"fuente": "simulador_sistema_central"})
