"""Treina o detector de documentos (YOLO) e avalia no conjunto de teste.

Parte de um YOLO pré-treinado (transfer learning) e ajusta para uma classe: documento.
As métricas de teste (precisão, recall, mAP@0.5 e mAP@0.5:0.95) são gravadas em
visao/resultados/detector_metricas.json.

Uso:
  python src/treinar_detector.py --dados datasets/preparado/deteccao/dados.yaml
  python src/treinar_detector.py --dados ... --epocas 1 --nome teste_rapido   # checagem rápida
"""
import argparse
import json
import logging
import platform
import time
from pathlib import Path

import torch
from ultralytics import YOLO

log = logging.getLogger("treinar_detector")
RAIZ = Path(__file__).resolve().parents[1]


def dispositivo() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "0"
    return "cpu"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--modelo", default="yolo11n.pt", help="pesos pré-treinados de partida")
    ap.add_argument("--epocas", type=int, default=50)
    ap.add_argument("--tamanho", type=int, default=640)
    ap.add_argument("--lote", type=int, default=16)
    ap.add_argument("--nome", default="detector")
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    disp = dispositivo()
    log.info("dispositivo: %s · modelo base: %s · %d épocas · %d px", disp, args.modelo, args.epocas, args.tamanho)
    modelo = YOLO(args.modelo)
    inicio = time.time()
    modelo.train(
        data=str(args.dados), epochs=args.epocas, imgsz=args.tamanho, batch=args.lote,
        device=disp, seed=args.semente, deterministic=True, patience=15,
        project=str(RAIZ / "runs"), name=args.nome, exist_ok=True, plots=True, verbose=False,
    )
    duracao = time.time() - inicio

    melhor = RAIZ / "runs" / args.nome / "weights" / "best.pt"
    avaliacao = YOLO(str(melhor)).val(data=str(args.dados), split="test", imgsz=args.tamanho,
                                      device=disp, plots=True, project=str(RAIZ / "runs"),
                                      name=f"{args.nome}_teste", exist_ok=True, verbose=False)
    caixa = avaliacao.box
    metricas = {
        "modelo_base": args.modelo,
        "epocas_configuradas": args.epocas,
        "tamanho_imagem_px": args.tamanho,
        "tempo_treino_min": round(duracao / 60, 1),
        "hardware": f"{platform.machine()} · {platform.platform()} · dispositivo {disp}",
        "teste": {
            "precisao": round(float(caixa.mp), 4),
            "recall": round(float(caixa.mr), 4),
            "mAP50": round(float(caixa.map50), 4),
            "mAP50_95": round(float(caixa.map), 4),
        },
        "pesos": str(melhor.relative_to(RAIZ)),
    }
    saida = RAIZ / "resultados" / f"{args.nome}_metricas.json"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    log.info("teste: %s", metricas["teste"])
    log.info("métricas gravadas em %s", saida.relative_to(RAIZ))


if __name__ == "__main__":
    main()
