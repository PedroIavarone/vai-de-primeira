"""Validação do robô com casos rotulados.

O arquivo de casos tem as mesmas colunas da base de cidadãos e mais a coluna "esperado", com os
avisos certos para cada pessoa separados por ";" (ex.: "cnh_vencendo;bpc_possivel"), "nenhum" ou
"revisao" (linha com dado inválido que deve ir para revisão humana).

Uso:
  python validar.py                                   # validacao/casos.csv com data 2026-11-12
  python validar.py --casos outro.csv --data 2026-11-12

Saídas: validacao/resultado.json e validacao/resultado.md (acertos, erros por caso e por tipo).
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from main import executar

PASTA = Path(__file__).resolve().parent
TIPOS = ["cnh_vencendo", "cnh_vencida", "cadunico_desatualizado", "nascimento", "bpc_possivel", "link_suspeito", "revisao"]


def _rotulos(texto: str) -> set[str]:
    texto = (texto or "").strip().lower()
    return set() if texto in ("", "nenhum") else {t.strip() for t in texto.split(";") if t.strip()}


def validar(casos: Path, hoje: date) -> dict:
    with open(casos, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    esperado = {l["id"]: _rotulos(l.get("esperado", "")) for l in linhas}
    with tempfile.TemporaryDirectory() as tmp:  # banco limpo: a idempotência não interfere na validação
        r = executar(base=casos, hoje=hoje, usar_llm=False, enviar=False, banco=Path(tmp) / "validacao.sqlite")
    obtido = {i: set(t) for i, t in r["decisoes"].items()}
    for i in r["ids_revisao_leitura"]:
        obtido[i] = {"revisao"}

    detalhes, por_tipo = [], {t: Counter() for t in TIPOS}
    for i, certo in esperado.items():
        robo = obtido.get(i, set())
        for t in TIPOS:
            if t in certo and t in robo:
                por_tipo[t]["vp"] += 1
            elif t in robo:
                por_tipo[t]["fp"] += 1
            elif t in certo:
                por_tipo[t]["fn"] += 1
        detalhes.append({"id": i, "esperado": sorted(certo) or ["nenhum"], "robo": sorted(robo) or ["nenhum"],
                         "acertou": certo == robo})
    acertos = sum(d["acertou"] for d in detalhes)
    metricas = {}
    for t, c in por_tipo.items():
        if c["vp"] + c["fp"] + c["fn"]:
            precisao = c["vp"] / (c["vp"] + c["fp"]) if c["vp"] + c["fp"] else 0.0
            recall = c["vp"] / (c["vp"] + c["fn"]) if c["vp"] + c["fn"] else 0.0
            metricas[t] = {"precisao": round(precisao, 3), "recall": round(recall, 3), "vp": c["vp"], "fp": c["fp"], "fn": c["fn"]}
    resultado = {"casos": len(detalhes), "acertos": acertos, "acuracia": round(acertos / len(detalhes), 3),
                 "data_referencia": hoje.isoformat(), "por_tipo": metricas,
                 "erros": [d for d in detalhes if not d["acertou"]]}

    saida = PASTA / "validacao"
    saida.mkdir(exist_ok=True)
    (saida / "resultado.json").write_text(json.dumps({**resultado, "detalhes": detalhes}, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    md = [f"# Resultado da validação", "",
          f"**{acertos} de {len(detalhes)} casos corretos ({resultado['acuracia']:.1%})**, data de referência {hoje:%d/%m/%Y}.",
          "Um caso só conta como certo se o conjunto de avisos for exatamente o esperado.", "",
          "| Aviso | Precisão | Recall | Acertos | Avisos a mais | Avisos faltando |", "|---|---|---|---|---|---|"]
    md += [f"| {t} | {m['precisao']:.0%} | {m['recall']:.0%} | {m['vp']} | {m['fp']} | {m['fn']} |" for t, m in metricas.items()]
    md += ["", "## Casos com erro", ""]
    md += ([f"- **{e['id']}**: esperado {', '.join(e['esperado'])}; robô {', '.join(e['robo'])}" for e in resultado["erros"]]
           or ["Nenhum."])
    (saida / "resultado.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return resultado


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--casos", type=Path, default=PASTA / "validacao" / "casos.csv")
    p.add_argument("--data", type=date.fromisoformat, default=date(2026, 11, 12))
    a = p.parse_args()
    r = validar(a.casos, a.data)
    print(f"\n{r['acertos']}/{r['casos']} casos corretos ({r['acuracia']:.1%})")
    for e in r["erros"]:
        print(f"  erro {e['id']}: esperado {e['esperado']}, robô {e['robo']}")
