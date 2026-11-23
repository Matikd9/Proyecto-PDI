import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Error, fecha } from "../componentes/Layout";

type Resultado = { valido: boolean; folio: string | null; tramite: string | null; titular: string | null; emitido_en: string | null };

export default function Verificar() {
  const { codigo } = useParams();
  const [texto, setTexto] = useState(codigo ?? "");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [error, setError] = useState<unknown>(null);
  const navegar = useNavigate();

  useEffect(() => {
    setResultado(null);
    setError(null);
    if (codigo) api.get<Resultado>(`/certificados/verificar/${encodeURIComponent(codigo)}`).then(setResultado).catch(setError);
  }, [codigo]);

  const enviar = (e: FormEvent) => { e.preventDefault(); if (texto.trim()) navegar(`/verificar/${texto.trim().toUpperCase()}`); };

  return (
    <div style={{ maxWidth: 620, margin: "0 auto" }}>
      <h1>Verificar certificado</h1>
      <div className="tarjeta">
        <form onSubmit={enviar} className="fila">
          <label htmlFor="codigo" className="sr-only">Código de verificación</label>
          <input id="codigo" placeholder="Código de 12 caracteres" value={texto} maxLength={16}
            onChange={(e) => setTexto(e.target.value)} style={{ flex: 1, minWidth: 200, textTransform: "uppercase" }} />
          <button className="boton" type="submit">Verificar</button>
        </form>
      </div>
      <Error error={error} />
      {resultado && (resultado.valido ? (
        <div className="tarjeta">
          <div className="mensaje mensaje--ok">Certificado válido (prototipo académico, sin validez legal).</div>
          <dl className="datos">
            <dt>Folio</dt><dd>{resultado.folio}</dd>
            <dt>Trámite</dt><dd>{resultado.tramite}</dd>
            <dt>Titular</dt><dd>{resultado.titular}</dd>
            <dt>Emitido</dt><dd>{fecha(resultado.emitido_en)}</dd>
          </dl>
        </div>
      ) : (
        <div className="mensaje mensaje--error" style={{ marginTop: 18 }}>El código no corresponde a un certificado vigente.</div>
      ))}
    </div>
  );
}
