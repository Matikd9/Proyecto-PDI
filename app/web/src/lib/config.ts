// Configuración en tiempo de ejecución: la misma imagen sirve para cualquier ambiente.
// En Cloud Run nginx genera /config.json desde variables de entorno.
export type Config = {
  apiUrl: string;
  authMode: "dev" | "firebase";
  firebaseApiKey?: string;
  firebaseAuthDomain?: string;
  firebaseProjectId?: string;
};

export let config: Config;

export async function cargarConfig(): Promise<void> {
  const r = await fetch("/config.json", { cache: "no-store" });
  if (!r.ok) throw new Error("No se pudo cargar /config.json");
  config = await r.json();
}
