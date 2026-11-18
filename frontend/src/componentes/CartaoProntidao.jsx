import { FAIXAS } from "../servicos/catalogo";

// Índice de Prontidão: chance de resolver o serviço na primeira ida (0 a 100).
export default function CartaoProntidao({ resultado }) {
  if (!resultado) return null;
  const { indice, faixa, componentes, pendencias } = resultado;
  return (
    <section className={`prontidao prontidao--${faixa}`} aria-labelledby="titulo-prontidao" aria-live="polite">
      <h2 id="titulo-prontidao" style={{ marginTop: 0 }}>
        Índice de Prontidão
      </h2>
      <p className="linha" style={{ marginBottom: 0 }}>
        <span className="prontidao__numero">{indice}</span>
        <span>
          de 100 · <strong>{FAIXAS[faixa]}</strong>
        </span>
      </p>
      <div
        className="prontidao__barra"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={indice}
        aria-label="Índice de Prontidão"
      >
        <div className="prontidao__preenchido" style={{ width: `${indice}%` }} />
      </div>
      <p className="pequeno secundario">
        Documentos {componentes.documentos} de 60 · Fila {componentes.fila} de 25 · Orientação {componentes.orientacao} de 15
      </p>
      {pendencias.length > 0 ? (
        <>
          <h3>O que falta para ir com segurança</h3>
          <ul>
            {pendencias.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </>
      ) : (
        <p>
          <strong>Tudo certo. Você pode ir: a chance de resolver na primeira ida é alta.</strong>
        </p>
      )}
    </section>
  );
}
