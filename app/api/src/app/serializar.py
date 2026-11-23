"""Conversión de modelos a respuestas, separando lo que ve el ciudadano y el funcionario."""
from app import estados
from app.esquemas import (
    DocumentoOut,
    HistorialCompletoOut,
    HistorialOut,
    SolicitudBackofficeOut,
    SolicitudOut,
    SolicitudResumenOut,
    ValidacionOut,
)
from app.modelos import Estado, Solicitud


def _base(sol: Solicitud, estado: Estado) -> dict:
    return dict(
        id=sol.id, folio=sol.folio, tramite_codigo=sol.tramite.codigo,
        tramite_nombre=sol.tramite.nombre, estado=estado,
        estado_descripcion=estados.DESCRIPCION_CIUDADANO[estado],
        creado_en=sol.creado_en, enviado_en=sol.enviado_en)


def resumen_ciudadano(sol: Solicitud) -> SolicitudResumenOut:
    return SolicitudResumenOut(**_base(sol, estados.estado_publico(sol.estado)))


def resumen_backoffice(sol: Solicitud) -> SolicitudResumenOut:
    return SolicitudResumenOut(**_base(sol, sol.estado))


def _ultima_observacion(sol: Solicitud) -> str | None:
    if sol.estado != Estado.OBSERVADA:
        return None
    for h in reversed(sol.historial):
        if h.estado_nuevo == Estado.OBSERVADA and h.visible_ciudadano:
            return h.comentario
    return None


def _detalle(sol: Solicitud, estado: Estado) -> dict:
    return dict(
        _base(sol, estado),
        nombres=sol.nombres, apellidos=sol.apellidos, tipo_documento=sol.tipo_documento,
        numero_documento=sol.numero_documento, nacionalidad=sol.nacionalidad,
        fecha_nacimiento=sol.fecha_nacimiento, email_contacto=sol.email_contacto,
        datos_tramite=sol.datos_tramite or {},
        documentos=[DocumentoOut.model_validate(d) for d in sol.documentos],
        ultima_observacion=_ultima_observacion(sol),
        editable=sol.estado in estados.EDITABLES,
        certificado_disponible=sol.estado == Estado.EMITIDA and sol.certificado is not None)


def detalle_ciudadano(sol: Solicitud) -> SolicitudOut:
    return SolicitudOut(**_detalle(sol, estados.estado_publico(sol.estado)))


def historial_ciudadano(sol: Solicitud) -> list[HistorialOut]:
    """Solo entradas visibles, con estados públicos y sin repeticiones consecutivas."""
    salida: list[HistorialOut] = []
    for h in sol.historial:
        if not h.visible_ciudadano:
            continue
        nuevo = estados.estado_publico(h.estado_nuevo)
        anterior = estados.estado_publico(h.estado_anterior) if h.estado_anterior else None
        if anterior == nuevo:
            continue
        salida.append(HistorialOut(estado_anterior=anterior, estado_nuevo=nuevo,
                                   comentario=h.comentario, creado_en=h.creado_en))
    return salida


def detalle_backoffice(sol: Solicitud, emails: dict) -> SolicitudBackofficeOut:
    return SolicitudBackofficeOut(
        **_detalle(sol, sol.estado),
        estado_interno=sol.estado,
        solicitante_email=sol.usuario.email,
        asignado_a_email=emails.get(sol.asignado_a),
        validaciones=[ValidacionOut.model_validate(v) for v in sol.validaciones],
        historial=[HistorialCompletoOut(
            estado_anterior=h.estado_anterior, estado_nuevo=h.estado_nuevo, comentario=h.comentario,
            creado_en=h.creado_en, actor_email=emails.get(h.actor_id),
            visible_ciudadano=h.visible_ciudadano) for h in sol.historial])
