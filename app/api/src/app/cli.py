"""Comandos administrativos. En GCP se ejecutan como Cloud Run Jobs, protegidos por IAM:

    python -m app.cli migrate
    python -m app.cli bootstrap-admin --email persona@ejemplo.cl
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db import get_sessionmaker
from app.main import configurar_logs
from app.modelos import Rol, Usuario
from app.servicios import auditoria

log = logging.getLogger("cli")


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    # alembic.ini y migrations/ están en el directorio de trabajo (/srv en el contenedor).
    raiz = Path(os.environ.get("ALEMBIC_DIR", Path.cwd()))
    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "migrations"))
    command.upgrade(cfg, "head")
    log.info("migraciones aplicadas")


def bootstrap_admin(email: str) -> int:
    """Promueve a administrador a una cuenta existente. Requiere que la persona se haya
    registrado antes en el portal (Identity Platform)."""
    email = email.strip().lower()
    db = get_sessionmaker()()
    try:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None and get_settings().auth_mode == "firebase":
            from firebase_admin import auth

            from app.seguridad import _firebase_app

            try:
                fb = auth.get_user_by_email(email, app=_firebase_app())
            except auth.UserNotFoundError:
                log.error("no existe una cuenta registrada con ese email")
                return 1
            usuario = Usuario(firebase_uid=fb.uid, email=email, nombre=fb.display_name)
            db.add(usuario)
            db.flush()
        if usuario is None:
            log.error("no existe un usuario con ese email")
            return 1
        anterior = usuario.rol
        usuario.rol, usuario.activo = Rol.ADMINISTRADOR, True
        auditoria.registrar(db, None, "BOOTSTRAP_ADMIN", "usuario", usuario.id,
                            {"email": email, "de": anterior.value if anterior else None})
        db.commit()
        log.info("usuario promovido a administrador")
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    configurar_logs()
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("migrate")
    p = sub.add_parser("bootstrap-admin")
    p.add_argument("--email", required=True)
    args = parser.parse_args(argv)
    if args.comando == "migrate":
        migrate()
        return 0
    return bootstrap_admin(args.email)


if __name__ == "__main__":
    sys.exit(main())
