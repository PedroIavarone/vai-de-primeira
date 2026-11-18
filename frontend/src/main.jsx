import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ProvedorAcessibilidade } from "./componentes/Acessibilidade";
import "./estilos/global.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <ProvedorAcessibilidade>
        <App />
      </ProvedorAcessibilidade>
    </BrowserRouter>
  </StrictMode>,
);
