"""Generación del PDF del certificado (al vuelo, no se almacena)."""
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.modelos import Certificado, Solicitud

AZUL = HexColor("#00234C")
AMARILLO = HexColor("#FFD100")


def enmascarar(nombres: str | None, apellidos: str | None) -> str:
    partes = f"{nombres or ''} {apellidos or ''}".split()
    return " ".join(p[0] + "*" * (len(p) - 1) for p in partes)


def generar_pdf(sol: Solicitud, cert: Certificado, url_verificacion: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4

    c.setFillColor(AZUL)
    c.rect(0, alto - 90, ancho, 90, fill=1, stroke=0)
    c.setFillColor(AMARILLO)
    c.rect(0, alto - 96, ancho, 6, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, alto - 50, "Trámites Migratorios · Prototipo")
    c.setFont("Helvetica", 10)
    c.drawString(40, alto - 70, "Prueba de concepto académica — Grupo VPM, UAI")

    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, alto - 150, sol.tramite.nombre)

    c.setFillColor(HexColor("#212529"))
    c.setFont("Helvetica", 11)
    lineas = [
        f"Folio: {sol.folio}",
        f"Titular: {sol.nombres} {sol.apellidos}",
        f"Documento: {sol.tipo_documento.value if sol.tipo_documento else ''} {sol.numero_documento}",
        f"Nacionalidad: {sol.nacionalidad}",
        f"Fecha de emisión: {cert.emitido_en:%d-%m-%Y %H:%M} UTC",
    ]
    d = sol.datos_tramite or {}
    if sol.tramite.codigo == "CERT_VIAJES":
        lineas.append(f"Período consultado: {d.get('fecha_desde')} a {d.get('fecha_hasta')}")
        lineas.append("Resultado: registros de viaje simulados (no corresponden a datos reales).")
    else:
        lineas.append("Resultado: permanencia definitiva VIGENTE (simulado).")
    y = alto - 190
    for linea in lineas:
        c.drawString(40, y, linea)
        y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 20, f"Código de verificación: {cert.codigo_verificacion}")
    c.setFont("Helvetica", 9)
    c.drawString(40, y - 38, f"Verifique en: {url_verificacion}")

    c.saveState()
    c.setFillColor(HexColor("#C8102E"))
    c.setFont("Helvetica-Bold", 40)
    c.translate(ancho / 2, alto / 2 - 120)
    c.rotate(30)
    c.setFillAlpha(0.15)
    c.drawCentredString(0, 0, "DOCUMENTO FICTICIO")
    c.restoreState()

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#6E6E6E"))
    c.drawString(40, 40, "Este documento es parte de una prueba de concepto académica. "
                         "No es un certificado oficial de la PDI ni tiene validez legal.")
    c.showPage()
    c.save()
    return buf.getvalue()
