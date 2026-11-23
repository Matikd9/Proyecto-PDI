import { StrictMode, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./estilos.css";
import { cargarConfig } from "./lib/config";
import { ProveedorSesion } from "./lib/auth";
import { Layout, Protegida } from "./componentes/Layout";
import Inicio from "./paginas/Inicio";
import Ingresar from "./paginas/Ingresar";
import Verificar from "./paginas/Verificar";
import FormSolicitud from "./paginas/FormSolicitud";
import MisSolicitudes from "./paginas/MisSolicitudes";
import DetalleSolicitud from "./paginas/DetalleSolicitud";
import Backoffice from "./paginas/Backoffice";
import BackofficeDetalle from "./paginas/BackofficeDetalle";
import Admin from "./paginas/Admin";

const ciudadano = (el: ReactElement) => <Protegida rol="ciudadano">{el}</Protegida>;
const funcionario = (el: ReactElement) => <Protegida rol="funcionario">{el}</Protegida>;

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Inicio /> },
      { path: "/ingresar", element: <Ingresar /> },
      { path: "/verificar/:codigo?", element: <Verificar /> },
      { path: "/solicitudes/nueva", element: ciudadano(<FormSolicitud />) },
      { path: "/solicitudes/:id/editar", element: ciudadano(<FormSolicitud />) },
      { path: "/solicitudes/:id", element: ciudadano(<DetalleSolicitud />) },
      { path: "/mis-solicitudes", element: ciudadano(<MisSolicitudes />) },
      { path: "/backoffice", element: funcionario(<Backoffice />) },
      { path: "/backoffice/:id", element: funcionario(<BackofficeDetalle />) },
      { path: "/admin", element: <Protegida rol="administrador"><Admin /></Protegida> },
      { path: "*", element: <p>Página no encontrada.</p> },
    ],
  },
]);

cargarConfig()
  .then(() =>
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <ProveedorSesion><RouterProvider router={router} /></ProveedorSesion>
      </StrictMode>,
    ),
  )
  .catch((e) => { document.getElementById("root")!.textContent = String(e); });
