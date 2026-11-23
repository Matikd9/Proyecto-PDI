"""Lógica de negocio de las solicitudes: transiciones, validación automática y emisión."""
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import estados
from app.modelos import (
    Certificado,
    Estado,
    HistorialEstado,
    ResultadoRegla,
    ResultadoValidacion,
    Solicitud,
    TipoArchivo,
)
from app.config import get_settings
from app.servicios import lectura_documentos, simuladores

_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para evitar confusiones

CAMPOS_OBLIGATORIOS = {
    "nombres": "Nombres",
    "apellidos": "Apellidos",
    "tipo_documento": "Tipo de documento",
    "numero_documento": "Número de documento",
    "nacionalidad": "Nacionalidad",
    "fecha_nacimiento": "Fecha de nacimiento",
    "email_contacto": "Email de contacto",
}
CAMPOS_TRAMITE = {
    "CERT_VIAJES": {"fecha_desde": "Fecha desde", "fecha_hasta": "Fecha hasta", "motivo": "Motivo"},
    "VIGENCIA_PD": {},
}


def _codigo(n: int) -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(n))


def generar_folio() -> str:
    return f"VPM-{datetime.now(timezone.utc).year}-{_codigo(6)}"


class Transiciones:
    """Acumula eventos para publicarlos solo después del commit."""

    def __init__(self, db: Session):
        self.db = db
        self.eventos: list[dict] = []

    def aplicar(self, sol: Solicitud, nuevo: Estado, actor_id: uuid.UUID | None,
                comentario: str | None = None, visible: bool = True) -> None:
        anterior = sol.estado
        sol.estado = nuevo
        self.db.add(HistorialEstado(solicitud_id=sol.id, estado_anterior=anterior, estado_nuevo=nuevo,
                                    actor_id=actor_id, comentario=comentario,
                                    visible_ciudadano=visible))
        self.eventos.append({
            "tipo": "solicitud.estado_cambiado",
            "solicitud_id": str(sol.id),
            "folio": sol.folio,
            "tramite": sol.tramite.codigo,
            "estado_anterior": anterior.value if anterior else None,
            # Al ciudadano solo se le notifica el estado público.
            "estado_publico": estados.estado_publico(nuevo).value,
            "estado_nuevo": nuevo.value,
            "email_contacto": sol.email_contacto,
            "actor": "sistema" if actor_id is None else str(actor_id),
            "fecha": datetime.now(timezone.utc).isoformat(),
        })


def campos_faltantes(sol: Solicitud) -> list[str]:
    faltan = [et for campo, et in CAMPOS_OBLIGATORIOS.items() if not getattr(sol, campo)]
    datos = sol.datos_tramite or {}
    faltan += [et for campo, et in CAMPOS_TRAMITE.get(sol.tramite.codigo, {}).items()
               if not datos.get(campo)]
    return faltan


def _regla(db: Session, sol: Solicitud, nombre: str, r: simuladores.Respuesta) -> simuladores.Respuesta:
    db.add(ResultadoValidacion(solicitud_id=sol.id, ronda=sol.ronda_validacion, regla=nombre,
                               resultado=r.resultado, detalle=r.detalle))
    return r


