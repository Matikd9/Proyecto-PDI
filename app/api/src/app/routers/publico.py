"""Endpoints públicos (sin token) y perfil del usuario autenticado."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.esquemas import TramiteOut, UsuarioOut, VerificacionOut
from app.modelos import Certificado, Solicitud, Tramite, Usuario
from app.seguridad import usuario_actual
from app.servicios.certificados import enmascarar

router = APIRouter()


@router.get("/health", tags=["público"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"estado": "ok"}


@router.get("/tramites", response_model=list[TramiteOut], tags=["público"])
def listar_tramites(db: Session = Depends(get_db)):
    return db.scalars(select(Tramite).where(Tramite.activo).order_by(Tramite.id)).all()


@router.get("/tramites/{codigo}", response_model=TramiteOut, tags=["público"])
def obtener_tramite(codigo: str, db: Session = Depends(get_db)):
    t = db.scalar(select(Tramite).where(Tramite.codigo == codigo, Tramite.activo))
    if not t:
        raise HTTPException(404, "Trámite no encontrado")
    return t


@router.get("/certificados/verificar/{codigo}", response_model=VerificacionOut, tags=["público"])
def verificar_certificado(codigo: str, db: Session = Depends(get_db)):
    cert = db.scalar(select(Certificado).where(Certificado.codigo_verificacion == codigo.upper()))
    if not cert or not cert.vigente:
        return VerificacionOut(valido=False)
    sol = db.get(Solicitud, cert.solicitud_id)
    return VerificacionOut(valido=True, folio=sol.folio, tramite=sol.tramite.nombre,
                           titular=enmascarar(sol.nombres, sol.apellidos), emitido_en=cert.emitido_en)


@router.get("/me", response_model=UsuarioOut, tags=["usuario"])
def me(usuario: Usuario = Depends(usuario_actual)):
    return usuario
