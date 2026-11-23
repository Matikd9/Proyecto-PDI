import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Estado, Resumen } from "../lib/tipos";
import { ETIQUETA_ESTADO } from "../lib/tipos";
import { Cargando, ChipEstado, Error, fecha } from "../componentes/Layout";

type Pagina = { items: Resumen[]; total: number; pagina: number; tamano: number };
const ESTADOS: Estado[] = ["EN_REVISION", "PREAPROBADA", "OBSERVADA", "EMITIDA", "RECHAZADA"];

export default function Backoffice() {
  const [params, setParams] = useSearchParams();
  const [pagina, setPagina] = useState<Pagina | null>(null);
  const [resumen, setResumen] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [q, setQ] = useState(params.get("q") ?? "");

  useEffect(() => {
    setPagina(null);
    Promise.all([api.get<Pagina>(`/backoffice/solicitudes?${params}`), api.get<Record<string, number>>("/backoffice/resumen")])
      .then(([p, r]) => { setPagina(p); setResumen(r); })
      .catch(setError);
  }, [params]);

  const filtrar = (k: string, v: string) => {
    const p = new URLSearchParams(params);
    if (v) p.set(k, v); else p.delete(k);
    if (k !== "pagina") p.delete("pagina");
    setParams(p);
  };
  const actual = Number(params.get("pagina") ?? 1);
  const paginas = pagina ? Math.max(1, Math.ceil(pagina.total / pagina.tamano)) : 1;

  return (
    <>
      <h1>Bandeja de solicitudes</h1>
      {resumen && (
        <div className="grilla grilla--3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", marginBottom: 18 }}>
          {ESTADOS.map((e) => (
            <button key={e} className="tarjeta contador enlace-claro" onClick={() => filtrar("estado", e)}
              style={{ outline: params.get("estado") === e ? "3px solid var(--amarillo)" : undefined }}>
              <strong>{resumen[e] ?? 0}</strong><span>{ETIQUETA_ESTADO[e]}</span>
            </button>
          ))}
        </div>
      )}
      <form className="tarjeta fila" style={{ marginBottom: 18 }} onSubmit={(e) => { e.preventDefault(); filtrar("q", q.trim()); }}>
        <label className="sr-only" htmlFor="f-estado">Estado</label>
        <select id="f-estado" value={params.get("estado") ?? ""} onChange={(e) => filtrar("estado", e.target.value)} style={{ width: "auto" }}>
          <option value="">Todos los estados</option>
          {[...ESTADOS, "RECIBIDA", "EN_VALIDACION"].map((e) => <option key={e} value={e}>{ETIQUETA_ESTADO[e as Estado]}</option>)}
        </select>
        <label className="sr-only" htmlFor="f-tramite">Trámite</label>
        <select id="f-tramite" value={params.get("tramite") ?? ""} onChange={(e) => filtrar("tramite", e.target.value)} style={{ width: "auto" }}>
          <option value="">Todos los trámites</option>
          <option value="CERT_VIAJES">Certificado de Viajes</option>
          <option value="VIGENCIA_PD">Vigencia de Permanencia Definitiva</option>
        </select>
        <label className="sr-only" htmlFor="f-q">Buscar</label>
        <input id="f-q" placeholder="Folio, documento o apellido" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 180 }} />
        <button className="boton" type="submit">Buscar</button>
      </form>
      <Error error={error} />
      {!pagina && !error && <Cargando />}
      {pagina && (
        <>
          <div className="tabla-envoltura">
            <table>
              <thead><tr><th>Folio</th><th>Trámite</th><th>Estado</th><th>Enviada</th><th></th></tr></thead>
              <tbody>
                {pagina.items.map((s) => (
                  <tr key={s.id}>
                    <td>{s.folio}</td>
                    <td>{s.tramite_nombre}</td>
                    <td><ChipEstado estado={s.estado} /></td>
                    <td>{fecha(s.enviado_en)}</td>
                    <td><Link to={`/backoffice/${s.id}`}>Revisar</Link></td>
                  </tr>
                ))}
                {pagina.items.length === 0 && <tr><td colSpan={5} className="suave">No hay solicitudes con estos filtros.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="fila fila--entre" style={{ marginTop: 12 }}>
            <span className="suave">{pagina.total} solicitudes</span>
            <div className="fila">
              <button className="boton boton--secundario boton--chico" disabled={actual <= 1} onClick={() => filtrar("pagina", String(actual - 1))}>Anterior</button>
              <span>{actual} / {paginas}</span>
              <button className="boton boton--secundario boton--chico" disabled={actual >= paginas} onClick={() => filtrar("pagina", String(actual + 1))}>Siguiente</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
