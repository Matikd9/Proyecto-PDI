"""Registro de auditoría: tabla `auditoria` + línea estructurada en Cloud Logging."""
import logging
import uuid

from sqlalchemy.orm import Session

from app.modelos import Auditoria

log = logging.getLogger("auditoria")


def registrar(db: Session, actor_id: uuid.UUID | None, accion: str, recurso_tipo: str,
              recurso_id: object, detalle: dict | None = None) -> None:
    """Agrega el registro a la sesión; se confirma junto con la operación auditada."""
    db.add(Auditoria(actor_id=actor_id, accion=accion, recurso_tipo=recurso_tipo,
                     recurso_id=str(recurso_id), detalle=detalle or {}))
    log.info("auditoria %s", accion, extra={"auditoria": {
        "actor_id": str(actor_id) if actor_id else None, "accion": accion,
        "recurso_tipo": recurso_tipo, "recurso_id": str(recurso_id)}})
