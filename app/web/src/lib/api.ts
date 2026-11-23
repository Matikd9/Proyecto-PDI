import { config } from "./config";
import { obtenerToken } from "./auth";

export class ErrorApi extends Error {
  constructor(public status: number, mensaje: string, public campos?: string[]) { super(mensaje); }
}

function mensajeDe(status: number, cuerpo: any): ErrorApi {
  const d = cuerpo?.detail;
  if (typeof d === "string") return new ErrorApi(status, d);
  if (d?.mensaje) return new ErrorApi(status, d.mensaje, d.campos);
  if (Array.isArray(d)) {
    const campos = d.map((e: any) => (e.loc ?? []).slice(-1)[0]).filter(Boolean);
    return new ErrorApi(status, "Revise los datos ingresados: " + d.map((e: any) => e.msg).join("; "), campos);
  }
  return new ErrorApi(status, `Error inesperado (${status}). Intente nuevamente.`);
}

async function solicitar(metodo: string, ruta: string, cuerpo?: unknown): Promise<Response> {
  const token = await obtenerToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (cuerpo instanceof FormData) body = cuerpo;
  else if (cuerpo !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(cuerpo); }
  const r = await fetch(`${config.apiUrl}/api/v1${ruta}`, { method: metodo, headers, body });
  if (!r.ok) throw mensajeDe(r.status, await r.json().catch(() => null));
  return r;
}

export const api = {
  get: async <T>(ruta: string) => (await solicitar("GET", ruta)).json() as Promise<T>,
  post: async <T>(ruta: string, cuerpo?: unknown) => (await solicitar("POST", ruta, cuerpo)).json() as Promise<T>,
  patch: async <T>(ruta: string, cuerpo: unknown) => (await solicitar("PATCH", ruta, cuerpo)).json() as Promise<T>,
  borrar: async (ruta: string) => { await solicitar("DELETE", ruta); },
  /** Descarga un archivo protegido (documento o certificado) usando el token. */
  descargar: async (ruta: string, nombre: string) => {
    const blob = await (await solicitar("GET", ruta)).blob();
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: nombre });
    a.click();
    URL.revokeObjectURL(url);
  },
};
