"""Publicación de eventos de cambio de estado (Pub/Sub) y registro estructurado (Cloud Logging)."""
import json
import logging
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger("eventos")


@lru_cache
def _publisher():
    from google.cloud import pubsub_v1

    return pubsub_v1.PublisherClient()


def publicar(evento: dict) -> None:
    """Se llama DESPUÉS del commit. Un fallo no revierte la solicitud (ver decisión D-09)."""
    s = get_settings()
    log.info("evento %s", evento["tipo"], extra={"evento": evento})
    if s.events_mode != "pubsub":
        return
    try:
        topic = _publisher().topic_path(s.gcp_project, s.pubsub_topic)
        datos = json.dumps(evento, default=str).encode()
        _publisher().publish(topic, datos, tipo=evento["tipo"]).result(timeout=10)
    except Exception:
        log.exception("no se pudo publicar el evento en Pub/Sub")
