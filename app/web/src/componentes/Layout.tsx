import { useState, type ReactNode } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useSesion } from "../lib/auth";
import type { Estado, Rol } from "../lib/tipos";
import { ETIQUETA_ESTADO } from "../lib/tipos";

export function Layout() {
  const { usuario, salir } = useSesion();
  const [abierto, setAbierto] = useState(false);
  const navegar = useNavigate();
  const { pathname } = useLocation();

  const enlaces: [string, string, boolean][] = [
    ["/", "Inicio", true],
    ["/mis-solicitudes", "Mis solicitudes", usuario?.rol === "ciudadano"],
    ["/backoffice", "Bandeja de funcionarios", usuario?.rol === "funcionario"],
    ["/admin", "Administración", usuario?.rol === "administrador"],
    ["/verificar", "Verificar certificado", true],
  ];

  return (
    <div className="app">
      <div className="aviso-poc" role="note">
        Prueba de concepto académica — Grupo VPM, UAI. No es un servicio oficial de la PDI. Use solo datos ficticios.
      </div>
      <header className="encabezado">
        <div className="contenedor encabezado__fila">
          <Link to="/" className="marca" aria-label="DPI, inicio">
            <span className="logo-dpi" aria-hidden="true">DPI</span>
            <span className="marca__sub">Prototipo · Arquitectura Cloud</span>
          </Link>
          <div className="utilidades">
            {usuario ? (
              <>
                <span className="chip-usuario ocultar-movil">{usuario.email} · {usuario.rol}</span>
                <button className="enlace-claro" onClick={async () => { await salir(); navegar("/"); }}>Cerrar sesión</button>
              </>
            ) : (
              <Link to="/ingresar" state={{ desde: pathname }}>Ingresar</Link>
            )}
            <button className="menu-boton" aria-expanded={abierto} aria-controls="nav-principal" onClick={() => setAbierto(!abierto)}>
              Menú
            </button>
          </div>
        </div>
        <nav id="nav-principal" className={`contenedor nav ${abierto ? "abierto" : ""}`} aria-label="Principal" onClick={() => setAbierto(false)}>
          {enlaces.filter(([, , ver]) => ver).map(([to, texto]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "activo" : "")}>{texto}</NavLink>
          ))}
        </nav>
      </header>
      <main><div className="contenedor"><Outlet /></div></main>
      <footer className="pie">
        <div className="contenedor">
          <strong>Laboratorio 3 · Arquitectura Cloud · Universidad Adolfo Ibáñez</strong><br />
          Vicente Vásquez · Matías Medina · Pascal Jorquera — Profesor Nicolás Riderelli.<br />
          Prototipo sin validez legal. Las consultas a Registro Civil, Migraciones e Interpol están simuladas.
        </div>
      </footer>
    </div>
  );
}

/** Exige sesión y rol. El backend vuelve a validar todo; esto es solo navegación. */
export function Protegida({ rol, children }: { rol: Rol; children: ReactNode }) {
  const { usuario, cargando } = useSesion();
  const { pathname, search } = useLocation();
  if (cargando) return <Cargando />;
  if (!usuario) return <Navigate to="/ingresar" replace state={{ desde: pathname + search }} />;
  if (usuario.rol !== rol) return <div className="mensaje mensaje--error">No tiene permisos para ver esta página.</div>;
  return <>{children}</>;
}

export const Cargando = () => <p className="suave" role="status">Cargando…</p>;

export const Error = ({ error }: { error: unknown }) =>
  error ? <div className="mensaje mensaje--error" role="alert">{error instanceof globalThis.Error ? error.message : String(error)}</div> : null;

export const ChipEstado = ({ estado }: { estado: Estado }) => (
  <span className={`estado estado--${estado}`}>{ETIQUETA_ESTADO[estado]}</span>
);

export const fecha = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" }) : "—";
