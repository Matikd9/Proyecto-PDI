"""Modelo de datos (PostgreSQL 16). Los enums se guardan como texto con CHECK."""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# JSONB en PostgreSQL, JSON genérico en otros motores (pruebas).
Json = JSON().with_variant(JSONB(), "postgresql")
# BIGSERIAL en PostgreSQL; INTEGER en SQLite para que el autoincremento funcione.
BigId = BigInteger().with_variant(Integer(), "sqlite")


def _enum(e: type[enum.Enum], nombre: str) -> Enum:
    return Enum(e, name=nombre, native_enum=False, length=20, validate_strings=True,
                values_callable=lambda x: [m.value for m in x])


class Rol(str, enum.Enum):
    CIUDADANO = "ciudadano"
    FUNCIONARIO = "funcionario"
    ADMINISTRADOR = "administrador"


class Estado(str, enum.Enum):
    BORRADOR = "BORRADOR"
    RECIBIDA = "RECIBIDA"
    EN_VALIDACION = "EN_VALIDACION"
    OBSERVADA = "OBSERVADA"
    EN_REVISION = "EN_REVISION"
    PREAPROBADA = "PREAPROBADA"
    EMITIDA = "EMITIDA"
    RECHAZADA = "RECHAZADA"


class TipoDocumentoIdentidad(str, enum.Enum):
    RUT = "RUT"
    PASAPORTE = "PASAPORTE"


class TipoArchivo(str, enum.Enum):
    IDENTIDAD = "identidad"
    RESPALDO_VIAJE = "respaldo_viaje"
    RESOLUCION_PD = "resolucion_pd"
    OTRO = "otro"


class ResultadoRegla(str, enum.Enum):
    OK = "OK"
    ALERTA = "ALERTA"
    FALTANTE = "FALTANTE"


def _ahora():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(120))
    rol: Mapped[Rol] = mapped_column(_enum(Rol, "rol"), default=Rol.CIUDADANO, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = _ahora()
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Tramite(Base):
    __tablename__ = "tramites"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    documentos_requeridos: Mapped[list] = mapped_column(Json, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Solicitud(Base):
    __tablename__ = "solicitudes"
    __table_args__ = (
        Index("ix_solicitudes_tramite_doc", "tramite_id", "numero_documento"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True, nullable=False)
    tramite_id: Mapped[int] = mapped_column(ForeignKey("tramites.id"), nullable=False)
    estado: Mapped[Estado] = mapped_column(_enum(Estado, "estado"), index=True, nullable=False,
                                           default=Estado.BORRADOR)
    nombres: Mapped[str | None] = mapped_column(String(100))
    apellidos: Mapped[str | None] = mapped_column(String(100))
    tipo_documento: Mapped[TipoDocumentoIdentidad | None] = mapped_column(
        _enum(TipoDocumentoIdentidad, "tipo_documento"))
    numero_documento: Mapped[str | None] = mapped_column(String(20))
    nacionalidad: Mapped[str | None] = mapped_column(String(60))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    email_contacto: Mapped[str | None] = mapped_column(String(254))
    datos_tramite: Mapped[dict] = mapped_column(Json, default=dict, nullable=False)
    ronda_validacion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    asignado_a: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = _ahora()
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tramite: Mapped[Tramite] = relationship(lazy="joined")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    documentos: Mapped[list["Documento"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan", order_by="Documento.creado_en")
    historial: Mapped[list["HistorialEstado"]] = relationship(
        cascade="all, delete-orphan", order_by="HistorialEstado.id")
    validaciones: Mapped[list["ResultadoValidacion"]] = relationship(
        cascade="all, delete-orphan", order_by="ResultadoValidacion.id")
    certificado: Mapped["Certificado | None"] = relationship(uselist=False)


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True, nullable=False)
    tipo: Mapped[TipoArchivo] = mapped_column(_enum(TipoArchivo, "tipo_archivo"), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(120), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    objeto_gcs: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    subido_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = _ahora()

    solicitud: Mapped[Solicitud] = relationship(back_populates="documentos")


class HistorialEstado(Base):
    """Solo se inserta; nunca se modifica."""
    __tablename__ = "historial_estados"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True, nullable=False)
    estado_anterior: Mapped[Estado | None] = mapped_column(_enum(Estado, "estado"))
    estado_nuevo: Mapped[Estado] = mapped_column(_enum(Estado, "estado"), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))  # NULL = sistema
    comentario: Mapped[str | None] = mapped_column(Text)
    visible_ciudadano: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = _ahora()


class ResultadoValidacion(Base):
    """Solo visible para funcionarios."""
    __tablename__ = "resultados_validacion"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True, nullable=False)
    ronda: Mapped[int] = mapped_column(Integer, nullable=False)
    regla: Mapped[str] = mapped_column(String(40), nullable=False)
    resultado: Mapped[ResultadoRegla] = mapped_column(_enum(ResultadoRegla, "resultado"), nullable=False)
    detalle: Mapped[dict] = mapped_column(Json, default=dict, nullable=False)
    creado_en: Mapped[datetime] = _ahora()


class Certificado(Base):
    __tablename__ = "certificados"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitudes.id", ondelete="CASCADE"), unique=True, nullable=False)
    codigo_verificacion: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    emitido_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    emitido_en: Mapped[datetime] = _ahora()
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    recurso_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    recurso_id: Mapped[str] = mapped_column(String(64), nullable=False)
    detalle: Mapped[dict] = mapped_column(Json, default=dict, nullable=False)
    creado_en: Mapped[datetime] = _ahora()
