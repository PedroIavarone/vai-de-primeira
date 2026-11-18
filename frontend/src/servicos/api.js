// Chamadas à API do Vai de Primeira (api/main.py). Contratos em docs/contratos.md.
export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function chamar(caminho, opcoes = {}) {
  const controle = new AbortController();
  const tempo = setTimeout(() => controle.abort(), opcoes.tempoLimite ?? 60000);
  try {
    const resposta = await fetch(`${API_URL}${caminho}`, { ...opcoes, signal: controle.signal });
    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail && typeof corpo.detail === "string" ? corpo.detail : `Erro ${resposta.status}`);
    }
    return await resposta.json();
  } catch (erro) {
    if (erro.name === "AbortError") throw new Error("A resposta demorou demais. Tente de novo.");
    if (erro instanceof TypeError) throw new Error("Não foi possível falar com o serviço agora. Confira a internet e tente de novo.");
    throw erro;
  } finally {
    clearTimeout(tempo);
  }
}

const json = (corpo) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(corpo),
});

export const buscarFila = () => chamar("/fila", { tempoLimite: 10000 });

export const perguntar = (pergunta, perfil) => chamar("/perguntar", { ...json({ pergunta, perfil }), tempoLimite: 90000 });

export function checarDocumento(arquivo) {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  return chamar("/checar-documento", { method: "POST", body: dados });
}

export const calcularProntidao = (pedido) => chamar("/prontidao", json(pedido));
