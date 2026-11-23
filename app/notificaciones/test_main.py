"""python -m pytest app/notificaciones"""
import base64
import json

import main


def _push(evento: dict) -> bytes:
    return json.dumps({"message": {"data": base64.b64encode(json.dumps(evento).encode()).decode(),
                                   "messageId": "1"}}).encode()


def test_notifica_estado_publico(capsys):
    main.procesar(_push({"estado_publico": "OBSERVADA", "folio": "VPM-2026-ABC123", "email_contacto": "a@ficticio.cl"}))
    log = json.loads(capsys.readouterr().out)
    assert log["notificacion"]["para"] == "a@ficticio.cl"
    assert "VPM-2026-ABC123" in log["notificacion"]["texto"]


def test_estados_sin_aviso_no_registran(capsys):
    main.procesar(_push({"estado_publico": "BORRADOR", "folio": "X"}))
    assert capsys.readouterr().out == ""
