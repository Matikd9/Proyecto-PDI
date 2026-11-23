import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Estado, SolicitudBackoffice } from "../lib/tipos";
import { ETIQUETA_DOCUMENTO, ETIQUETA_ESTADO } from "../lib/tipos";
import { Cargando, ChipEstado, Error, fecha } from "../componentes/Layout";

// Solo para mostrar los botones; la API valida la matriz de transiciones.
const ACCIONES: Partial<Record<Estado, [Estado, string, string][]>> = {
  EN_REVISION: [["PREAPROBADA", "Validar antecedentes", ""], ["OBSERVADA", "Pedir corrección", "boton--secundario"], ["RECHAZADA", "Rechazar", "boton--peligro"]],
  PREAPROBADA: [["EMITIDA", "Aprobar y emitir certificado", ""], ["OBSERVADA", "Pedir corrección", "boton--secundario"], ["RECHAZADA", "Rechazar", "boton--peligro"]],
};
const REGLA: Record<string, string> = {
  DOCUMENTOS_OBLIGATORIOS: "Documentos obligatorios", DUPLICADOS: "Duplicados",
  REGISTRO_CIVIL_SIM: "Registro Civil (simulado)", MIGRACIONES_SIM: "Migraciones (simulado)",
  ALERTAS_INTERPOL_SIM: "Alertas / Interpol (simulado)", LECTURA_DOCUMENTO: "Lectura del documento (Gemini)",
};

export default function BackofficeDetalle() {
  const { id } = useParams();
  const [sol, setSol] = useState<SolicitudBackoffice | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [comentario, setComentario] = useState("");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => { api.get<SolicitudBackoffice>(`/backoffice/solicitudes/${id}`).then(setSol).catch(setError); }, [id]);

  if (!sol) return error ? <Error error={error} /> : <Cargando />;

  const accion = async (ruta: string, cuerpo?: unknown) => {
    setError(null); setOcupado(true);
    try { setSol(await api.post<SolicitudBackoffice>(ruta, cuerpo)); setComentario(""); }
    catch (e) { setError(e); } finally { setOcupado(false); }
  };
  const ronda = Math.max(0, ...sol.validaciones.map((v) => v.ronda));
  const acciones = ACCIONES[sol.estado_interno] ?? [];

  return (
    <>
      <div className="miga"><Link to="/backoffice">Bandeja</Link> › {sol.folio}</div>
      <div className="fila fila--entre">
        <h1>{sol.tramite_nombre}</h1>
        <ChipEstado estado={sol.estado_interno} />
      </div>
      <p className="suave">
        Folio {sol.folio} · Solicitante {sol.solicitante_email} · Asignada a {sol.asignado_a_email ?? "nadie"}
        {!sol.asignado_a_email && <> · <button className="enlace-claro" style={{ color: "var(--enlace)" }} onClick={() => accion(`/backoffice/solicitudes/${sol.id}/asignar`)}>asignarme</button></>}
      </p>
      <Error error={error} />

      <div className="grilla grilla--principal">
        <div>
          <div className="tarjeta">
            <h2>Validación automática <span className="suave" style={{ fontSize: 14 }}>(ronda {ronda})</span></h2>
            <div className="tabla-envoltura">
              <table>
                <thead><tr><th>Regla</th><th>Resultado</th><th>Detalle</th></tr></thead>
                <tbody>
                  {sol.validaciones.filter((v) => v.ronda === ronda).map((v) => (
                    <tr key={v.regla}>
                      <td>{REGLA[v.regla] ?? v.regla}</td>
                      <td><span className={`estado ${v.resultado === "OK" ? "estado--EMITIDA" : v.resultado === "ALERTA" ? "estado--RECHAZADA" : "estado--OBSERVADA"}`}>{v.resultado}</span></td>
                      <td style={{ fontSize: 13 }}>{String(v.detalle.motivo ?? "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="tarjeta">
            <h2>Datos del solicitante</h2>
            <dl className="datos">
              <dt>Nombre</dt><dd>{sol.nombres} {sol.apellidos}</dd>
              <dt>Documento</dt><dd>{sol.tipo_documento} {sol.numero_documento}</dd>
              <dt>Nacionalidad</dt><dd>{sol.nacionalidad}</dd>
              <dt>Nacimiento</dt><dd>{sol.fecha_nacimiento}</dd>
              <dt>Contacto</dt><dd>{sol.email_contacto}</dd>
              {Object.entries(sol.datos_tramite).map(([k, v]) => <Fragment key={k}><dt>{k.replace("_", " ")}</dt><dd>{v}</dd></Fragment>)}
            </dl>
          </div>
          <div className="tarjeta">
            <h2>Documentos</h2>
            <p className="suave" style={{ fontSize: 13 }}>Cada descarga queda registrada en la auditoría.</p>
            <ul className="lista-docs">
              {sol.documentos.map((d) => (
                <li key={d.id}>
                  <span>{ETIQUETA_DOCUMENTO[d.tipo]}: {d.nombre_original}</span>
                  <button className="boton boton--secundario boton--chico" onClick={() => api.descargar(`/documentos/${d.id}/contenido`, d.nombre_original).catch(setError)}>Descargar</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div>
          {acciones.length > 0 && (
            <div className="tarjeta">
              <h2>Resolver</h2>
              <div className="campo">
                <label htmlFor="comentario">Comentario</label>
                <textarea id="comentario" rows={3} maxLength={1000} value={comentario} onChange={(e) => setComentario(e.target.value)} />
                <span className="ayuda">Obligatorio para pedir corrección o rechazar. El ciudadano verá el comentario.</span>
              </div>
              <div className="grilla">
                {acciones.map(([estado, texto, clase]) => (
                  <button key={estado} className={`boton ${clase}`} disabled={ocupado}
                    onClick={() => accion(`/backoffice/solicitudes/${sol.id}/transiciones`, { estado_nuevo: estado, comentario: comentario || null })}>
                    {texto}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="tarjeta">
            <h2>Historial</h2>
            <ol className="linea">
              {sol.historial.map((h, i) => (
                <li key={i}>
                  <strong>{ETIQUETA_ESTADO[h.estado_nuevo]}</strong>
                  <div className="suave" style={{ fontSize: 12 }}>{fecha(h.creado_en)} · {h.actor_email ?? "sistema"}{!h.visible_ciudadano && " · interno"}</div>
                  {h.comentario && <div style={{ fontSize: 14 }}>{h.comentario}</div>}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </>
  );
}
