import { useState } from "react";
import { Botao, Selo } from "../componentes/Basicos";
import { removerServico, salvarServico, usuarioAtual } from "../servicos/armazenamento";
import { FAIXAS, LISTA_SERVICOS, SERVICOS, STATUS } from "../servicos/catalogo";

function CartaoServico({ registro, aoMudar }) {
  const servico = SERVICOS[registro.id];
  return (
    <li className="cartao">
      <h3>{servico.nome}</h3>
      <p className="linha">
        <Selo tipo={registro.status}>{STATUS[registro.status]}</Selo>
        {registro.indice != null && (
          <Selo tipo={registro.faixa}>
            Prontidão {registro.indice} · {FAIXAS[registro.faixa]}
          </Selo>
        )}
      </p>
      <div className="campo">
        <label htmlFor={`status-${registro.id}`}>Situação</label>
        <select
          id={`status-${registro.id}`}
          value={registro.status}
          onChange={(e) => aoMudar(salvarServico(registro.id, { status: e.target.value }))}
        >
          {Object.entries(STATUS).map(([valor, nome]) => (
            <option key={valor} value={valor}>
              {nome}
            </option>
          ))}
        </select>
      </div>
      <div className="linha">
        <Botao para={`/servico/${registro.id}`}>Ver o que levar</Botao>
        {servico.conferir && (
          <Botao variante="secundario" para={`/conferir?servico=${registro.id}`}>
            Conferir documentos
          </Botao>
        )}
        <Botao variante="secundario" onClick={() => aoMudar(removerServico(registro.id))} aria-label={`Remover ${servico.nome}`}>
          Remover
        </Botao>
      </div>
    </li>
  );
}

export default function MeusServicos() {
  const [usuario, setUsuario] = useState(usuarioAtual);
  const disponiveis = LISTA_SERVICOS.filter((s) => !usuario.servicos.some((r) => r.id === s.id));
  const primeiroNome = usuario.nome.split(" ")[0];

  return (
    <>
      <h1>Olá, {primeiroNome}!</h1>
      <p className="secundario">Aqui ficam os serviços que você quer resolver. A ideia é você ir uma vez só e voltar com tudo resolvido.</p>

      <h2>Meus serviços</h2>
      {usuario.servicos.length === 0 ? (
        <p>Você ainda não escolheu nenhum serviço. Escolha abaixo o que precisa resolver.</p>
      ) : (
        <ul className="limpa grade">
          {usuario.servicos.map((r) => (
            <CartaoServico key={r.id} registro={r} aoMudar={setUsuario} />
          ))}
        </ul>
      )}

      {disponiveis.length > 0 && (
        <>
          <h2>Adicionar um serviço</h2>
          <ul className="limpa linha">
            {disponiveis.map((s) => (
              <li key={s.id}>
                <Botao variante="secundario" onClick={() => setUsuario(salvarServico(s.id))}>
                  + {s.curto}
                </Botao>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
