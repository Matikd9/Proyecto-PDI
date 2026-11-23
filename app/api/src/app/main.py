"""Punto de entrada de la API de Trámites."""
import json
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, backoffice, ciudadano, publico


class FormatoJson(logging.Formatter):
    """Una línea JSON por registro: Cloud Logging la interpreta como log estructurado."""

    def format(self, record: logging.LogRecord) -> str:
        datos = {"severity": record.levelname, "message": record.getMessage(), "logger": record.name}
        for clave in ("evento", "auditoria"):
            if hasattr(record, clave):
                datos[clave] = getattr(record, clave)
        if record.exc_info:
            datos["exception"] = self.formatException(record.exc_info)
        return json.dumps(datos, default=str, ensure_ascii=False)


def configurar_logs() -> None:
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoJson())
    logging.basicConfig(level=logging.INFO, handlers=[manejador], force=True)


def crear_app() -> FastAPI:
    s = get_settings()
    configurar_logs()
    app = FastAPI(
        title="API de Trámites Migratorios — Prototipo",
        description="Prueba de concepto académica (Grupo VPM, UAI). No es un servicio oficial de la PDI. "
                    "Use solo datos ficticios.",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.lista_cors,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def cabeceras_seguridad(request, call_next):
        respuesta = await call_next(request)
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
        return respuesta

    prefijo = "/api/v1"
    app.include_router(publico.router, prefix=prefijo)
    app.include_router(ciudadano.router, prefix=prefijo)
    app.include_router(ciudadano.documentos_router, prefix=prefijo)
    app.include_router(backoffice.router, prefix=prefijo)
    app.include_router(admin.router, prefix=prefijo)
    return app


app = crear_app()
