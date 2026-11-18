import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { falar } from "../componentes/Acessibilidade";
import { Aviso, Botao } from "../componentes/Basicos";
import { perguntar } from "../servicos/api";
import { LISTA_SERVICOS } from "../servicos/catalogo";
import { Resposta } from "./Assistente";
import { ListaUnidades, useFila } from "./Fila";

const PERGUNTAS = {
  cin: "O que preciso levar para tirar a Carteira de Identidade Nacional?",
  cnh: "O que preciso para renovar a CNH?",
  cadunico: "O que preciso levar para atualizar o Cadastro Único?",
  bpc: "Quem tem direito ao BPC e como pedir?",
};

// Modo totem: tela da entrada da unidade, sem login, com letra e botões grandes.
// Volta sozinho para o início depois de 90 s sem uso, para não deixar a resposta de uma pessoa para a próxima.
export default function Totem() {
  const { fila } = useFila(15000);
  const [resposta, setResposta] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [ajuda, setAjuda] = useState(false);
  const [erro, setErro] = useState("");

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

  return (
    <div className="totem">
      <h1>Bem-vindo! O que você veio resolver?</h1>
      <ul className="limpa grade">
        {LISTA_SERVICOS.map((s) => (
          <li key={s.id}>
            <Botao grande onClick={() => escolher(s.id)} disabled={carregando}>
              {s.curto}
            </Botao>
          </li>
        ))}
      </ul>

      <div style={{ margin: "1.5rem 0" }}>
        <Botao grande variante="perigo" onClick={pedirAjuda}>
          Preciso de ajuda
        </Botao>
      </div>
      <Aviso tipo="ok">{ajuda ? "Um atendente foi chamado e já vem até você." : ""}</Aviso>
      <Aviso tipo="erro">{erro}</Aviso>
      {carregando && <p>Procurando a resposta...</p>}
      {resposta && (
        <section className="cartao" aria-label="Resposta">
          <Resposta resposta={resposta} />
          <p style={{ marginTop: "1rem" }}>
            <Botao variante="secundario" onClick={() => setResposta(null)}>
              Voltar ao início
            </Botao>
          </p>
        </section>
      )}

      <h2>Espera nas unidades</h2>
      {fila && <ListaUnidades fila={fila} />}
      <p className="pequeno">
        <Link to="/">Sair do modo totem</Link>
      </p>
    </div>
  );
}
