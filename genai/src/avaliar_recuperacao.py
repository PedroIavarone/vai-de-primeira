"""Avaliação da recuperação (sem chamar o LLM).

Para cada pergunta no tema com gabarito, verifica se o que o agente envia ao modelo (os k trechos da
busca híbrida, cada um reduzido à janela de 1.400 caracteres mais parecida com a pergunta) contém os
termos esperados. Se o termo não chega ao modelo, a resposta certa só sairia da memória do LLM, que é
o que o RAG quer evitar.

Compara duas bases de conhecimento:
  - páginas oficiais extraídas (genai/fontes/texto/), a base da avaliação v2;
  - corpus do PLN + páginas oficiais complementares, a base atual.

Uso:  python src/avaliar_recuperacao.py   →  avaliacao/recuperacao.json
"""
import json
import unicodedata
from pathlib import Path

import base_conhecimento as bc
from agente import janela_relevante

RAIZ = Path(__file__).resolve().parents[1]


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.replace(" ", " ").replace(" ", " "))
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).lower().split())


def avaliar(base, perguntas, k):
    detalhes = []
    for p in perguntas:
        trechos = base.buscar(p["pergunta"], k=k, servico=p.get("servico"))
        contexto = norm(" ".join(janela_relevante(t["texto"], p["pergunta"]) for t in trechos))
        ok = all(any(norm(alt) in contexto for alt in grupo) for grupo in p["deve_conter"])
        detalhes.append({"id": p["id"], "pergunta": p["pergunta"], "termos_no_contexto": ok,
                         "fontes": sorted({t["fonte"] for t in trechos})})
    return detalhes


def main():
    perguntas = [p for p in json.loads((RAIZ / "avaliacao/perguntas.json").read_text(encoding="utf-8"))
                 if p["categoria"] == "no_tema" and p.get("deve_conter")]
    resultado = {}
    corpus_original = bc.CORPUS_PLN
    for nome, corpus in (("paginas_oficiais", RAIZ / "nao_existe.jsonl"), ("corpus_pln", corpus_original)):
        bc.CORPUS_PLN = corpus
        base = bc.BaseConhecimento(reconstruir=True)
        for k in (4, 6, 8):
            d = avaliar(base, perguntas, k)
            acertos = sum(x["termos_no_contexto"] for x in d)
            resultado[f"{nome}_k{k}"] = {"trechos_na_base": len(base.trechos), "k": k, "acertos": acertos,
                                         "total": len(d), "taxa": round(acertos / len(d), 3),
                                         "faltou": [x["id"] for x in d if not x["termos_no_contexto"]]}
            print(f"{nome:17} k={k}  {acertos}/{len(d)}  faltou: {resultado[f'{nome}_k{k}']['faltou']}")
    bc.CORPUS_PLN = corpus_original
    (RAIZ / "avaliacao" / "recuperacao.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
