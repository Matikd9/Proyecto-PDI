"""Servicio de notificaciones: recibe los eventos de Pub/Sub (push) y registra la notificación.

El envío de correo está SIMULADO: la notificación queda como log estructurado en Cloud Logging.
Solo la cuenta de servicio de la suscripción puede invocarlo (Cloud Run con IAM e ingreso interno),
por eso no se valida el token aquí.
"""
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

MENSAJES = {
    "RECIBIDA": "Hemos recibido su solicitud {folio}.",
    "OBSERVADA": "Su solicitud {folio} requiere correcciones. Ingrese al portal para revisarlas.",
    "EN_REVISION": "Su solicitud {folio} está siendo revisada por un funcionario.",
    "EMITIDA": "Su certificado de la solicitud {folio} fue emitido.",
    "RECHAZADA": "Su solicitud {folio} fue rechazada. Ingrese al portal para ver el motivo.",
}


def log(severidad: str, mensaje: str, **datos) -> None:
    print(json.dumps({"severity": severidad, "message": mensaje, **datos}, ensure_ascii=False), flush=True)


def procesar(cuerpo: bytes) -> None:
    mensaje = json.loads(cuerpo)["message"]
    evento = json.loads(base64.b64decode(mensaje["data"]))
    texto = MENSAJES.get(evento.get("estado_publico", ""))
    if not texto:
        return  # estados internos o sin aviso al ciudadano
    log("INFO", "notificacion simulada", notificacion={
        "para": evento.get("email_contacto"),
        "asunto": "Trámites Migratorios (prototipo)",
        "texto": texto.format(folio=evento.get("folio")),
        "solicitud_id": evento.get("solicitud_id"),
        "pubsub_message_id": mensaje.get("messageId"),
    })


class Manejador(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            procesar(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.send_response(204)
        except (KeyError, ValueError) as exc:
            # Mensaje mal formado: se responde 204 para que Pub/Sub no lo reintente sin fin.
            log("ERROR", "evento invalido", error=str(exc))
            self.send_response(204)
        self.end_headers()

    def log_message(self, *args):  # silencia el log por defecto de http.server
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Manejador).serve_forever()
