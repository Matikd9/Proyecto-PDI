import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useSesion } from "../lib/auth";
import type { Auditoria, Rol, Usuario } from "../lib/tipos";
import { Cargando, Error, fecha } from "../componentes/Layout";

export default function Admin() {
  const { usuario: yo } = useSesion();
  const [usuarios, setUsuarios] = useState<Usuario[] | null>(null);
  const [auditoria, setAuditoria] = useState<Auditoria[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<unknown>(null);

  const cargar = (busqueda = q) =>
    Promise.all([api.get<Usuario[]>(`/admin/usuarios?q=${encodeURIComponent(busqueda)}`), api.get<Auditoria[]>("/admin/auditoria?limite=50")])
      .then(([u, a]) => { setUsuarios(u); setAuditoria(a); })
      .catch(setError);

  useEffect(() => { cargar(""); }, []);

  const actualizar = async (u: Usuario, cambios: Partial<Pick<Usuario, "rol" | "activo">>) => {
    setError(null);
    try { await api.patch(`/admin/usuarios/${u.id}`, cambios); await cargar(); } catch (e) { setError(e); }
  };

  return (
    <>
      <h1>Administración de usuarios</h1>
      <p className="suave">Los cambios de rol tienen efecto inmediato y quedan registrados en la auditoría.</p>
      <form className="tarjeta fila" style={{ marginBottom: 18 }} onSubmit={(e) => { e.preventDefault(); cargar(); }}>
        <label className="sr-only" htmlFor="buscar">Buscar usuario</label>
        <input id="buscar" placeholder="Buscar por correo o nombre" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <button className="boton" type="submit">Buscar</button>
      </form>
      <Error error={error} />
      {!usuarios ? <Cargando /> : (
        <div className="tabla-envoltura">
          <table>
            <thead><tr><th>Correo</th><th>Nombre</th><th>Rol</th><th>Estado</th></tr></thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.nombre ?? "—"}</td>
                  <td>
                    <label className="sr-only" htmlFor={`rol-${u.id}`}>Rol de {u.email}</label>
                    <select id={`rol-${u.id}`} value={u.rol} disabled={u.id === yo?.id} style={{ width: "auto" }}
                      onChange={(e) => actualizar(u, { rol: e.target.value as Rol })}>
                      <option value="ciudadano">Ciudadano</option>
                      <option value="funcionario">Funcionario</option>
                      <option value="administrador">Administrador</option>
                    </select>
                  </td>
                  <td>
                    <button className={`boton boton--chico ${u.activo ? "boton--secundario" : ""}`} disabled={u.id === yo?.id}
                      onClick={() => actualizar(u, { activo: !u.activo })}>
                      {u.activo ? "Desactivar" : "Activar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="titulo-seccion" style={{ marginTop: 28 }}>Auditoría reciente</h2>
      <div className="tabla-envoltura">
        <table>
          <thead><tr><th>Fecha</th><th>Acción</th><th>Recurso</th><th>Detalle</th></tr></thead>
          <tbody>
            {auditoria.map((a) => (
              <tr key={a.id}>
                <td>{fecha(a.creado_en)}</td>
                <td>{a.accion}</td>
                <td>{a.recurso_tipo}</td>
                <td style={{ fontSize: 13 }}>{Object.entries(a.detalle).map(([k, v]) => `${k}: ${v}`).join(" · ")}</td>
              </tr>
            ))}
            {auditoria.length === 0 && <tr><td colSpan={4} className="suave">Sin registros.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
