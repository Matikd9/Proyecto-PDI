"""Esquema inicial + catálogo de trámites.

Ver decisión D-08: la primera migración crea el esquema desde los modelos.
Las siguientes usarán operaciones Alembic explícitas.

Revision ID: 0001
Revises:
"""
from alembic import op
from sqlalchemy.orm import Session

from app.catalogo import cargar_catalogo
from app.db import Base
import app.modelos  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexion = op.get_bind()
    Base.metadata.create_all(bind=conexion)
    cargar_catalogo(Session(bind=conexion))


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
