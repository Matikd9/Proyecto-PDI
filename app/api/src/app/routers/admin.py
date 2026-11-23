"""Administración de usuarios y roles. Solo el rol administrador; cada cambio queda auditado."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.esquemas import AuditoriaOut, UsuarioActualizar, UsuarioOut
from app.modelos import Auditoria, Rol, Usuario
from app.seguridad import solo_admin
from app.servicios import auditoria

router = APIRouter(prefix="/admin", tags=["administración"])


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(q: str | None = Query(default=None, max_length=60), rol: Rol | None = None,
                    db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    filtro = select(Usuario)
    if q:
        filtro = filtro.where(or_(Usuario.email.ilike(f"%{q}%"), Usuario.nombre.ilike(f"%{q}%")))
    if rol:
        filtro = filtro.where(Usuario.rol == rol)
    return db.scalars(filtro.order_by(Usuario.creado_en.desc()).limit(100)).all()


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(usuario_id: uuid.UUID, datos: UsuarioActualizar, db: Session = Depends(get_db),
                       admin: Usuario = Depends(solo_admin)):
    u = db.get(Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if u.id == admin.id:
        raise HTTPException(409, "No puede modificar su propio rol o estado")

    quita_admin = u.rol == Rol.ADMINISTRADOR and (
        (datos.rol is not None and datos.rol != Rol.ADMINISTRADOR) or datos.activo is False)
    if quita_admin:
        admins = db.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.rol == Rol.ADMINISTRADOR, Usuario.activo))
        if admins <= 1:
            raise HTTPException(409, "Debe existir al menos un administrador activo")

    if datos.rol is not None and datos.rol != u.rol:
        auditoria.registrar(db, admin.id, "ROL_CAMBIADO", "usuario", u.id,
                            {"email": u.email, "de": u.rol.value, "a": datos.rol.value})
        u.rol = datos.rol
    if datos.activo is not None and datos.activo != u.activo:
        auditoria.registrar(db, admin.id, "USUARIO_ACTIVADO" if datos.activo else "USUARIO_DESACTIVADO",
                            "usuario", u.id, {"email": u.email})
        u.activo = datos.activo
    db.commit()
    return u


@router.get("/auditoria", response_model=list[AuditoriaOut])
def listar_auditoria(limite: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db),
                     _: Usuario = Depends(solo_admin)):
    return db.scalars(select(Auditoria).order_by(Auditoria.id.desc()).limit(limite)).all()
