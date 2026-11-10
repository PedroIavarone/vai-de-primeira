"""Avaliação de ponta a ponta nas fotos reais do conjunto de teste.

Cada foto passa pelo mesmo caminho do uso real: detector → recorte da caixa →
classificador de qualidade. O rótulo esperado vem da condição de captura do MIDV-2020:
fotos da condição "reflexo de luz" devem sair como reflexo; as demais, como ok.
Grava visao/resultados/ponta_a_ponta.json com o acerto geral e por condição.

Uso:
  python src/avaliar_ponta_a_ponta.py
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from conferencia import Conferencia

RAIZ = Path(__file__).resolve().parents[1]


def main():
    conf = Conferencia()
    linhas = [r for r in csv.DictReader(open(RAIZ / "datasets/preparado/manifesto.csv", encoding="utf-8"))
              if r["conjunto"] == "teste"]
    total, sem_doc = Counter(), 0
    por_condicao = defaultdict(Counter)
    confusoes = Counter()
    for r in linhas:
        nome = f"{r['tipo']}_{int(r['numero']):02d}"
        resultado = conf.analisar_arquivo(RAIZ / "datasets/preparado/deteccao/images/teste" / f"{nome}.jpg",
                                          identificar_tipo=False)
        esperado = "reflexo" if r["condicao"] == "reflexo_de_luz" else "ok"
        if not resultado["documentos"]:
            sem_doc += 1
            por_condicao[r["condicao"]]["erro"] += 1
            continue
        previsto = resultado["documentos"][0]["qualidade"]
        certo = previsto == esperado
        total["acerto" if certo else "erro"] += 1
        por_condicao[r["condicao"]]["acerto" if certo else "erro"] += 1
        if not certo:
            confusoes[f"{esperado} → {previsto}"] += 1

    n = len(linhas)
    saida = {
        "fotos_teste": n,
        "acerto_geral": round(total["acerto"] / n, 4),
        "sem_documento_detectado": sem_doc,
        "confusoes": dict(confusoes.most_common()),
        "por_condicao": {c: {"acerto": round(v["acerto"] / (v["acerto"] + v["erro"]), 4),
                             "fotos": v["acerto"] + v["erro"]} for c, v in sorted(por_condicao.items())},
    }
    destino = RAIZ / "resultados" / "ponta_a_ponta.json"
    destino.write_text(json.dumps(saida, indent=2, ensure_ascii=False))
    print(f"acerto geral: {saida['acerto_geral']:.1%} ({total['acerto']}/{n}) · sem documento: {sem_doc}")
    for c, v in saida["por_condicao"].items():
        print(f"  {c:22} {v['acerto']:.0%} de {v['fotos']}")
    print("confusões:", saida["confusoes"] or "nenhuma")


if __name__ == "__main__":
    main()
