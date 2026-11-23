"""Catálogo de trámites (se carga en la migración inicial y en las pruebas)."""
from sqlalchemy.orm import Session

from app.modelos import Tramite

TRAMITES = [
    {
        "id": 1,
        "codigo": "CERT_VIAJES",
        "nombre": "Certificado de Viajes",
        "descripcion": "Certifica las entradas y salidas del país registradas en un período.",
        "documentos_requeridos": ["identidad"],
    },
    {
        "id": 2,
        "codigo": "VIGENCIA_PD",
        "nombre": "Certificado de Vigencia de Permanencia Definitiva",
        "descripcion": "Acredita que la permanencia definitiva de una persona extranjera se encuentra vigente.",
        "documentos_requeridos": ["identidad", "resolucion_pd"],
    },
]


def cargar_catalogo(db: Session) -> None:
    for t in TRAMITES:
        if db.get(Tramite, t["id"]) is None:
            db.add(Tramite(**t, activo=True))
    db.commit()
