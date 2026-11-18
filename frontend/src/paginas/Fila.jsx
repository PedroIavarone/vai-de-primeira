import { useEffect, useState } from "react";
import { Aviso, Botao, Selo } from "../componentes/Basicos";
import { buscarFila } from "../servicos/api";

const NOMES_STATUS = { tranquila: "Tranquila", moderada: "Moderada", cheia: "Cheia" };

export function useFila(intervaloMs = 30000) {
  const [fila, setFila] = useState(null);
  const [erro, setErro] = useState("");
  const atualizar = () =>
    buscarFila()
      .then((f) => {
        setFila(f);
        setErro("");
      })
      .catch((e) => setErro(e.message));
  useEffect(() => {
    atualizar();
    const id = setInterval(atualizar, intervaloMs);
    return () => clearInterval(id);
  }, [intervaloMs]);
  return { fila, erro, atualizar };
}

export function ListaUnidades({ fila }) {
  const unidades = [...fila.unidades].sort((a, b) => a.espera_min - b.espera_min);
  return (
    <ul className="limpa grade">
      {unidades.map((u, i) => (
        <li key={u.id} className="cartao">
          <h3>
            {u.nome} {i === 0 && <span className="visualmente-oculto">(menor espera)</span>}
          </h3>
          <p className="linha" style={{ marginBottom: "0.5rem" }}>
            <span style={{ fontSize: "2rem", fontWeight: 700 }}>{u.espera_min} min</span>
            <Selo tipo={u.status}>{NOMES_STATUS[u.status]}</Selo>
          </p>
          <p className="pequeno secundario" style={{ margin: 0 }}>
            {u.pessoas} pessoas ·{" "}
            {u.origem === "sensor" ? `contagem real do totem (lida às ${u.lido_em?.slice(11, 16)})` : "estimativa"}
          </p>
        </li>
      ))}
    </ul>
  );
}

export default function Fila() {
  const { fila, erro, atualizar } = useFila();
  return (
    <>
      <h1>Fila agora</h1>
      <p className="secundario">
        Veja a espera antes de sair de casa. Se uma unidade estiver cheia, escolha outra ou outro horário.
      </p>
      <Aviso tipo="erro">{erro}</Aviso>
      {fila && <ListaUnidades fila={fila} />}
      <p className="linha">
        <Botao variante="secundario" onClick={atualizar}>
          Atualizar
        </Botao>
        {fila && <span className="pequeno secundario">Atualizado às {fila.atualizado_em.slice(11, 16)}. Atualiza sozinho a cada 30 segundos.</span>}
      </p>
    </>
  );
}
