import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { falar } from "../componentes/Acessibilidade";
import { Botao, Selo } from "../componentes/Basicos";
import { salvarServico, usuarioAtual } from "../servicos/armazenamento";
import { SERVICOS } from "../servicos/catalogo";
import NaoEncontrada from "./NaoEncontrada";

export default function Servico() {
  const { id } = useParams();
  const servico = SERVICOS[id];

  // Ver a lista oficial do que levar conta como "orientação" no Índice de Prontidão.
  useEffect(() => {
    if (servico && usuarioAtual()) salvarServico(id, { orientado: true });
  }, [id, servico]);

  if (!servico) return <NaoEncontrada />;

  const resumo = `${servico.nome}. O que levar: ${servico.levar.join("; ")}. Onde: ${servico.onde} ${servico.custo}`;

  return (
    <>
      <p>
        <Link to="/meus-servicos">← Meus serviços</Link>
      </p>
      <h1>{servico.nome}</h1>
      <p className="linha">
        <Selo tipo={servico.gratuito ? "ok" : "quase"}>{servico.gratuito ? "Gratuito" : "Tem custo"}</Selo>
        <span className="secundario">{servico.custo}</span>
      </p>

      {servico.regra && (
        <div className="aviso">
          <strong>Quem pode pedir:</strong> {servico.regra}
        </div>
      )}

      <div className="grade">
        <section className="cartao" aria-labelledby="levar">
          <h2 id="levar" style={{ marginTop: 0 }}>
            O que levar
          </h2>
          <ul>
            {servico.levar.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
        <section className="cartao" aria-labelledby="onde">
          <h2 id="onde" style={{ marginTop: 0 }}>
            Onde ir
          </h2>
          <p>{servico.onde}</p>
          <Link to="/fila">Ver a fila das unidades agora</Link>
        </section>
      </div>

      <div className="linha" style={{ margin: "1rem 0" }}>
        <Botao variante="secundario" onClick={() => falar(resumo)}>
          Ouvir este resumo
        </Botao>
        {servico.conferir && <Botao para={`/conferir?servico=${id}`}>Conferir meus documentos</Botao>}
        <Botao variante="secundario" para={`/assistente?servico=${id}`}>
          Tirar uma dúvida
        </Botao>
      </div>

      <section className="cartao" aria-labelledby="fontes">
        <h2 id="fontes" style={{ marginTop: 0 }}>
          Fontes oficiais
        </h2>
        <ul>
          {servico.fontes.map((f) => (
            <li key={f.url}>
              <a href={f.url} target="_blank" rel="noreferrer">
                {f.nome}
                <span className="visualmente-oculto"> (abre em outra aba)</span>
              </a>
            </li>
          ))}
        </ul>
        <p className="pequeno secundario">
          Desconfie de sites que cobram por serviços gratuitos. Os canais oficiais terminam em gov.br.
        </p>
      </section>
    </>
  );
}
