"""Almacenamiento de documentos: Cloud Storage privado (nube) o carpeta local (desarrollo)."""
import hashlib
import re
import uuid
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

# Firmas binarias ("magic bytes") permitidas. El tipo se decide por el contenido,
# nunca por la extensión ni por el Content-Type que envía el cliente.
FIRMAS = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]

_OBJETO = re.compile(r"^solicitudes/[0-9a-f-]{36}/[0-9a-f-]{36}$")


def detectar_tipo(contenido: bytes) -> str | None:
    for firma, tipo in FIRMAS:
        if contenido.startswith(firma):
            return tipo
    return None


def limpiar_nombre(nombre: str | None) -> str:
    base = (nombre or "documento").replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[^\w.\- ]", "_", base, flags=re.UNICODE).strip(" .") or "documento"
    return base[:120]


def content_disposition(nombre: str) -> str:
    """Cabecera de descarga segura también para nombres con tildes (RFC 6266)."""
    from urllib.parse import quote

    ascii_ = nombre.encode("ascii", "replace").decode().replace("?", "_").replace('"', "_")
    return f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"


def nombre_objeto(solicitud_id: uuid.UUID, documento_id: uuid.UUID) -> str:
    return f"solicitudes/{solicitud_id}/{documento_id}"


def sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


class AlmacenLocal:
    def __init__(self, raiz: str):
        self.raiz = Path(raiz).resolve()

    def _ruta(self, objeto: str) -> Path:
        if not _OBJETO.match(objeto):
            raise ValueError("nombre de objeto no permitido")
        return self.raiz / objeto

    def guardar(self, objeto: str, contenido: bytes, content_type: str) -> None:
        ruta = self._ruta(objeto)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)

    def leer(self, objeto: str) -> bytes:
        return self._ruta(objeto).read_bytes()

    def eliminar(self, objeto: str) -> None:
        self._ruta(objeto).unlink(missing_ok=True)


class AlmacenGCS:
    def __init__(self, bucket: str):
        from google.cloud import storage

        self.bucket = storage.Client().bucket(bucket)

    def guardar(self, objeto: str, contenido: bytes, content_type: str) -> None:
        blob = self.bucket.blob(objeto)
        # if_generation_match=0: falla si el objeto ya existe (nunca se sobrescribe).
        blob.upload_from_string(contenido, content_type=content_type, if_generation_match=0)

    def leer(self, objeto: str) -> bytes:
        return self.bucket.blob(objeto).download_as_bytes()

    def eliminar(self, objeto: str) -> None:
        from google.api_core.exceptions import NotFound

        try:
            self.bucket.blob(objeto).delete()
        except NotFound:
            pass


@lru_cache
def get_almacen() -> AlmacenLocal | AlmacenGCS:
    s = get_settings()
    if s.storage_mode == "local":
        return AlmacenLocal(s.local_storage_dir)
    return AlmacenGCS(s.gcs_bucket)
