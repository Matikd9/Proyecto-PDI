import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Historial, Solicitud } from "../lib/tipos";
import { ETIQUETA_DOCUMENTO, ETIQUETA_ESTADO } from "../lib/tipos";
import { Cargando, ChipEstado, Error, fecha } from "../componentes/Layout";

export default function DetalleSolicitud() {
  const { id } = useParams();
  const [sol, setSol] = useState<Solicitud | null>(null);
  const [historial, setHistorial] = useState<Historial[]>([]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([api.get<Solicitud>(`/solicitudes/${id}`), api.get<Historial[]>(`/solicitudes/${id}/historial`)])
      .then(([s, h]) => { setSol(s); setHistorial(h); })
      .catch(setError);
  }, [id]);

  if (error) return <Error error={error} />;
  if (!sol) return <Cargando />;

  const descargar = (ruta: string, nombre: string) => api.descargar(ruta, nombre).catch(setError);

  return (
    <>
      <div className="miga"><Link to="/mis-solicitudes">Mis solicitudes</Link> › {sol.folio}</div>
      <div className="fila fila--entre">
        <h1>{sol.tramite_nombre}</h1>
        <ChipEstado estado={sol.estado} />
      </div>
      <p className="suave">Folio {sol.folio} · {sol.estado_descripcion}</p>

      {sol.estado === "OBSERVADA" && (
        <div className="mensaje mensaje--alerta">
          <strong>Requiere corrección:</strong> {sol.ultima_observacion}
          <div style={{ marginTop: 10 }}><Link className="boton boton--chico" to={`/solicitudes/${sol.id}/editar`}>Corregir solicitud</Link></div>
        </div>
      )}
      {sol.estado === "BORRADOR" && (
        <div className="mensaje mensaje--info">
          Esta solicitud aún no ha sido enviada.{" "}
          <Link to={`/solicitudes/${sol.id}/editar`}>Continuar</Link>
        </div>
      )}
      {sol.certificado_disponible && (
        <div className="mensaje mensaje--ok fila fila--entre">
          <span>Su certificado fue emitido.</span>
          <button className="boton boton--chico" onClick={() => descargar(`/solicitudes/${sol.id}/certificado`, `certificado-${sol.folio}.pdf`)}>
            Descargar certificado (PDF)
          </button>
        </div>
      )}

      <div className="grilla grilla--principal">
        <div>
          <div className="tarjeta">
            <h2>Datos</h2>
            <dl className="datos">
              <dt>Solicitante</dt><dd>{sol.nombres} {sol.apellidos}</dd>
              <dt>Documento</dt><dd>{sol.tipo_documento} {sol.numero_documento}</dd>
              <dt>Nacionalidad</dt><dd>{sol.nacionalidad}</dd>
              <dt>Contacto</dt><dd>{sol.email_contacto}</dd>
              {sol.datos_tramite.fecha_desde && <><dt>Período</dt><dd>{sol.datos_tramite.fecha_desde} a {sol.datos_tramite.fecha_hasta}</dd></>}
              <dt>Enviada</dt><dd>{fecha(sol.enviado_en)}</dd>
            </dl>
          </div>
          <div className="tarjeta">
            <h2>Documentos</h2>
            <ul className="lista-docs">
              {sol.documentos.map((d) => (
                <li key={d.id}>
                  <span>{ETIQUETA_DOCUMENTO[d.tipo]}: {d.nombre_original}</span>
                  <button className="boton boton--secundario boton--chico" onClick={() => descargar(`/documentos/${d.id}/contenido`, d.nombre_original)}>
                    Descargar
                  </button>
                </li>
              ))}
              {sol.documentos.length === 0 && <li className="suave">Sin documentos.</li>}
            </ul>
          </div>
        </div>
        <div className="tarjeta">
          <h2>Seguimiento</h2>
          <ol className="linea">
            {historial.map((h, i) => (
              <li key={i}>
                <strong>{ETIQUETA_ESTADO[h.estado_nuevo]}</strong>
                <div className="suave" style={{ fontSize: 13 }}>{fecha(h.creado_en)}</div>
                {h.comentario && <div style={{ fontSize: 14 }}>{h.comentario}</div>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </>
  );
}
