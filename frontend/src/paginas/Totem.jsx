import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { falar, useAcessibilidade } from "../componentes/Acessibilidade";
import { Aviso } from "../componentes/Basicos";
import { perguntar } from "../servicos/api";
import { LISTA_SERVICOS } from "../servicos/catalogo";
import { Resposta } from "./Assistente";
import { useFila } from "./Fila";

// Unidade onde este totem está instalado (o mesmo id usado pelo ESP32 e pela API /fila).
const UNIDADE_DO_TOTEM = "centro";

const PERGUNTAS = {
  cin: "O que preciso levar para tirar a Carteira de Identidade Nacional?",
  cnh: "O que preciso para renovar a CNH?",
  cadunico: "O que preciso levar para atualizar o Cadastro Único?",
  bpc: "Quem tem direito ao BPC e como pedir?",
};

// Ícone e linha curta de cada botão (custo e onde, para a pessoa decidir antes de tocar).
const BOTOES = {
  cin: { icone: "🪪", titulo: "Identidade nova", linha: "CIN · grátis" },
  cnh: { icone: "🚗", titulo: "Renovar a CNH", linha: "tem custo · exame médico" },
  cadunico: { icone: "🏠", titulo: "Cadastro Único", linha: "grátis · no CRAS" },
  bpc: { icone: "🤝", titulo: "Entender o BPC", linha: "orientação · grátis" },
};

const hora = () => new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

// Modo totem: quiosque na entrada da unidade, sem o menu do site, sem login, com letra e botões grandes.
// Volta sozinho para o início depois de 90 s sem uso, para não deixar a resposta de uma pessoa para a próxima.
export default function Totem() {
  const { fila } = useFila(15000);
  const { contraste, escala, alternarContraste, mudarEscala } = useAcessibilidade();
  const navegar = useNavigate();
  const [resposta, setResposta] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [ajuda, setAjuda] = useState(false);
  const [erro, setErro] = useState("");
  const [agora, setAgora] = useState(hora);
  const segurar = useRef(null);

  useEffect(() => {
    const id = setInterval(() => setAgora(hora()), 15000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!resposta && !ajuda) return undefined;
    const id = setTimeout(() => {
      setResposta(null);
      setAjuda(false);
    }, 90000);
    return () => clearTimeout(id);
  }, [resposta, ajuda]);

  async function escolher(servicoId) {
    setErro("");
    setAjuda(false);
    setCarregando(true);
    setResposta(null);
    try {
      const r = await perguntar(PERGUNTAS[servicoId], "idoso");
      setResposta(r);
      falar(r.resposta);
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  }

  function pedirAjuda() {
    setAjuda(true);
    falar("Um atendente foi chamado e já vem até você.");
  }

  function ouvir() {
    falar(document.getElementById("conteudo")?.innerText);
  }

  function abrirLibras() {
    // O VLibras (index.html) cria o próprio botão; o totem só o aciona com um alvo grande.
    document.querySelector("[vw-access-button]")?.click();
  }

  // Saída do quiosque para o atendente: segurar o logo por 3 segundos.
  const comecarSaida = () => {
    segurar.current = setTimeout(() => navegar("/"), 3000);
  };
  const cancelarSaida = () => clearTimeout(segurar.current);

  const unidades = fila ? [...fila.unidades].sort((a, b) => a.espera_min - b.espera_min) : [];
  const daqui = fila?.unidades.find((u) => u.id === UNIDADE_DO_TOTEM);

  return (
    <div className="totem-tela">
      <header className="totem-topo">
        <button
          type="button"
          className="totem-logo"
          aria-label="Vai de Primeira"
          onPointerDown={comecarSaida}
          onPointerUp={cancelarSaida}
          onPointerLeave={cancelarSaida}
        >
          <img src="/icone.svg" alt="" />
        </button>
        <span className="totem-unidade">
          <b>{daqui?.nome || "Central de Atendimento"}</b>
          <span>Vai de Primeira · totem 1</span>
        </span>
        <span className="totem-acessos" role="group" aria-label="Acessibilidade">
          <button type="button" onClick={() => mudarEscala(escala >= 150 ? -50 : 10)} aria-label="Aumentar a letra">
            A+ Aumentar
          </button>
          <button type="button" onClick={alternarContraste} aria-pressed={contraste}>
            ◐ Contraste
          </button>
          <button type="button" onClick={ouvir}>
            🔊 Ouvir
          </button>
          <button type="button" onClick={abrirLibras}>
            🤟 Libras
          </button>
        </span>
        <span className="totem-hora" aria-label={`Agora são ${agora}`}>
          {agora}
        </span>
      </header>

      <main id="conteudo" tabIndex={-1} className="totem-conteudo">
        {resposta ? (
          <section className="totem-resposta" aria-label="Resposta">
            <Resposta resposta={resposta} />
            <button type="button" className="totem-voltar" onClick={() => setResposta(null)}>
              ← Voltar ao início
            </button>
          </section>
        ) : (
          <>
            <h1>Olá! O que você veio resolver hoje?</h1>
            <ul className="limpa totem-servicos">
              {LISTA_SERVICOS.map((s) => (
                <li key={s.id}>
                  <button type="button" className="totem-servico" onClick={() => escolher(s.id)} disabled={carregando}>
                    <span className="totem-icone" aria-hidden="true">
                      {BOTOES[s.id].icone}
                    </span>
                    <span>
                      <b>{BOTOES[s.id].titulo}</b>
                      <span>{BOTOES[s.id].linha}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            <button type="button" className="totem-ajuda" onClick={pedirAjuda}>
              <span className="totem-icone" aria-hidden="true">
                🙋
              </span>
              <span>
                <b>Preciso de ajuda</b>
                <span>Um atendente vem até você</span>
              </span>
              <span aria-hidden="true" className="totem-seta">
                →
              </span>
            </button>
          </>
        )}

        <Aviso tipo="ok">{ajuda ? "Um atendente foi chamado e já vem até você." : ""}</Aviso>
        <Aviso tipo="erro">{erro}</Aviso>
        {carregando && <p className="totem-carregando">Procurando a resposta…</p>}

        <h2>Espera agora nas unidades</h2>
        <ul className="limpa totem-fila">
          {unidades.map((u, i) => (
            <li key={u.id} className={`totem-unidade-fila${i === 0 ? " menor" : ""}`}>
              {i === 0 && <span className="totem-selo">Menor espera</span>}
              <b>
                {u.nome}
                {u.id === UNIDADE_DO_TOTEM ? " · aqui" : ""}
              </b>
              <span className="totem-espera">
                <b>{u.espera_min} min</b> {u.pessoas} pessoas{u.origem === "sensor" ? " · ao vivo" : ""}
              </span>
              <span className="totem-lotacao" aria-hidden="true">
                <span className={`lotacao-${u.status}`} style={{ width: `${Math.min(100, Math.max(6, (u.espera_min / 60) * 100))}%` }} />
              </span>
            </li>
          ))}
        </ul>
      </main>

      <footer className="totem-rodape">
        <span>Toque em uma opção para começar · a tela volta ao início após 90 s parada</span>
        <span>
          Atendente: segure o logo por 3 s para sair
          <Link to="/" className="visualmente-oculto">
            Sair do modo totem
          </Link>
        </span>
      </footer>
    </div>
  );
}
