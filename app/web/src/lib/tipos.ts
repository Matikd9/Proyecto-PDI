export type Rol = "ciudadano" | "funcionario" | "administrador";
export type Estado =
  | "BORRADOR" | "RECIBIDA" | "EN_VALIDACION" | "OBSERVADA"
  | "EN_REVISION" | "PREAPROBADA" | "EMITIDA" | "RECHAZADA";

export type Usuario = { id: string; email: string; nombre: string | null; rol: Rol; activo: boolean };

export type Tramite = { codigo: string; nombre: string; descripcion: string; documentos_requeridos: string[] };

export type Documento = {
  id: string; tipo: string; nombre_original: string; content_type: string; tamano_bytes: number; creado_en: string;
};

export type Resumen = {
  id: string; folio: string; tramite_codigo: string; tramite_nombre: string; estado: Estado;
  estado_descripcion: string; creado_en: string; enviado_en: string | null;
};

export type Solicitud = Resumen & {
  nombres: string | null; apellidos: string | null; tipo_documento: "RUT" | "PASAPORTE" | null;
  numero_documento: string | null; nacionalidad: string | null; fecha_nacimiento: string | null;
  email_contacto: string | null; datos_tramite: Record<string, string>; documentos: Documento[];
  ultima_observacion: string | null; editable: boolean; certificado_disponible: boolean;
};

export type Historial = { estado_anterior: Estado | null; estado_nuevo: Estado; comentario: string | null; creado_en: string };

export type SolicitudBackoffice = Solicitud & {
  estado_interno: Estado; solicitante_email: string; asignado_a_email: string | null;
  validaciones: { ronda: number; regla: string; resultado: "OK" | "ALERTA" | "FALTANTE"; detalle: Record<string, unknown>; creado_en: string }[];
  historial: (Historial & { actor_email: string | null; visible_ciudadano: boolean })[];
};

export type Auditoria = {
  id: number; actor_id: string | null; accion: string; recurso_tipo: string; recurso_id: string;
  detalle: Record<string, unknown>; creado_en: string;
};

export const ETIQUETA_ESTADO: Record<Estado, string> = {
  BORRADOR: "Borrador", RECIBIDA: "Recibida", EN_VALIDACION: "En validación", OBSERVADA: "Observada",
  EN_REVISION: "En revisión", PREAPROBADA: "Preaprobada", EMITIDA: "Emitida", RECHAZADA: "Rechazada",
};

export const ETIQUETA_DOCUMENTO: Record<string, string> = {
  identidad: "Documento de identidad (cédula o pasaporte)",
  resolucion_pd: "Resolución de permanencia definitiva",
  respaldo_viaje: "Respaldo de viaje (pasaje o timbre)",
  otro: "Otro documento",
};
