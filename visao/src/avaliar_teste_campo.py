"""Teste de campo: o pipeline completo em imagens de documentos fictícios brasileiros.

As imagens de teste_campo/fotos/ têm documentos brasileiros fictícios (CIN, CNH e certidão) em
4 condições (ok, borrado, reflexo, cortado), rotuladas em teste_campo/rotulos.csv. Este é o primeiro
contato do modelo, treinado com documentos estrangeiros do MIDV-2020, com o layout brasileiro.

Para cada imagem, mede:
  - detecção: maior confiança do detector (mesmo abaixo do limiar) e se passou do limiar de 0,50;
  - qualidade: classe prevista para o recorte do documento detectado;
  - tipo: documento identificado pelo OCR.

Uso (dentro de visao/src):
  python avaliar_teste_campo.py                                   # detector em uso (modelos/detector.pt)
  python avaliar_teste_campo.py --detector ../runs/detector_br/weights/best.pt --nome teste_campo_ajustado
Saídas: ../resultados/<nome>.json e ../resultados/<nome>.md
"""
import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path

import cv2

from conferencia import CONF_DETECTOR, TAM_DETECTOR, Conferencia

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "teste_campo"
SAIDA = RAIZ / "resultados"


def maior_confianca(conf: Conferencia, imagem) -> tuple[float, list[int] | None]:
    r = conf.detector.predict(imagem, imgsz=TAM_DETECTOR, conf=0.01, device=conf.dispositivo, verbose=False)[0]
    if not len(r.boxes):
        return 0.0, None
    i = int(r.boxes.conf.argmax())
    return float(r.boxes.conf[i]), list(map(int, r.boxes.xyxy[i].tolist()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", type=Path, help="pesos de outro detector, para comparar")
    ap.add_argument("--nome", default="teste_campo")
    args = ap.parse_args()
    conf = Conferencia()
    if args.detector:
        from ultralytics import YOLO
        conf.detector = YOLO(str(args.detector))
    with open(PASTA / "rotulos.csv", encoding="utf-8") as f:
        rotulos = list(csv.DictReader(f))

    linhas = []
    for item in rotulos:
        imagem = cv2.imread(str(PASTA / "fotos" / item["arquivo"]))
        conf_max, caixa = maior_confianca(conf, imagem)
        inicio = time.perf_counter()
        r = conf.analisar(imagem)
        ms = round((time.perf_counter() - inicio) * 1000)
        doc = r["documentos"][0] if r["documentos"] else None
        # Qualidade também no recorte de maior confiança, mesmo abaixo do limiar, para separar
        # o erro do detector do erro do classificador.
        qualidade_recorte = None
        if caixa:
            x0, y0, x1, y1 = caixa
            qualidade_recorte = conf.avaliar_qualidade(imagem[y0:y1, x0:x1])[0]
        linhas.append({
            "arquivo": item["arquivo"],
            "tipo_real": item["tipo"],
            "condicao_real": item["condicao"],
            "conf_detector_max": round(conf_max, 3),
            "detectado": doc is not None,
            "qualidade_prevista": doc["qualidade"] if doc else None,
            "qualidade_no_melhor_recorte": qualidade_recorte,
            "tipo_previsto": doc["tipo"] if doc else None,
            "latencia_ms": ms,
        })
        print(f"{item['arquivo']:28} conf {conf_max:.3f}  qualidade {qualidade_recorte}  tipo {doc['tipo'] if doc else '-'}")

    n = len(linhas)
    detectados = [l for l in linhas if l["detectado"]]
    resumo = {
        "imagens": n,
        "limiar_detector": CONF_DETECTOR,
        "detectados_no_limiar": len(detectados),
        "conf_detector_mediana": sorted(l["conf_detector_max"] for l in linhas)[n // 2],
        "qualidade_certa_entre_detectados": sum(l["qualidade_prevista"] == l["condicao_real"] for l in detectados),
        "qualidade_certa_no_melhor_recorte": sum(l["qualidade_no_melhor_recorte"] == l["condicao_real"] for l in linhas),
        "tipo_certo_entre_detectados": sum(l["tipo_previsto"] == l["tipo_real"] for l in detectados),
        "qualidade_prevista_no_melhor_recorte": dict(Counter(l["qualidade_no_melhor_recorte"] for l in linhas)),
    }
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / f"{args.nome}.json").write_text(json.dumps({"resumo": resumo, "imagens": linhas}, indent=2, ensure_ascii=False),
                                             encoding="utf-8")
    with open(SAIDA / f"{args.nome}.md", "w", encoding="utf-8") as f:
        f.write("# Teste de campo com documentos fictícios brasileiros\n\n")
        f.write(f"{n} imagens · limiar do detector {CONF_DETECTOR}\n\n")
        f.write("| Arquivo | Tipo | Condição | Confiança do detector | Detectado | Qualidade (melhor recorte) | Tipo (OCR) |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for l in linhas:
            f.write(f"| {l['arquivo']} | {l['tipo_real']} | {l['condicao_real']} | {l['conf_detector_max']:.3f} | "
                    f"{'sim' if l['detectado'] else 'não'} | {l['qualidade_no_melhor_recorte'] or '-'} | {l['tipo_previsto'] or '-'} |\n")
        f.write("\n```json\n" + json.dumps(resumo, indent=2, ensure_ascii=False) + "\n```\n")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
