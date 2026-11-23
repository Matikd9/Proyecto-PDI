"""Entorno de Alembic: usa la misma configuración de conexión que la API."""
from alembic import context

from app.db import Base, get_engine
import app.modelos  # noqa: F401  (registra las tablas en Base.metadata)


def run_migrations_online() -> None:
    with get_engine().connect() as conexion:
        context.configure(connection=conexion, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
