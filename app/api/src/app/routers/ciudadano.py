"""Endpoints del ciudadano: solo opera sobre SUS solicitudes (lo ajeno responde 404)."""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import estados
from app.config import get_settings
from app.db import get_db
from app.esquemas import (
    DATOS_POR_TRAMITE,
    DocumentoOut,
    HistorialOut,
    SolicitudActualizar,
    SolicitudCrear,
    SolicitudOut,
    SolicitudResumenOut,
)
from app.modelos import (
    Documento,
    Estado,
    HistorialEstado,
    Rol,
    Solicitud,
    TipoArchivo,
    Tramite,
    Usuario,
)
from app.seguridad import solo_ciudadano, usuario_actual
from app.serializar import detalle_ciudadano, historial_ciudadano, resumen_ciudadano
from app.servicios import almacenamiento, auditoria, certificados, eventos
from app.servicios import solicitudes as negocio

router = APIRouter(tags=["ciudadano"])


def _propia(db: Session, solicitud_id: uuid.UUID, usuario: Usuario) -> Solicitud:
    sol = db.get(Solicitud, solicitud_id)
    if not sol or sol.usuario_id != usuario.id:
        raise HTTPException(404, "Solicitud no encontrada")
    return sol


def _aplicar_campos(sol: Solicitud, datos: SolicitudActualizar | SolicitudCrear) -> None:
    valores = datos.model_dump(exclude_unset=True, exclude={"tramite_codigo"})
    if "datos_tramite" in valores:
        modelo = DATOS_POR_TRAMITE[sol.tramite.codigo]
        try:
            limpio = modelo.model_validate(valores.pop("datos_tramite") or {})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_url=False, include_context=False))
        sol.datos_tramite = limpio.model_dump(mode="json", exclude_none=True)
    for campo, valor in valores.items():
        setattr(sol, campo, valor)


@router.post("/solicitudes", response_model=SolicitudOut, status_code=201)
def crear(datos: SolicitudCrear, db: Session = Depends(get_db),
          usuario: Usuario = Depends(solo_ciudadano)):
    tramite = db.scalar(select(Tramite).where(Tramite.codigo == datos.tramite_codigo, Tramite.activo))
    if not tramite:
        raise HTTPException(422, "Trámite no válido")
    limite = get_settings().max_activas_por_tramite
    if negocio.activas_del_usuario(db, usuario.id, tramite.id) >= limite:
        raise HTTPException(429, f"Máximo {limite} solicitudes activas por trámite")
    sol = Solicitud(folio=negocio.generar_folio(), usuario_id=usuario.id, tramite=tramite,
                    estado=Estado.BORRADOR, datos_tramite={}, email_contacto=usuario.email)
    db.add(sol)
    _aplicar_campos(sol, datos)
    db.flush()
    db.add(HistorialEstado(solicitud_id=sol.id, estado_anterior=None, estado_nuevo=Estado.BORRADOR,
                           actor_id=usuario.id, visible_ciudadano=True))
    try:
        db.commit()
    except IntegrityError:  # colisión de folio (muy improbable)
        db.rollback()
        raise HTTPException(503, "Intente nuevamente")
    return detalle_ciudadano(sol)


@router.get("/solicitudes", response_model=list[SolicitudResumenOut])
def listar(db: Session = Depends(get_db), usuario: Usuario = Depends(solo_ciudadano)):
    sols = db.scalars(select(Solicitud).where(Solicitud.usuario_id == usuario.id)
                      .order_by(Solicitud.creado_en.desc())).all()
    return [resumen_ciudadano(s) for s in sols]


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudOut)
def obtener(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
            usuario: Usuario = Depends(solo_ciudadano)):
    return detalle_ciudadano(_propia(db, solicitud_id, usuario))


@router.patch("/solicitudes/{solicitud_id}", response_model=SolicitudOut)
def actualizar(solicitud_id: uuid.UUID, datos: SolicitudActualizar, db: Session = Depends(get_db),
               usuario: Usuario = Depends(solo_ciudadano)):
    sol = _propia(db, solicitud_id, usuario)
    if sol.estado not in estados.EDITABLES:
        raise HTTPException(409, "La solicitud no se puede editar en su estado actual")
    _aplicar_campos(sol, datos)
    db.commit()
    return detalle_ciudadano(sol)


