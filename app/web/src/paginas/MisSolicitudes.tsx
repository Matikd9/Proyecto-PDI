import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Resumen } from "../lib/tipos";
import { Cargando, ChipEstado, Error, fecha } from "../componentes/Layout";

export default function MisSolicitudes() {
  const [lista, setLista] = useState<Resumen[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => { api.get<Resumen[]>("/solicitudes").then(setLista).catch(setError); }, []);

  return (
    <>
      <div className="fila fila--entre">
        <h1>Mis solicitudes</h1>
        <Link className="boton" to="/">Nueva solicitud</Link>
      </div>
      <Error error={error} />
      {!lista && !error && <Cargando />}
      {lista?.length === 0 && <div className="tarjeta">Aún no tiene solicitudes. Elija un trámite en la página de inicio.</div>}
      {lista && lista.length > 0 && (
        <div className="tabla-envoltura">
          <table>
            <thead><tr><th>Folio</th><th>Trámite</th><th>Estado</th><th>Creada</th><th></th></tr></thead>
            <tbody>
              {lista.map((s) => (
                <tr key={s.id}>
                  <td>{s.folio}</td>
                  <td>{s.tramite_nombre}</td>
                  <td><ChipEstado estado={s.estado} /></td>
                  <td>{fecha(s.creado_en)}</td>
                  <td><Link to={`/solicitudes/${s.id}`}>Ver detalle</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
