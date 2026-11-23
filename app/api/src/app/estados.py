"""Máquina de estados de una solicitud. Toda transición se valida aquí, en el servidor."""
from app.modelos import Estado

E = Estado

# Estados desde los que el ciudadano puede editar y subir documentos.
EDITABLES = {E.BORRADOR, E.OBSERVADA}
# Estados que cuentan para el límite de solicitudes activas por persona.
TERMINALES = {E.EMITIDA, E.RECHAZADA}

TRANSICIONES_CIUDADANO = {
    E.BORRADOR: {E.RECIBIDA},
    E.OBSERVADA: {E.RECIBIDA},
}

TRANSICIONES_SISTEMA = {
    E.RECIBIDA: {E.EN_VALIDACION},
    E.EN_VALIDACION: {E.PREAPROBADA, E.EN_REVISION, E.OBSERVADA},
}

TRANSICIONES_FUNCIONARIO = {
    E.EN_REVISION: {E.PREAPROBADA, E.OBSERVADA, E.RECHAZADA},
    E.PREAPROBADA: {E.EMITIDA, E.OBSERVADA, E.RECHAZADA},
}

# Estados en que el funcionario debe dejar un comentario.
REQUIERE_COMENTARIO = {E.OBSERVADA, E.RECHAZADA}

# Texto que ve el ciudadano para cada estado.
DESCRIPCION_CIUDADANO = {
    E.BORRADOR: "Borrador: aún no ha sido enviada.",
    E.RECIBIDA: "Solicitud recibida.",
    E.EN_VALIDACION: "Validación automática en curso.",
    E.OBSERVADA: "Requiere correcciones de su parte.",
    E.EN_REVISION: "En revisión por un funcionario.",
    E.PREAPROBADA: "En revisión por un funcionario.",  # no se adelanta el resultado
    E.EMITIDA: "Certificado emitido.",
    E.RECHAZADA: "Solicitud rechazada.",
}


def estado_publico(estado: Estado) -> Estado:
    """Estado que se informa al ciudadano: PREAPROBADA no se distingue de EN_REVISION,
    así el ciudadano no puede deducir si hubo una alerta (regla del Lab 1)."""
    return E.EN_REVISION if estado == E.PREAPROBADA else estado


def permitida(tabla: dict[Estado, set[Estado]], desde: Estado, hacia: Estado) -> bool:
    return hacia in tabla.get(desde, set())
