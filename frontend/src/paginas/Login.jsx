import { useId, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Aviso, Botao, CampoTexto, Selo } from "../componentes/Basicos";
import { entrar } from "../servicos/armazenamento";
import { mascararDigitacao } from "../servicos/cpf";
import { useFila } from "./Fila";

const NOMES_STATUS = { tranquila: "Tranquila", moderada: "Moderada", cheia: "Cheia" };

// O que a pessoa ganha ao entrar, antes de pedir o CPF.
const PROMESSAS = [
  { icone: "🔔", titulo: "Aviso antes do prazo", texto: "Por e-mail, antes de o documento vencer." },
  { icone: "📷", titulo: "Documentos conferidos pela câmera", texto: "Antes de sair de casa, não no balcão." },
  { icone: "✓", titulo: "Nota de 0 a 100", texto: "A chance de resolver na primeira ida." },
];

// Senha com o botão "Mostrar": diminui o erro de digitação de quem tem pouca prática.
function CampoSenha({ valor, aoMudar }) {
  const id = useId();
  const [visivel, setVisivel] = useState(false);
  return (
    <div className="campo">
      <label htmlFor={id}>Senha</label>
      <div className="campo-senha">
        <input id={id} type={visivel ? "text" : "password"} autoComplete="current-password" value={valor} onChange={aoMudar} required />
        <button type="button" onClick={() => setVisivel(!visivel)} aria-pressed={visivel} aria-controls={id}>
          {visivel ? "Esconder" : "Mostrar"}
        </button>
      </div>
    </div>
  );
}

export default function Login() {
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const navegar = useNavigate();
  const local = useLocation();
  const { fila } = useFila();
  const melhor = fila ? [...fila.unidades].sort((a, b) => a.espera_min - b.espera_min)[0] : null;

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      await entrar(cpf, senha);
      navegar(local.state?.voltarPara || "/meus-servicos", { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="entrar">
      <section className="entrar__promessa" aria-labelledby="promessa">
        <span className="entrar__servicos">Identidade · CNH · Cadastro Único · BPC</span>
        <h1 id="promessa">Vá uma vez só e volte com tudo resolvido.</h1>
        <ul className="limpa entrar__lista">
          {PROMESSAS.map((p) => (
            <li key={p.titulo}>
              <span className="entrar__icone" aria-hidden="true">
                {p.icone}
              </span>
              <span>
                <b>{p.titulo}</b>
                <span className="secundario">{p.texto}</span>
              </span>
            </li>
          ))}
        </ul>
        {melhor && (
          <p className="entrar__fila">
            <span className="ponto" aria-hidden="true" />
            Agora na <b>{melhor.nome}</b>: {melhor.espera_min} min de espera <Selo tipo={melhor.status}>{NOMES_STATUS[melhor.status]}</Selo>
          </p>
        )}
      </section>

      <form className="cartao entrar__form" onSubmit={enviar} noValidate>
        <h2>Entrar</h2>
        <p className="secundario">Veja seus serviços e se já pode ir.</p>
        <CampoTexto
          rotulo="CPF"
          inputMode="numeric"
          autoComplete="username"
          placeholder="000.000.000-00"
          value={cpf}
          onChange={(e) => setCpf(mascararDigitacao(e.target.value))}
          required
        />
        <CampoSenha valor={senha} aoMudar={(e) => setSenha(e.target.value)} />
        <Aviso tipo="erro">{erro}</Aviso>
        <Botao type="submit" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </Botao>
        <p className="entrar__ou">primeira vez aqui?</p>
        <Botao variante="secundario" para="/cadastro">
          Criar cadastro
        </Botao>
        <p className="pequeno secundario entrar__nota">🔒 Dados fictícios neste protótipo. As regras vêm de páginas oficiais, sempre citadas.</p>
      </form>
    </div>
  );
}
