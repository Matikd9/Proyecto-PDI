import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useSesion } from "../lib/auth";
import type { Tramite } from "../lib/tipos";
import { Cargando, Error } from "../componentes/Layout";

const CATEGORIA: Record<string, string> = {
  CERT_VIAJES: "Todos · Certificados",
  VIGENCIA_PD: "Extranjeros residentes permanentes",
};

export default function Inicio() {
  const { usuario } = useSesion();
  const [tramites, setTramites] = useState<Tramite[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => { api.get<Tramite[]>("/tramites").then(setTramites).catch(setError); }, []);

  return (
    <>
      <section className="portada">
        <div className="contenedor">
          <h1>Certificados migratorios en línea</h1>
          <p>
            Solicite su Certificado de Viajes o de Vigencia de Permanencia Definitiva sin acudir a un cuartel:
            complete el formulario, adjunte sus documentos y siga el estado de su solicitud.
          </p>
          {!usuario && <Link className="boton boton--amarillo" to="/ingresar">Ingresar o crear cuenta</Link>}
        </div>
      </section>

      <div className="grilla grilla--principal">
        <section>
          <h2 className="titulo-seccion">Trámites</h2>
          <div className="tarjeta">
            <Error error={error} />
            {!tramites && !error && <Cargando />}
            {tramites?.map((t) => (
              <div className="tramite" key={t.codigo}>
                <div>
                  <div className="tramite__categoria">{CATEGORIA[t.codigo]}</div>
                  <div className="tramite__nombre">{t.nombre}</div>
                  <div className="suave" style={{ fontSize: 13 }}>{t.descripcion}</div>
                </div>
                <Link className="boton" to={`/solicitudes/nueva?tramite=${t.codigo}`}>Realizar</Link>
              </div>
            ))}
          </div>
        </section>

        <aside>
          <h2 className="titulo-seccion">Accesos directos</h2>
          <div className="grilla">
            <Link className="acceso" to="/mis-solicitudes">Consultar mis solicitudes</Link>
            <Link className="acceso" to="/verificar">Verificar un certificado</Link>
            <Link className="acceso" to="/backoffice">Ingreso de funcionarios</Link>
          </div>
        </aside>
      </div>

      <section style={{ marginTop: 28 }}>
        <h2 className="titulo-seccion">¿Cómo funciona?</h2>
        <div className="grilla grilla--3">
          {[
            ["1. Ingrese", "Cree una cuenta con su correo electrónico. La integración con Clave Única no está disponible en este prototipo."],
            ["2. Solicite", "Complete sus datos y adjunte los documentos requeridos en formato PDF, JPG o PNG (máximo 5 MB)."],
            ["3. Validación", "El sistema revisa duplicados y consulta registros (simulados). Si falta información, se le pedirá corregirla."],
            ["4. Emisión", "Un funcionario revisa y aprueba. Descargue su certificado con código de verificación."],
          ].map(([t, d]) => (
            <div className="tarjeta" key={t}><h3>{t}</h3><p className="suave" style={{ margin: 0 }}>{d}</p></div>
          ))}
        </div>
      </section>
    </>
  );
}
