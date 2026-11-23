"""Autenticación (Identity Platform) y autorización por rol (base de datos).

El token solo prueba QUIÉN es el usuario. QUÉ puede hacer lo decide `usuarios.rol`.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.modelos import Rol, Usuario

log = logging.getLogger(__name__)


@dataclass
class Identidad:
    uid: str
    email: str
    nombre: str | None


@lru_cache
def _firebase_app():
    import firebase_admin

    return firebase_admin.initialize_app(options={"projectId": get_settings().gcp_project})


def verificar_token(token: str, check_revoked: bool = False) -> Identidad:
    s = get_settings()
    if s.auth_mode == "dev":
        # Formato: dev|<uid>|<email>. Solo existe en local (ver Settings.validar_seguridad).
        partes = token.split("|")
        if len(partes) != 3 or partes[0] != "dev" or "@" not in partes[2]:
            raise ValueError("token dev inválido")
        return Identidad(uid=partes[1], email=partes[2].lower(), nombre=None)

    from firebase_admin import auth

    claims = auth.verify_id_token(token, app=_firebase_app(), check_revoked=check_revoked)
    email = claims.get("email")
    if not email:
        raise ValueError("el token no contiene email")
    return Identidad(uid=claims["uid"], email=email.lower(), nombre=claims.get("name"))


def _token_de(request: Request) -> str:
    cabecera = request.headers.get("Authorization", "")
    tipo, _, token = cabecera.partition(" ")
    if tipo.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta el token de acceso",
                            headers={"WWW-Authenticate": "Bearer"})
    return token


def obtener_o_crear_usuario(db: Session, ident: Identidad) -> Usuario:
    """Primer acceso: crea el usuario SIEMPRE como ciudadano. Nunca se lee un rol del cliente."""
    usuario = db.scalar(select(Usuario).where(Usuario.firebase_uid == ident.uid))
    if usuario:
        return usuario
    usuario = Usuario(firebase_uid=ident.uid, email=ident.email, nombre=ident.nombre,
                      rol=Rol.CIUDADANO)
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # Carrera entre dos peticiones simultáneas, o email ya asociado a otra cuenta.
        db.rollback()
        usuario = db.scalar(select(Usuario).where(Usuario.firebase_uid == ident.uid))
        if usuario is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "El email ya está asociado a otra cuenta")
    return usuario


def _usuario_actual(request: Request, db: Session, check_revoked: bool) -> Usuario:
    try:
        ident = verificar_token(_token_de(request), check_revoked=check_revoked)
    except HTTPException:
        raise
    except Exception as exc:  # firma, expiración, revocación, audiencia...
        log.info("token rechazado: %s", type(exc).__name__)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado",
                            headers={"WWW-Authenticate": "Bearer"})
    usuario = obtener_o_crear_usuario(db, ident)
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta desactivada")
    return usuario


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    return _usuario_actual(request, db, check_revoked=False)


def requiere(*roles: Rol, check_revoked: bool = False):
    """Dependencia de FastAPI: exige que el usuario tenga uno de los roles indicados."""

    def dependencia(request: Request, db: Session = Depends(get_db)) -> Usuario:
        usuario = _usuario_actual(request, db, check_revoked=check_revoked)
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permisos para esta operación")
        return usuario

    return dependencia


solo_ciudadano = requiere(Rol.CIUDADANO)
solo_funcionario = requiere(Rol.FUNCIONARIO)
solo_admin = requiere(Rol.ADMINISTRADOR, check_revoked=True)
