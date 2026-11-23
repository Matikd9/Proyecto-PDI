// Asistente de 3 pasos. Sirve para crear (/solicitudes/nueva?tramite=X) y para corregir
// una solicitud en borrador u observada (/solicitudes/:id/editar).
import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ErrorApi } from "../lib/api";
import type { Solicitud, Tramite } from "../lib/tipos";
import { ETIQUETA_DOCUMENTO } from "../lib/tipos";
import { Cargando, Error } from "../componentes/Layout";

const MAX_MB = 5;
const TIPOS = ["application/pdf", "image/jpeg", "image/png"];

type Campos = Record<string, string>;
const CAMPOS_BASE = ["nombres", "apellidos", "tipo_documento", "numero_documento", "nacionalidad", "fecha_nacimiento", "email_contacto"];

function desdeSolicitud(s: Solicitud): Campos {
  const c: Campos = {};
  for (const k of CAMPOS_BASE) c[k] = ((s as any)[k] ?? "") as string;
  return { ...c, ...s.datos_tramite };
}

export default function FormSolicitud() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navegar = useNavigate();
  const [tramite, setTramite] = useState<Tramite | null>(null);
  const [sol, setSol] = useState<Solicitud | null>(null);
  const [campos, setCampos] = useState<Campos>({ tipo_documento: "RUT" });
  const pasoInicial = (useLocation().state as { paso?: number } | null)?.paso ?? 1;
  const [paso, setPaso] = useState(pasoInicial);
  const [error, setError] = useState<unknown>(null);
  const [errCampos, setErrCampos] = useState<string[]>([]);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        if (id) {
          const s = await api.get<Solicitud>(`/solicitudes/${id}`);
          if (!s.editable) { navegar(`/solicitudes/${id}`, { replace: true }); return; }
          setSol(s);
          setCampos(desdeSolicitud(s));
          setTramite(await api.get<Tramite>(`/tramites/${s.tramite_codigo}`));
          if (s.estado === "OBSERVADA") setPaso(2);
        } else {
          const codigo = params.get("tramite");
          if (!codigo) { setError("Seleccione un trámite desde la página de inicio."); return; }
          setTramite(await api.get<Tramite>(`/tramites/${encodeURIComponent(codigo)}`));
        }
      } catch (e) { setError(e); }
    })();
  }, [id]);

  if (error && !tramite) return <Error error={error} />;
  if (!tramite) return <Cargando />;

  const esViajes = tramite.codigo === "CERT_VIAJES";
  const cambiar = (k: string, v: string) => setCampos({ ...campos, [k]: v });

  const cuerpo = () => {
    const base: Record<string, unknown> = {};
    for (const k of CAMPOS_BASE) base[k] = campos[k] || null;
    base.datos_tramite = esViajes
      ? { fecha_desde: campos.fecha_desde || null, fecha_hasta: campos.fecha_hasta || null, motivo: campos.motivo || null }
      : { numero_resolucion: campos.numero_resolucion || null };
    return base;
  };

  const guardarDatos = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setErrCampos([]); setOcupado(true);
    try {
      const s = sol
        ? await api.patch<Solicitud>(`/solicitudes/${sol.id}`, cuerpo())
        : await api.post<Solicitud>("/solicitudes", { tramite_codigo: tramite.codigo, ...cuerpo() });
      setSol(s);
      // Cambiar de ruta vuelve a montar el componente: se indica el paso por el estado de navegación.
      if (!id) navegar(`/solicitudes/${s.id}/editar`, { replace: true, state: { paso: 2 } });
      setPaso(2);
    } catch (err) {
      setError(err);
      if (err instanceof ErrorApi) setErrCampos(err.campos ?? []);
    } finally { setOcupado(false); }
  };

  const subir = async (tipo: string, archivo: File | undefined) => {
    if (!archivo || !sol) return;
    setError(null);
    if (archivo.size > MAX_MB * 1024 * 1024) return setError(`El archivo supera ${MAX_MB} MB.`);
    if (!TIPOS.includes(archivo.type)) return setError("Formato no permitido. Use PDF, JPG o PNG.");
    const fd = new FormData();
    fd.append("tipo", tipo);
    fd.append("archivo", archivo);
    setOcupado(true);
    try {
      await api.post(`/solicitudes/${sol.id}/documentos`, fd);
      setSol(await api.get<Solicitud>(`/solicitudes/${sol.id}`));
    } catch (err) { setError(err); } finally { setOcupado(false); }
  };

  const quitar = async (docId: string) => {
    if (!sol) return;
    setOcupado(true);
    try {
      await api.borrar(`/solicitudes/${sol.id}/documentos/${docId}`);
      setSol(await api.get<Solicitud>(`/solicitudes/${sol.id}`));
    } catch (err) { setError(err); } finally { setOcupado(false); }
  };

  const enviar = async () => {
    if (!sol) return;
    setError(null); setOcupado(true);
    try {
      await api.post(`/solicitudes/${sol.id}/enviar`);
      navegar(`/solicitudes/${sol.id}`);
    } catch (err) { setError(err); setOcupado(false); }
  };

  const campo = (k: string, etiqueta: string, props: Record<string, unknown> = {}) => (
    <div className={`campo ${errCampos.includes(k) ? "campo--error" : ""}`}>
      <label htmlFor={k}>{etiqueta}</label>
      <input id={k} value={campos[k] ?? ""} onChange={(e) => cambiar(k, e.target.value)} {...props} />
    </div>
  );

  const opcionales = ["respaldo_viaje", "otro"].filter((t) => !tramite.documentos_requeridos.includes(t));
  const subidosDe = (t: string) => sol?.documentos.filter((d) => d.tipo === t) ?? [];
  const faltan = tramite.documentos_requeridos.filter((t) => subidosDe(t).length === 0);

  return (
    <>
      <div className="miga"><Link to="/">Inicio</Link> › {tramite.nombre}</div>
      <h1>{tramite.nombre}</h1>
      {sol && <p className="suave">Folio {sol.folio}</p>}
      {sol?.ultima_observacion && (
        <div className="mensaje mensaje--alerta"><strong>Corrección solicitada:</strong> {sol.ultima_observacion}</div>
      )}
      <ol className="pasos">
        {["Datos", "Documentos", "Revisión y envío"].map((p, i) => (
          <li key={p} className={paso === i + 1 ? "actual" : paso > i + 1 ? "hecho" : ""}>{p}</li>
        ))}
      </ol>
      <Error error={error} />

      {paso === 1 && (
        <form className="tarjeta" onSubmit={guardarDatos}>
          <h2>Datos del solicitante</h2>
          <div className="form-grilla">
            {campo("nombres", "Nombres", { required: true, maxLength: 100, autoComplete: "given-name" })}
            {campo("apellidos", "Apellidos", { required: true, maxLength: 100, autoComplete: "family-name" })}
            <div className="campo">
              <label htmlFor="tipo_documento">Tipo de documento</label>
              <select id="tipo_documento" value={campos.tipo_documento} onChange={(e) => cambiar("tipo_documento", e.target.value)}>
                <option value="RUT">RUT (cédula chilena)</option>
                <option value="PASAPORTE">Pasaporte</option>
              </select>
            </div>
            {campo("numero_documento", campos.tipo_documento === "RUT" ? "RUT (ej: 12345678-5)" : "N° de pasaporte",
              { required: true, maxLength: 20, pattern: "[0-9A-Za-z.\\-]+" })}
            {campo("nacionalidad", "Nacionalidad", { required: true, maxLength: 60 })}
            {campo("fecha_nacimiento", "Fecha de nacimiento", { required: true, type: "date" })}
            {campo("email_contacto", "Correo de contacto", { required: true, type: "email" })}
          </div>
          <h2 style={{ marginTop: 10 }}>Datos del trámite</h2>
          <div className="form-grilla">
            {esViajes ? (
              <>
                {campo("fecha_desde", "Período desde", { required: true, type: "date" })}
                {campo("fecha_hasta", "Período hasta", { required: true, type: "date" })}
                {campo("motivo", "Motivo de la solicitud", { required: true, maxLength: 300 })}
              </>
            ) : (
              campo("numero_resolucion", "N° de resolución de permanencia definitiva (opcional)", { maxLength: 30 })
            )}
          </div>
          <div className="fila fila--entre">
            <Link to="/" className="boton boton--secundario">Cancelar</Link>
            <button className="boton" type="submit" disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar y continuar"}</button>
          </div>
        </form>
      )}

      {paso === 2 && sol && (
        <div className="tarjeta">
          <h2>Documentos</h2>
          <p className="suave">PDF, JPG o PNG de hasta {MAX_MB} MB. Use solo documentos ficticios.</p>
          {[...tramite.documentos_requeridos, ...opcionales].map((t) => (
            <div key={t} style={{ borderTop: "1px solid var(--borde)", padding: "12px 0" }}>
              <div className="fila fila--entre">
                <div>
                  <strong>{ETIQUETA_DOCUMENTO[t]}</strong>{" "}
                  <span className="suave">{tramite.documentos_requeridos.includes(t) ? "(obligatorio)" : "(opcional)"}</span>
                </div>
                <label className="boton boton--secundario boton--chico">
                  Adjuntar
                  <input type="file" className="sr-only" accept=".pdf,.jpg,.jpeg,.png" disabled={ocupado}
                    onChange={(e) => { subir(t, e.target.files?.[0]); e.target.value = ""; }} />
                </label>
              </div>
              <ul className="lista-docs">
                {subidosDe(t).map((d) => (
                  <li key={d.id}>
                    <span>{d.nombre_original} <span className="suave">({Math.ceil(d.tamano_bytes / 1024)} KB)</span></span>
                    <button className="boton boton--secundario boton--chico" onClick={() => quitar(d.id)} disabled={ocupado}>Quitar</button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div className="fila fila--entre" style={{ marginTop: 10 }}>
            <button className="boton boton--secundario" onClick={() => setPaso(1)}>Volver</button>
            <button className="boton" onClick={() => setPaso(3)} disabled={faltan.length > 0}>Continuar</button>
          </div>
          {faltan.length > 0 && <p className="suave" style={{ textAlign: "right" }}>Faltan documentos obligatorios.</p>}
        </div>
      )}

      {paso === 3 && sol && (
        <div className="tarjeta">
          <h2>Revise y envíe</h2>
          <dl className="datos">
            <dt>Solicitante</dt><dd>{campos.nombres} {campos.apellidos}</dd>
            <dt>Documento</dt><dd>{campos.tipo_documento} {campos.numero_documento}</dd>
            <dt>Nacionalidad</dt><dd>{campos.nacionalidad}</dd>
            <dt>Contacto</dt><dd>{campos.email_contacto}</dd>
            {esViajes && <><dt>Período</dt><dd>{campos.fecha_desde} a {campos.fecha_hasta}</dd></>}
            <dt>Documentos</dt><dd>{sol.documentos.map((d) => d.nombre_original).join(", ")}</dd>
          </dl>
          <div className="mensaje mensaje--info" style={{ marginTop: 16 }}>
            Al enviar, el sistema validará su solicitud automáticamente. Podrá seguir su estado en "Mis solicitudes".
          </div>
          <div className="fila fila--entre">
            <button className="boton boton--secundario" onClick={() => setPaso(2)}>Volver</button>
            <button className="boton" onClick={enviar} disabled={ocupado}>{ocupado ? "Enviando…" : "Enviar solicitud"}</button>
          </div>
        </div>
      )}
    </>
  );
}