def validar(db: Session, sol: Solicitud) -> tuple[Estado, str | None]:
    """Ejecuta las reglas. Una ALERTA deriva a revisión humana sin explicar el motivo;
    un FALTANTE devuelve la solicitud al ciudadano con el motivo; nunca se rechaza aquí."""
    sol.ronda_validacion += 1
    R = ResultadoRegla
    resultados: list[simuladores.Respuesta] = []

    # 1. Documentos obligatorios del trámite.
    tipos = {d.tipo.value for d in sol.documentos}
    faltan = [t for t in sol.tramite.documentos_requeridos if t not in tipos]
    resultados.append(_regla(db, sol, "DOCUMENTOS_OBLIGATORIOS", simuladores.Respuesta(
        R.FALTANTE if faltan else R.OK,
        {"faltan": faltan, "motivo": f"Faltan documentos obligatorios: {', '.join(faltan)}.",
         "visible": True} if faltan else {})))

    # 2. Duplicados (mismo trámite y documento, solicitud activa).
    otras = db.scalars(select(Solicitud).where(
        Solicitud.tramite_id == sol.tramite_id,
        Solicitud.numero_documento == sol.numero_documento,
        Solicitud.id != sol.id,
        Solicitud.estado.not_in([Estado.BORRADOR, *estados.TERMINALES]),
    )).all()
    if any(o.usuario_id == sol.usuario_id for o in otras):
        r = simuladores.Respuesta(R.FALTANTE, {
            "motivo": "Ya tiene otra solicitud activa para este trámite y documento.", "visible": True})
    elif otras:
        # Otra cuenta usa el mismo documento: posible suplantación -> revisión silenciosa.
        r = simuladores.Respuesta(R.ALERTA, {"motivo": "Documento usado por otra cuenta",
                                             "folios": [o.folio for o in otras]})
    else:
        r = simuladores.Respuesta(R.OK)
    resultados.append(_regla(db, sol, "DUPLICADOS", r))

    # 3-5. Sistemas externos SIMULADOS.
    tipo, numero = sol.tipo_documento, sol.numero_documento
    resultados.append(_regla(db, sol, "REGISTRO_CIVIL_SIM", simuladores.registro_civil(tipo, numero)))
    if sol.tramite.codigo == "CERT_VIAJES":
        d = sol.datos_tramite or {}
        con_respaldo = TipoArchivo.RESPALDO_VIAJE.value in tipos
        r = simuladores.migraciones_viajes(tipo, numero, d.get("fecha_desde"), d.get("fecha_hasta"))
        if r.resultado == R.FALTANTE and con_respaldo:
            # El ciudadano ya adjuntó un respaldo: lo revisa un funcionario.
            r = simuladores.Respuesta(R.ALERTA, {"motivo": "Sin registros; respaldo adjunto a revisar"})
        resultados.append(_regla(db, sol, "MIGRACIONES_SIM", r))
    resultados.append(_regla(db, sol, "ALERTAS_INTERPOL_SIM", simuladores.alertas_interpol(tipo, numero)))

    # 6. Lectura del documento de identidad con Gemini (opcional, real).
    if get_settings().gemini_modelo:
        resultados.append(_regla(db, sol, "LECTURA_DOCUMENTO", lectura_documentos.leer_identidad(sol)))

    if any(r.resultado == R.ALERTA for r in resultados):
        return Estado.EN_REVISION, None
    visibles = [r.detalle["motivo"] for r in resultados
                if r.resultado == R.FALTANTE and r.detalle.get("visible")]
    if visibles:
        return Estado.OBSERVADA, " ".join(visibles)
    return Estado.PREAPROBADA, None


def enviar(db: Session, sol: Solicitud, actor_id: uuid.UUID) -> Transiciones:
    t = Transiciones(db)
    sol.enviado_en = datetime.now(timezone.utc)
    t.aplicar(sol, Estado.RECIBIDA, actor_id)
    t.aplicar(sol, Estado.EN_VALIDACION, None)
    db.flush()
    resultado, motivo = validar(db, sol)
    t.aplicar(sol, resultado, None, comentario=motivo)
    return t


def emitir_certificado(db: Session, sol: Solicitud, funcionario_id: uuid.UUID) -> Certificado:
    cert = Certificado(solicitud_id=sol.id, codigo_verificacion=_codigo(12), emitido_por=funcionario_id)
    db.add(cert)
    return cert


def activas_del_usuario(db: Session, usuario_id: uuid.UUID, tramite_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Solicitud).where(
        Solicitud.usuario_id == usuario_id, Solicitud.tramite_id == tramite_id,
        Solicitud.estado.not_in(list(estados.TERMINALES)))) or 0
