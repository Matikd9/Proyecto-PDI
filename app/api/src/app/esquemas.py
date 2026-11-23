"""Esquemas de entrada y salida (Pydantic). Las entradas usan extra='forbid':
un campo no previsto (por ejemplo `rol` o `estado`) se rechaza con 422."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.modelos import Estado, ResultadoRegla, Rol, TipoArchivo, TipoDocumentoIdentidad


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Públicos ----------
class TramiteOut(Salida):
    codigo: str
    nombre: str
    descripcion: str
    documentos_requeridos: list[str]


class VerificacionOut(BaseModel):
    valido: bool
    folio: str | None = None
    tramite: str | None = None
    titular: str | None = None
    emitido_en: datetime | None = None


# ---------- Usuario ----------
class UsuarioOut(Salida):
    id: uuid.UUID
    email: str
    nombre: str | None
    rol: Rol
    activo: bool


# ---------- Solicitudes (ciudadano) ----------
class DatosViajes(Entrada):
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    motivo: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _rango(self):
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise ValueError("fecha_desde debe ser anterior o igual a fecha_hasta")
        if self.fecha_hasta and self.fecha_hasta > date.today():
            raise ValueError("fecha_hasta no puede estar en el futuro")
        return self


class DatosVigencia(Entrada):
    numero_resolucion: str | None = Field(default=None, max_length=30)


DATOS_POR_TRAMITE = {"CERT_VIAJES": DatosViajes, "VIGENCIA_PD": DatosVigencia}


class SolicitudCampos(Entrada):
    nombres: str | None = Field(default=None, max_length=100)
    apellidos: str | None = Field(default=None, max_length=100)
    tipo_documento: TipoDocumentoIdentidad | None = None
    numero_documento: str | None = Field(default=None, max_length=20, pattern=r"^[0-9A-Za-z.\-]+$")
    nacionalidad: str | None = Field(default=None, max_length=60)
    fecha_nacimiento: date | None = None
    email_contacto: EmailStr | None = None
    datos_tramite: dict | None = None

    @field_validator("numero_documento")
    @classmethod
    def _normalizar(cls, v: str | None) -> str | None:
        return "".join(c for c in v.upper() if c.isalnum()) if v else v

    @field_validator("fecha_nacimiento")
    @classmethod
    def _pasado(cls, v: date | None) -> date | None:
        if v and v >= date.today():
            raise ValueError("fecha_nacimiento debe estar en el pasado")
        return v


class SolicitudCrear(SolicitudCampos):
    tramite_codigo: str = Field(max_length=30)


class SolicitudActualizar(SolicitudCampos):
    pass


class DocumentoOut(Salida):
    id: uuid.UUID
    tipo: TipoArchivo
    nombre_original: str
    content_type: str
    tamano_bytes: int
    creado_en: datetime


class HistorialOut(Salida):
    estado_anterior: Estado | None
    estado_nuevo: Estado
    comentario: str | None
    creado_en: datetime


class SolicitudResumenOut(Salida):
    id: uuid.UUID
    folio: str
    tramite_codigo: str
    tramite_nombre: str
    estado: Estado
    estado_descripcion: str
    creado_en: datetime
    enviado_en: datetime | None


class SolicitudOut(SolicitudResumenOut):
    nombres: str | None
    apellidos: str | None
    tipo_documento: TipoDocumentoIdentidad | None
    numero_documento: str | None
    nacionalidad: str | None
    fecha_nacimiento: date | None
    email_contacto: str | None
    datos_tramite: dict
    documentos: list[DocumentoOut]
    ultima_observacion: str | None
    editable: bool
    certificado_disponible: bool


# ---------- Backoffice ----------
class ValidacionOut(Salida):
    ronda: int
    regla: str
    resultado: ResultadoRegla
    detalle: dict
    creado_en: datetime


class HistorialCompletoOut(HistorialOut):
    actor_email: str | None
    visible_ciudadano: bool


class SolicitudBackofficeOut(SolicitudOut):
    estado_interno: Estado
    solicitante_email: str
    asignado_a_email: str | None
    validaciones: list[ValidacionOut]
    historial: list[HistorialCompletoOut]


class PaginaSolicitudes(BaseModel):
    items: list[SolicitudResumenOut]
    total: int
    pagina: int
    tamano: int


class TransicionIn(Entrada):
    estado_nuevo: Estado
    comentario: str | None = Field(default=None, max_length=1000)
    visible_ciudadano: bool = True


# ---------- Administración ----------
class UsuarioActualizar(Entrada):
    rol: Rol | None = None
    activo: bool | None = None


class AuditoriaOut(Salida):
    id: int
    actor_id: uuid.UUID | None
    accion: str
    recurso_tipo: str
    recurso_id: str
    detalle: dict
    creado_en: datetime