@router.post("/solicitudes/{solicitud_id}/documentos", response_model=DocumentoOut, status_code=201)
async def subir_documento(solicitud_id: uuid.UUID, tipo: TipoArchivo = Form(...),
                          archivo: UploadFile = File(...), db: Session = Depends(get_db),
                          usuario: Usuario = Depends(solo_ciudadano)):
    s = get_settings()
    sol = _propia(db, solicitud_id, usuario)
    if sol.estado not in estados.EDITABLES:
        raise HTTPException(409, "No se pueden adjuntar documentos en el estado actual")
    if len(sol.documentos) >= s.max_documentos:
        raise HTTPException(409, f"Máximo {s.max_documentos} documentos por solicitud")

    limite = s.max_archivo_mb * 1024 * 1024
    contenido = await archivo.read(limite + 1)  # nunca se lee más de lo permitido
    if len(contenido) > limite:
        raise HTTPException(413, f"El archivo supera {s.max_archivo_mb} MB")
    if not contenido:
        raise HTTPException(422, "El archivo está vacío")
    tipo_real = almacenamiento.detectar_tipo(contenido)
    if not tipo_real:
        raise HTTPException(415, "Formato no permitido. Use PDF, JPG o PNG")

    doc = Documento(id=uuid.uuid4(), solicitud_id=sol.id, tipo=tipo,
                    nombre_original=almacenamiento.limpiar_nombre(archivo.filename),
                    content_type=tipo_real, tamano_bytes=len(contenido),
                    sha256=almacenamiento.sha256(contenido), subido_por=usuario.id)
    doc.objeto_gcs = almacenamiento.nombre_objeto(sol.id, doc.id)
    almacenamiento.get_almacen().guardar(doc.objeto_gcs, contenido, tipo_real)
    db.add(doc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        almacenamiento.get_almacen().eliminar(doc.objeto_gcs)  # no dejar huérfanos
        raise
    return doc


@router.delete("/solicitudes/{solicitud_id}/documentos/{documento_id}", status_code=204)
def eliminar_documento(solicitud_id: uuid.UUID, documento_id: uuid.UUID,
                       db: Session = Depends(get_db), usuario: Usuario = Depends(solo_ciudadano)):
    sol = _propia(db, solicitud_id, usuario)
    doc = db.get(Documento, documento_id)
    if not doc or doc.solicitud_id != sol.id:
        raise HTTPException(404, "Documento no encontrado")
    if sol.estado not in estados.EDITABLES:
        raise HTTPException(409, "No se pueden eliminar documentos en el estado actual")
    objeto = doc.objeto_gcs
    db.delete(doc)
    db.commit()
    almacenamiento.get_almacen().eliminar(objeto)
    return Response(status_code=204)


@router.post("/solicitudes/{solicitud_id}/enviar", response_model=SolicitudOut)
def enviar(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
           usuario: Usuario = Depends(solo_ciudadano)):
    sol = _propia(db, solicitud_id, usuario)
    if not estados.permitida(estados.TRANSICIONES_CIUDADANO, sol.estado, Estado.RECIBIDA):
        raise HTTPException(409, "La solicitud ya fue enviada")
    faltan = negocio.campos_faltantes(sol)
    if faltan:
        raise HTTPException(422, {"mensaje": "Faltan datos obligatorios", "campos": faltan})
    t = negocio.enviar(db, sol, usuario.id)
    db.commit()
    for e in t.eventos:
        eventos.publicar(e)
    db.refresh(sol)
    return detalle_ciudadano(sol)


@router.get("/solicitudes/{solicitud_id}/historial", response_model=list[HistorialOut])
def historial(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
              usuario: Usuario = Depends(solo_ciudadano)):
    return historial_ciudadano(_propia(db, solicitud_id, usuario))


@router.get("/solicitudes/{solicitud_id}/certificado")
def descargar_certificado(solicitud_id: uuid.UUID, db: Session = Depends(get_db),
                          usuario: Usuario = Depends(solo_ciudadano)):
    sol = _propia(db, solicitud_id, usuario)
    if sol.estado != Estado.EMITIDA or not sol.certificado:
        raise HTTPException(404, "Certificado no disponible")
    url = f"{get_settings().web_url.rstrip('/')}/verificar/{sol.certificado.codigo_verificacion}"
    pdf = certificados.generar_pdf(sol, sol.certificado, url)
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="certificado-{sol.folio}.pdf"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


# ---------- Descarga de documentos (dueño o funcionario) ----------
documentos_router = APIRouter(tags=["documentos"])


@documentos_router.get("/documentos/{documento_id}/contenido")
def contenido_documento(documento_id: uuid.UUID, db: Session = Depends(get_db),
                        usuario: Usuario = Depends(usuario_actual)):
    doc = db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    sol = doc.solicitud
    es_dueno = usuario.rol == Rol.CIUDADANO and sol.usuario_id == usuario.id
    es_funcionario = usuario.rol == Rol.FUNCIONARIO
    if not (es_dueno or es_funcionario):
        raise HTTPException(404, "Documento no encontrado")
    contenido = almacenamiento.get_almacen().leer(doc.objeto_gcs)
    if es_funcionario:
        auditoria.registrar(db, usuario.id, "DOCUMENTO_DESCARGADO", "documento", doc.id,
                            {"solicitud": sol.folio})
        db.commit()
    return Response(contenido, media_type=doc.content_type, headers={
        "Content-Disposition": almacenamiento.content_disposition(doc.nombre_original),
        "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
