"""Configuración de la API, leída desde variables de entorno."""
import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: Literal["local", "dev", "qa", "prod"] = "local"
    gcp_project: str = ""

    # Base de datos: DATABASE_URL (local/pruebas) o piezas separadas (Cloud SQL).
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tramites"
    db_user: str = "tramites"
    db_password: str = ""
    db_sslmode: str = "prefer"

    # Integraciones (modo local para desarrollo y pruebas).
    auth_mode: Literal["firebase", "dev"] = "firebase"
    storage_mode: Literal["gcs", "local"] = "gcs"
    gcs_bucket: str = ""
    local_storage_dir: str = ".local-storage"
    events_mode: Literal["pubsub", "log"] = "pubsub"
    pubsub_topic: str = "solicitud-eventos"

    cors_origins: str = "http://localhost:5173"
    web_url: str = "http://localhost:5173"  # para el enlace de verificación del certificado

    # Reglas de negocio.
    max_archivo_mb: int = 5
    max_documentos: int = 6
    max_activas_por_tramite: int = 3

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validar_seguridad(self) -> None:
        """Impide configuraciones inseguras en la nube."""
        en_cloud_run = bool(os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"))
        if en_cloud_run and (self.auth_mode == "dev" or self.entorno == "local"):
            raise RuntimeError("AUTH_MODE=dev / ENTORNO=local no están permitidos en Cloud Run")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validar_seguridad()
    return s
