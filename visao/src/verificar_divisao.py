"""Confere a divisão gerada por preparar_dados.py.

Verifica que:
  1. nenhum documento (tipo + número) aparece em mais de um conjunto, no detector e na qualidade;
  2. toda condição de captura e todo tipo de documento aparecem nos três conjuntos;
  3. cada imagem do detector tem um rótulo YOLO válido.

Uso:
  python src/verificar_divisao.py --preparado datasets/preparado
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

CONJUNTOS = ("treino", "validacao", "teste")


def docs_por_conjunto(pastas: dict[str, list[Path]]) -> dict[str, set[str]]:
    return {c: {p.stem for pasta in ps for p in pasta.glob("*.jpg")} for c, ps in pastas.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparado", type=Path, required=True)
    args = ap.parse_args()
    raiz = args.preparado
    erros = []

    det = docs_por_conjunto({c: [raiz / "deteccao" / "images" / c] for c in CONJUNTOS})
    qual = docs_por_conjunto({c: list((raiz / "qualidade" / c).iterdir()) for c in CONJUNTOS})
    for nome, docs in (("detector", det), ("qualidade", qual)):
        for i, a in enumerate(CONJUNTOS):
            for b in CONJUNTOS[i + 1:]:
                comuns = docs[a] & docs[b]
                if comuns:
                    erros.append(f"{nome}: {len(comuns)} documentos em {a} e {b} (ex.: {sorted(comuns)[:3]})")
        print(f"{nome:9} " + " · ".join(f"{c} {len(docs[c])}" for c in CONJUNTOS) + " documentos")
    for c in CONJUNTOS:
        if det[c] != qual[c]:
            erros.append(f"{c}: documentos do detector e da qualidade não coincidem")

    for c in CONJUNTOS:
        for img in (raiz / "deteccao" / "images" / c).glob("*.jpg"):
            rotulo = raiz / "deteccao" / "labels" / c / f"{img.stem}.txt"
            partes = rotulo.read_text().split() if rotulo.exists() else []
            if len(partes) != 5 or not all(0.0 <= float(v) <= 1.0 for v in partes[1:]):
                erros.append(f"rótulo inválido: {rotulo}")

    cobertura = defaultdict(Counter)
    with open(raiz / "manifesto.csv", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            cobertura[("condicao", linha["condicao"])][linha["conjunto"]] += 1
            cobertura[("tipo", linha["tipo"])][linha["conjunto"]] += 1
    for (eixo, valor), cont in sorted(cobertura.items()):
        faltando = [c for c in CONJUNTOS if cont[c] == 0]
        if faltando:
            erros.append(f"{eixo} '{valor}' sem exemplos em: {', '.join(faltando)}")
    print(f"cobertura: {sum(1 for k in cobertura if k[0] == 'condicao')} condições e "
          f"{sum(1 for k in cobertura if k[0] == 'tipo')} tipos verificados nos três conjuntos")

    if erros:
        print("\nFALHOU:")
        print("\n".join(f"- {e}" for e in erros))
        sys.exit(1)
    print("\nOK: sem vazamento entre conjuntos e com cobertura completa.")


if __name__ == "__main__":
    main()
