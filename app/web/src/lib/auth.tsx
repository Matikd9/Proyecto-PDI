// Sesión del usuario. Identity Platform (firebase) solo dice QUIÉN es;
// el rol siempre viene de la API (/me), nunca del cliente.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Auth } from "firebase/auth";
import { config } from "./config";
import type { Usuario } from "./tipos";

type Sesion = {
  usuario: Usuario | null;
  cargando: boolean;
  ingresar: (email: string, clave: string) => Promise<void>;
  registrar: (email: string, clave: string, nombre: string) => Promise<void>;
  salir: () => Promise<void>;
  recargar: () => Promise<void>;
};

const Ctx = createContext<Sesion>(null!);
const CLAVE_DEV = "token-dev";
let auth: Auth | null = null;

async function firebaseAuth(): Promise<Auth> {
  if (auth) return auth;
  const { initializeApp } = await import("firebase/app");
  const { getAuth } = await import("firebase/auth");
  const app = initializeApp({
    apiKey: config.firebaseApiKey,
    authDomain: config.firebaseAuthDomain,
    projectId: config.firebaseProjectId,
  });
  auth = getAuth(app);
  await auth.authStateReady();
  return auth;
}

export async function obtenerToken(): Promise<string | null> {
  if (config.authMode === "dev") return sessionStorage.getItem(CLAVE_DEV);
  const a = await firebaseAuth();
  return a.currentUser ? a.currentUser.getIdToken() : null;
}

async function pedirPerfil(): Promise<Usuario | null> {
  const token = await obtenerToken();
  if (!token) return null;
  const r = await fetch(`${config.apiUrl}/api/v1/me`, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 403) throw new Error("Su cuenta está desactivada.");
  return r.ok ? r.json() : null;
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = async () => {
    try { setUsuario(await pedirPerfil()); } catch { setUsuario(null); }
  };

  useEffect(() => { recargar().finally(() => setCargando(false)); }, []);

  const ingresar = async (email: string, clave: string) => {
    if (config.authMode === "dev") {
      // Modo desarrollo local: no hay contraseña real; la API lo rechaza en la nube.
      sessionStorage.setItem(CLAVE_DEV, `dev|${email.toLowerCase()}|${email.toLowerCase()}`);
    } else {
      const { signInWithEmailAndPassword } = await import("firebase/auth");
      await signInWithEmailAndPassword(await firebaseAuth(), email, clave);
    }
    const perfil = await pedirPerfil();
    if (!perfil) throw new Error("No se pudo iniciar sesión.");
    setUsuario(perfil);
  };

  const registrar = async (email: string, clave: string, nombre: string) => {
    if (config.authMode === "firebase") {
      const { createUserWithEmailAndPassword, updateProfile } = await import("firebase/auth");
      const cred = await createUserWithEmailAndPassword(await firebaseAuth(), email, clave);
      await updateProfile(cred.user, { displayName: nombre });
      await cred.user.getIdToken(true);
    }
    await ingresar(email, clave);
  };

  const salir = async () => {
    sessionStorage.removeItem(CLAVE_DEV);
    if (config.authMode === "firebase") {
      const { signOut } = await import("firebase/auth");
      await signOut(await firebaseAuth());
    }
    setUsuario(null);
  };

  return <Ctx.Provider value={{ usuario, cargando, ingresar, registrar, salir, recargar }}>{children}</Ctx.Provider>;
}

export const useSesion = () => useContext(Ctx);
