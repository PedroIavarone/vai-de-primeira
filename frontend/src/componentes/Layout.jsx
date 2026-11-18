import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { sair, usuarioAtual } from "../servicos/armazenamento";
import { BarraAcessibilidade } from "./Acessibilidade";

export function Cabecalho() {
  const usuario = usuarioAtual();
  const navegar = useNavigate();
  return (
    <header className="cabecalho">
      <div className="cabecalho__topo">
        <Link to="/" className="marca">
          <img src="/icone.svg" alt="" />
          <span>
            <strong>Vai de Primeira</strong>
            <small>resolvido na primeira ida</small>
          </span>
        </Link>
        <BarraAcessibilidade />
      </div>
      <nav className="menu" aria-label="Principal">
        <div className="menu__itens">
        {usuario ? (
          <>
            <NavLink to="/meus-servicos">Meus serviços</NavLink>
            <NavLink to="/conferir">Conferir documentos</NavLink>
            <NavLink to="/fila">Fila agora</NavLink>
            <NavLink to="/assistente">Tirar dúvidas</NavLink>
            <NavLink to="/privacidade">Meus dados</NavLink>
            <NavLink to="/por-que">Por que existimos</NavLink>
            <a
              className="menu__sair"
              href="/login"
              onClick={(e) => {
                e.preventDefault();
                sair();
                navegar("/login");
              }}
            >
              Sair
            </a>
          </>
        ) : (
          <>
            <NavLink to="/login">Entrar</NavLink>
            <NavLink to="/cadastro">Criar cadastro</NavLink>
            <NavLink to="/fila">Fila agora</NavLink>
            <NavLink to="/por-que">Por que existimos</NavLink>
          </>
        )}
        </div>
      </nav>
    </header>
  );
}

export function Rodape() {
  return (
    <footer className="rodape">
      <p>
        Vai de Primeira · protótipo com dados fictícios. As regras de cada serviço vêm de páginas oficiais do
        governo, sempre citadas.
      </p>
      <p>
        Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
      </p>
    </footer>
  );
}

export function Layout() {
  return (
    <>
      <a className="pular-conteudo" href="#conteudo">
        Pular para o conteúdo
      </a>
      <Cabecalho />
      <main id="conteudo" tabIndex={-1} className="pagina">
        <Outlet />
      </main>
      <Rodape />
    </>
  );
}

export function RotaProtegida({ children }) {
  const local = useLocation();
  if (!usuarioAtual()) return <Navigate to="/login" replace state={{ voltarPara: local.pathname }} />;
  return children;
}
