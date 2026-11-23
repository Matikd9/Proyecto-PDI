"""Conexión a la base de datos y sesión por petición."""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    url = s.sqlalchemy_url
    if isinstance(url, str) and url.startswith("sqlite"):
        # Solo para pruebas rápidas en memoria.
        from sqlalchemy.pool import StaticPool

        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # db-f1-micro admite 25 conexiones: 2 instancias x (3 + 2) queda holgado.
    return create_engine(url, pool_size=3, max_overflow=2, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
