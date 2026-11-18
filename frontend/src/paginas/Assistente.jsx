import { useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { falar } from "../componentes/Acessibilidade";
import { Aviso, Botao, Selo } from "../componentes/Basicos";
import { perguntar } from "../servicos/api";
import { salvarServico, usuarioAtual } from "../servicos/armazenamento";
import { SERVICOS } from "../servicos/catalogo";

const SUGESTOES = {
  cin: "O que preciso levar para tirar a identidade nova?",
  cnh: "Minha CNH vai vencer. Como faço para renovar?",
  cadunico: "Como atualizo meu Cadastro Único?",
  bpc: "Tenho 67 anos. Posso ter direito ao BPC?",
};

function idade(nascimento) {
  if (!nascimento) return null;
  const n = new Date(nascimento);
  const hoje = new Date();
  return hoje.getFullYear() - n.getFullYear() - (hoje < new Date(hoje.getFullYear(), n.getMonth(), n.getDate()) ? 1 : 0);
}

// Reconhecimento de voz do navegador (Chrome e Edge). Sem suporte, o botão não aparece.
const Reconhecimento = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export function Resposta({ resposta }) {
  return (
    <div>
      <p style={{ whiteSpace: "pre-line" }}>{resposta.resposta}</p>
      {resposta.documentos_necessarios?.length > 0 && (
        <>
          <h3>Documentos</h3>
          <ul>
            {resposta.documentos_necessarios.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </>
      )}
      <p className="linha">
        {resposta.gratuito === true && <Selo tipo="ok">Gratuito</Selo>}
        {resposta.gratuito === false && <Selo tipo="quase">Tem custo</Selo>}
        {resposta.encaminhar_para && <Selo tipo="quase">Procure: {resposta.encaminhar_para}</Selo>}
      </p>
      {resposta.fontes?.length > 0 && (
        <p className="pequeno">
          Fonte:{" "}
          {resposta.fontes.map((f, i) => (
            <span key={f}>
              {i > 0 && " · "}
              {resposta.urls?.[i] ? (
                <a href={resposta.urls[i]} target="_blank" rel="noreferrer">
                  {f}
                </a>
              ) : (
                f
              )}
            </span>
          ))}
        </p>
      )}
      <Botao variante="secundario" onClick={() => falar(resposta.resposta)}>
        Ouvir a resposta
      </Botao>
    </div>
  );
}

export default function Assistente() {
  const [parametros] = useSearchParams();
  const usuario = usuarioAtual();
  const servicoInicial = parametros.get("servico");
  const [perfil, setPerfil] = useState(() => ((idade(usuario?.nascimento) ?? 0) >= 60 ? "idoso" : "geral"));
  const [texto, setTexto] = useState(SUGESTOES[servicoInicial] || "");
  const [conversa, setConversa] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [ouvindo, setOuvindo] = useState(false);
  const [erro, setErro] = useState("");
  const campo = useRef(null);

  async function enviar(e) {
    e?.preventDefault();
    const pergunta = texto.trim();
    if (pergunta.length < 3) {
      setErro("Escreva a sua dúvida com pelo menos 3 letras.");
      return;
    }
    setErro("");
    setCarregando(true);
    setConversa((c) => [...c, { quem: "pessoa", texto: pergunta }]);
    setTexto("");
    try {
      const r = await perguntar(pergunta, perfil);
      setConversa((c) => [...c, { quem: "assistente", resposta: r }]);
      // Receber a lista oficial do assistente conta como orientação no Índice de Prontidão.
      if (usuario && SERVICOS[r.servico] && r.documentos_necessarios?.length) salvarServico(r.servico, { orientado: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
      campo.current?.focus();
    }
  }

  function ouvir() {
    const rec = new Reconhecimento();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    rec.onresult = (ev) => setTexto(ev.results[0][0].transcript);
    rec.onerror = () => setErro("Não consegui ouvir. Tente de novo ou escreva a pergunta.");
    rec.onend = () => setOuvindo(false);
    setOuvindo(true);
    rec.start();
  }

  return (
    <>
      <h1>Tirar dúvidas</h1>
      <p className="secundario">
        Pergunte sobre identidade nova, CNH, Cadastro Único ou BPC. A resposta vem de páginas oficiais, com a fonte.
        Não escreva seu CPF ou outros dados pessoais.
      </p>

      <div className="campo" style={{ maxWidth: 360 }}>
        <label htmlFor="perfil">Como prefere a resposta?</label>
        <select id="perfil" value={perfil} onChange={(e) => setPerfil(e.target.value)}>
          <option value="geral">Normal</option>
          <option value="idoso">Bem explicada, passo a passo</option>
          <option value="baixa_escolaridade">Com palavras bem simples</option>
        </select>
      </div>

      <div className="conversa" aria-live="polite">
        {conversa.map((m, i) =>
          m.quem === "pessoa" ? (
            <div key={i} className="balao balao--pessoa">
              <span className="visualmente-oculto">Você perguntou: </span>
              {m.texto}
            </div>
          ) : (
            <div key={i} className="balao balao--assistente">
              <span className="visualmente-oculto">Resposta: </span>
              <Resposta resposta={m.resposta} />
            </div>
          ),
        )}
        {carregando && <p className="secundario">Procurando nas fontes oficiais...</p>}
      </div>

      <form onSubmit={enviar} className="cartao">
        <div className="campo">
          <label htmlFor="pergunta">Sua pergunta</label>
          <textarea id="pergunta" ref={campo} rows={3} value={texto} onChange={(e) => setTexto(e.target.value)} />
        </div>
        <Aviso tipo="erro">{erro}</Aviso>
        <div className="linha">
          <Botao type="submit" disabled={carregando}>
            Perguntar
          </Botao>
          {Reconhecimento && (
            <Botao variante="secundario" onClick={ouvir} disabled={ouvindo || carregando}>
              {ouvindo ? "Ouvindo..." : "Falar a pergunta"}
            </Botao>
          )}
        </div>
      </form>
    </>
  );
}
