import { Navigate, Route, Routes } from "react-router-dom";
import { Layout, RotaProtegida } from "./componentes/Layout";
import Assistente from "./paginas/Assistente";
import Conferir from "./paginas/Conferir";
import { Cadastro } from "./paginas/Entrada";
import Login from "./paginas/Login";
import Fila from "./paginas/Fila";
import MeusServicos from "./paginas/MeusServicos";
import NaoEncontrada from "./paginas/NaoEncontrada";
import PorQue from "./paginas/PorQue";
import Privacidade from "./paginas/Privacidade";
import Servico from "./paginas/Servico";
import Totem from "./paginas/Totem";

const protegida = (elemento) => <RotaProtegida>{elemento}</RotaProtegida>;

export default function App() {
  return (
    <Routes>
      {/* O totem é um quiosque: ocupa a tela toda, sem o cabeçalho e o menu do site. */}
      <Route path="totem" element={<Totem />} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/meus-servicos" replace />} />
        <Route path="login" element={<Login />} />
        <Route path="cadastro" element={<Cadastro />} />
        <Route path="meus-servicos" element={protegida(<MeusServicos />)} />
        <Route path="servico/:id" element={<Servico />} />
        <Route path="conferir" element={protegida(<Conferir />)} />
        <Route path="fila" element={<Fila />} />
        <Route path="assistente" element={<Assistente />} />
        <Route path="privacidade" element={protegida(<Privacidade />)} />
        <Route path="por-que" element={<PorQue />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
