"""Endpoints del funcionario: bandeja, detalle y cambios de estado según la matriz."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import estados
from app.db import get_db
from app.esquemas import PaginaSolicitudes, SolicitudBackofficeOut, TransicionIn
from app.modelos import Estado, Solicitud, Tramite, Usuario
from app.seguridad import solo_funcionario
from app.serializar import detalle_backoffice, resumen_backoffice
from app.servicios import eventos
from app.servicios import solicitudes as negocio

router = APIRouter(prefix="/backoffice", tags=["backoffice"])


def _obtener(db: Session, solicitud_id: uuid.UUID) -> Solicitud:
    sol = db.get(Solicitud, solicitud_id)
    if not sol or sol.estado == Estado.BORRADOR:  # los borradores son privados del ciudadano
        raise HTTPException(404, "Solicitud no encontrada")
    return sol


def _detalle(db: Session, sol: Solicitud) -> SolicitudBackofficeOut:
    ids = {sol.asignado_a, *(h.actor_id for h in sol.historial)} - {None}
    emails = dict(db.execute(select(Usuario.id, Usuario.email).where(Usuario.id.in_(ids))).all()) if ids else {}
    return detalle_backoffice(sol, emails)


@router.get("/solicitudes", response_model=PaginaSolicitudes)
def bandeja(estado: Estado | None = None, tramite: str | None = None,
            q: str | None = Query(default=None, max_length=60),
            pagina: int = Query(default=1, ge=1), tamano: int = Query(default=20, ge=1, le=50),
            db: Session = Depends(get_db), _: Usuario = Depends(solo_funcionario)):
    filtro = select(Solicitud).where(Solicitud.estado != Estado.BORRADOR)
    if estado:
        filtro = filtro.where(Solicitud.estado == estado)
    if tramite:
        filtro = filtro.join(Tramite).where(Tramite.codigo == tramite)
    if q:
        patron = f"%{q}%"
        filtro = filtro.where(or_(Solicitud.folio.ilike(patron), Solicitud.numero_documento.ilike(patron),
                                  Solicitud.apellidos.ilike(patron)))
    total = db.scalar(select(func.count()).select_from(filtro.subquery()))
    filas = db.scalars(filtro.order_by(Solicitud.enviado_en.desc())
                       .offset((pagina - 1) * tamano).limit(tamano)).all()
    return PaginaSolicitudes(items=[resumen_backoffice(s) for s in filas], total=total,
                             pagina=pagina, tamano=tamano)


@router.get("/resumen")
def resumen(db: Session = Depends(get_db), _: Usuario = Depends(solo_funcionario)):
    filas = db.execute(select(Solicitud.estado, func.count()).where(Solicitud.estado != Estado.BORRADOR)
                       .group_by(Solicitud.estado)).all()
    return {e.value: 0 for e in Estado if e != Estado.BORRADOR} | {e.value: n for e, n in filas}


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudBackofficeOut)
def detalle(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
            _: Usuario = Depends(solo_funcionario)):
    return _detalle(db, _obtener(db, solicitud_id))


@router.post("/solicitudes/{solicitud_id}/asignar", response_model=SolicitudBackofficeOut)
def asignar(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
            funcionario: Usuario = Depends(solo_funcionario)):
    sol = _obtener(db, solicitud_id)
    sol.asignado_a = funcionario.id
    db.commit()
    return _detalle(db, sol)


@router.post("/solicitudes/{solicitud_id}/transiciones", response_model=SolicitudBackofficeOut)
def transicionar(solicitud_id: uuid.UUID, datos: TransicionIn, db: Session = Depends(get_db),
                 funcionario: Usuario = Depends(solo_funcionario)):
    sol = _obtener(db, solicitud_id)
    nuevo = datos.estado_nuevo
    if not estados.permitida(estados.TRANSICIONES_FUNCIONARIO, sol.estado, nuevo):
        raise HTTPException(409, f"Transición no permitida: {sol.estado.value} → {nuevo.value}")
    if nuevo in estados.REQUIERE_COMENTARIO and not datos.comentario:
        raise HTTPException(422, "Debe indicar un comentario para observar o rechazar")
    # Pasar a PREAPROBADA es interno: el ciudadano sigue viendo "En revisión".
    visible = datos.visible_ciudadano and nuevo != Estado.PREAPROBADA
    if nuevo == Estado.OBSERVADA:
        visible = True  # el ciudadano necesita saber qué corregir
    if sol.asignado_a is None:
        sol.asignado_a = funcionario.id
    t = negocio.Transiciones(db)
    t.aplicar(sol, nuevo, funcionario.id, comentario=datos.comentario, visible=visible)
    if nuevo == Estado.EMITIDA:
        negocio.emitir_certificado(db, sol, funcionario.id)
    db.commit()
    for e in t.eventos:
        eventos.publicar(e)
    db.refresh(sol)
    return _detalle(db, sol)
