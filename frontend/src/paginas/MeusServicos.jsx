import { useEffect, useRef, useState } from "react";
import { Botao } from "../componentes/Basicos";
import { removerServico, salvarServico, usuarioAtual } from "../servicos/armazenamento";
import { LISTA_SERVICOS, SERVICOS } from "../servicos/catalogo";
import { useFila } from "./Fila";

// Nome curto de cada faixa do Índice de Prontidão, como aparece no cartão.
const FAIXA_CURTA = { pronta: "Pronta para ir", quase: "Quase pronta", nao_pronta: "Ainda não está pronta" };

// Etapas do serviço em uma linha. "Pronta para ir" acende sozinha quando o índice chega à faixa pronta.
function etapaAtual(registro) {
  if (registro.status === "concluido") return 3;
  if (registro.faixa === "pronta") return 2;
  return 1;
}

// Anel com o índice de 0 a 100 (SVG simples, sem biblioteca).
function Anel({ indice, faixa }) {
  const r = 34;
  const volta = 2 * Math.PI * r;
  const cheio = indice == null ? 0 : (indice / 100) * volta;
  return (
    <svg className={`anel anel--${faixa || "vazio"}`} viewBox="0 0 84 84" role="img" aria-label={indice == null ? "Ainda sem índice" : `Índice ${indice} de 100`}>
      <circle cx="42" cy="42" r={r} className="anel-fundo" />
      <circle cx="42" cy="42" r={r} className="anel-valor" strokeDasharray={`${cheio} ${volta}`} transform="rotate(-90 42 42)" />
      <text x="42" y="50" textAnchor="middle">
        {indice ?? "–"}
      </text>
    </svg>
  );
}

// Menu ⋯ com as ações que não são a principal.
function MenuMais({ servico, aoRemover }) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef(null);
  useEffect(() => {
    if (!aberto) return undefined;
    const fechar = (e) => {
      if (e.key === "Escape" || (e.type === "mousedown" && !caixa.current?.contains(e.target))) setAberto(false);
    };
    document.addEventListener("mousedown", fechar);
    document.addEventListener("keydown", fechar);
    return () => {
      document.removeEventListener("mousedown", fechar);
      document.removeEventListener("keydown", fechar);
    };
  }, [aberto]);
  return (
    <div className="menu-mais" ref={caixa}>
      <button type="button" aria-expanded={aberto} aria-label={`Mais opções de ${servico.nome}`} onClick={() => setAberto(!aberto)}>
        ⋯
      </button>
      {aberto && (
        <div className="menu-mais__lista">
          <Botao variante="secundario" para={`/servico/${servico.id}`}>
            Ver o que levar
          </Botao>
          <Botao variante="secundario" onClick={aoRemover}>
            Remover este serviço
          </Botao>
        </div>
      )}
    </div>
  );
}

function CartaoServico({ registro, aoMudar, melhorUnidade }) {
  const servico = SERVICOS[registro.id];
  const etapa = etapaAtual(registro);
  const pronta = registro.faixa === "pronta";

  let texto;
  if (registro.status === "concluido") texto = "Serviço resolvido.";
  else if (registro.indice == null) texto = servico.conferir ? "Confira os documentos para saber se já pode ir." : "Veja o que levar e onde ir antes de sair de casa.";
  else if (pronta) texto = melhorUnidade ? `Melhor agora: ${melhorUnidade.nome}, ${melhorUnidade.espera_min} min de espera.` : "Documentos conferidos.";
  else texto = registro.falta || "Ainda falta algo para ir com segurança.";

  // Uma ação principal por cartão.
  const acao =
    servico.conferir && !pronta && registro.status !== "concluido"
      ? { para: `/conferir?servico=${registro.id}`, nome: registro.indice == null ? "Conferir documentos" : "Continuar a conferência" }
      : { para: `/servico/${registro.id}`, nome: pronta ? "Ver o que levar e onde ir" : "Ver o que levar" };

  return (
    <li className="cartao cartao-servico">
      <div className="cartao-servico__topo">
        <div>
          <h3>{servico.nome}</h3>
          <span className={`etiqueta ${servico.gratuito ? "etiqueta--gratis" : "etiqueta--custo"}`}>{servico.gratuito ? "Grátis" : "Tem custo"}</span>
        </div>
        <MenuMais servico={servico} aoRemover={() => aoMudar(removerServico(registro.id))} />
      </div>

      <div className="cartao-servico__indice">
        <Anel indice={registro.indice} faixa={registro.faixa} />
        <div>
          <p className={`faixa faixa--${registro.faixa || "vazio"}`}>{registro.indice == null ? "Ainda não conferido" : FAIXA_CURTA[registro.faixa]}</p>
          <p className="secundario">{texto}</p>
        </div>
      </div>

      <div className="etapas" role="group" aria-label={`Etapa de ${servico.nome}`}>
        <button type="button" aria-pressed={etapa === 1} className={etapa > 1 ? "feita" : ""} onClick={() => aoMudar(salvarServico(registro.id, { status: "em_andamento" }))}>
          {etapa > 1 ? "✓ " : "1 "}Preparando
        </button>
        <button type="button" aria-pressed={etapa === 2} className={etapa > 2 ? "feita" : ""} disabled title="Acende quando o Índice de Prontidão chega a pronta">
          {etapa > 2 ? "✓ " : "2 "}Pronta para ir
        </button>
        <button type="button" aria-pressed={etapa === 3} onClick={() => aoMudar(salvarServico(registro.id, { status: "concluido" }))}>
          3 Resolvido
        </button>
      </div>

      <Botao para={acao.para}>{acao.nome}</Botao>
    </li>
  );
}

export default function MeusServicos() {
  const [usuario, setUsuario] = useState(usuarioAtual);
  const { fila } = useFila();
  const disponiveis = LISTA_SERVICOS.filter((s) => !usuario.servicos.some((r) => r.id === s.id));
  const primeiroNome = usuario.nome.split(" ")[0];
  const melhorUnidade = fila ? [...fila.unidades].sort((a, b) => a.espera_min - b.espera_min)[0] : null;

  return (
    <>
      <h1>Olá, {primeiroNome}!</h1>
      <p className="secundario">Aqui ficam os serviços que você quer resolver. A ideia é você ir uma vez só e voltar com tudo resolvido.</p>

      <h2>Meus serviços</h2>
      {usuario.servicos.length === 0 ? (
        <p>Você ainda não escolheu nenhum serviço. Escolha abaixo o que precisa resolver.</p>
      ) : (
        <ul className="limpa grade-servicos">
          {usuario.servicos.map((r) => (
            <CartaoServico key={r.id} registro={r} aoMudar={setUsuario} melhorUnidade={melhorUnidade} />
          ))}
        </ul>
      )}

      {disponiveis.length > 0 && (
        <div className="adicionar">
          <span>Adicionar:</span>
          <ul className="limpa linha">
            {disponiveis.map((s) => (
              <li key={s.id}>
                <Botao variante="secundario" onClick={() => setUsuario(salvarServico(s.id))}>
                  + {s.curto}
                </Botao>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
