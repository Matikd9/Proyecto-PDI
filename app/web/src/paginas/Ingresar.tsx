import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useSesion } from "../lib/auth";
import { config } from "../lib/config";
import { Error } from "../componentes/Layout";

const INICIO_POR_ROL = { ciudadano: "/mis-solicitudes", funcionario: "/backoffice", administrador: "/admin" };

// Traduce los códigos de error de Identity Platform a mensajes comprensibles.
function traducir(e: any): string {
  const c: string = e?.code ?? "";
  if (c.includes("invalid-credential") || c.includes("wrong-password") || c.includes("user-not-found")) return "Correo o contraseña incorrectos.";
  if (c.includes("email-already-in-use")) return "Ya existe una cuenta con ese correo.";
  if (c.includes("weak-password")) return "La contraseña debe tener al menos 6 caracteres.";
  if (c.includes("too-many-requests")) return "Demasiados intentos. Espere unos minutos.";
  return e?.message ?? "No se pudo completar la operación.";
}

export default function Ingresar() {
  const { usuario, ingresar, registrar } = useSesion();
  const [modo, setModo] = useState<"ingresar" | "registrar">("ingresar");
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const desde = (useLocation().state as { desde?: string } | null)?.desde;

  if (usuario) return <Navigate to={desde && desde !== "/ingresar" ? desde : INICIO_POR_ROL[usuario.rol]} replace />;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      if (modo === "ingresar") await ingresar(email, clave);
      else await registrar(email, clave, nombre);
      // Al quedar `usuario` definido, el <Navigate> de arriba redirige.
    } catch (err) {
      setError(traducir(err));
    } finally {
      setEnviando(false);
    }
  };

  const dev = config.authMode === "dev";
  return (
    <div style={{ maxWidth: 460, margin: "0 auto" }}>
      <h1>{modo === "ingresar" ? "Ingresar" : "Crear cuenta"}</h1>
      <div className="tarjeta">
        {dev && (
          <div className="mensaje mensaje--alerta">
            Modo desarrollo local: se ingresa solo con el correo (sin contraseña real). Este modo está bloqueado en la nube.
          </div>
        )}
        <Error error={error} />
        <form onSubmit={enviar}>
          {modo === "registrar" && (
            <div className="campo">
              <label htmlFor="nombre">Nombre</label>
              <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required maxLength={120} autoComplete="name" />
            </div>
          )}
          <div className="campo">
            <label htmlFor="email">Correo electrónico</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </div>
          {!dev && (
            <div className="campo">
              <label htmlFor="clave">Contraseña</label>
              <input id="clave" type="password" value={clave} onChange={(e) => setClave(e.target.value)} required minLength={6}
                autoComplete={modo === "ingresar" ? "current-password" : "new-password"} />
              {modo === "registrar" && <span className="ayuda">Mínimo 6 caracteres.</span>}
            </div>
          )}
          <button className="boton" type="submit" disabled={enviando} style={{ width: "100%" }}>
            {enviando ? "Procesando…" : modo === "ingresar" ? "Ingresar" : "Crear cuenta"}
          </button>
        </form>

        <p style={{ textAlign: "center", margin: "16px 0 8px" }}>
          {modo === "ingresar" ? "¿No tiene cuenta? " : "¿Ya tiene cuenta? "}
          <button className="enlace-claro" style={{ color: "var(--enlace)", textDecoration: "underline" }}
            onClick={() => { setModo(modo === "ingresar" ? "registrar" : "ingresar"); setError(null); }}>
            {modo === "ingresar" ? "Crear una cuenta" : "Ingresar"}
          </button>
        </p>
        <hr style={{ border: 0, borderTop: "1px solid var(--borde)", margin: "16px 0" }} />
        <button className="btn-cu btn-m btn-color-estandar rounded-full btn-fw" type="button" disabled
          aria-label="Iniciar sesión con ClaveÚnica (simulado, no disponible en el prototipo)">
          <span className="cl-claveunica" aria-hidden="true"></span>
          <span className="texto" aria-hidden="true">Iniciar sesión</span>
        </button>
        <p className="suave" style={{ fontSize: 12, textAlign: "center", margin: "6px 0 12px" }}>
          ClaveÚnica está simulada: no está integrada en el prototipo.
        </p>
        <p className="suave" style={{ fontSize: 12, marginBottom: 0 }}>
          Las cuentas nuevas tienen rol ciudadano. Los roles de funcionario y administrador los asigna un administrador.
        </p>
      </div>
    </div>
  );
}
