"""Treina o classificador de qualidade do documento (ok, borrado, reflexo, cortado).

Transfer learning a partir de um YOLO de classificação pré-treinado. No conjunto de
teste calcula precisão, recall e F1 por classe e a matriz de confusão, gravados em
visao/resultados/qualidade_metricas.json e visao/resultados/qualidade_matriz_confusao.png.

Uso:
  python src/treinar_qualidade.py --dados datasets/preparado/qualidade
"""
import argparse
import json
import logging
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from sklearn.metrics import classification_report, confusion_matrix
from ultralytics import YOLO

log = logging.getLogger("treinar_qualidade")
RAIZ = Path(__file__).resolve().parents[1]
CLASSES = ["ok", "borrado", "reflexo", "cortado"]


def dispositivo() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "0" if torch.cuda.is_available() else "cpu"


def matriz_png(matriz, caminho: Path):
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.imshow(matriz, cmap="Blues")
    ax.set_xticks(range(len(CLASSES)), CLASSES)
    ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("previsto")
    ax.set_ylabel("real")
    limite = matriz.max() / 2
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ax.text(j, i, int(matriz[i, j]), ha="center", va="center",
                    color="white" if matriz[i, j] > limite else "#1F2933")
    ax.set_title("Qualidade do documento · conjunto de teste")
    fig.tight_layout()
    fig.savefig(caminho, dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", type=Path, required=True, help="pasta com treino/, validacao/ e teste/")
    ap.add_argument("--modelo", default="yolo11n-cls.pt")
    ap.add_argument("--epocas", type=int, default=30)
    ap.add_argument("--tamanho", type=int, default=224)
    ap.add_argument("--nome", default="qualidade")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # O YOLO de classificação espera as pastas train/ e val/; criamos atalhos para as nossas.
    for nosso, deles in (("treino", "train"), ("validacao", "val"), ("teste", "test")):
        atalho = args.dados / deles
        if not atalho.exists():
            atalho.symlink_to(nosso, target_is_directory=True)

    disp = dispositivo()
    inicio = time.time()
    YOLO(args.modelo).train(
        data=str(args.dados), epochs=args.epocas, imgsz=args.tamanho, device=disp, seed=42,
        deterministic=True, patience=10, project=str(RAIZ / "runs"), name=args.nome,
        exist_ok=True, plots=True, verbose=False,
        fliplr=0.0, hsv_h=0.0,  # sem espelhar nem mudar matiz: o documento tem orientação e cores fixas
    )
    duracao = time.time() - inicio

    modelo = YOLO(str(RAIZ / "runs" / args.nome / "weights" / "best.pt"))
    nomes = modelo.names
    reais, previstos = [], []
    for classe in CLASSES:
        imagens = sorted((args.dados / "teste" / classe).glob("*.jpg"))
        for lote in range(0, len(imagens), 64):
            for r in modelo.predict([str(p) for p in imagens[lote:lote + 64]], imgsz=args.tamanho,
                                    device=disp, verbose=False):
                reais.append(classe)
                previstos.append(nomes[int(r.probs.top1)])

    relatorio = classification_report(reais, previstos, labels=CLASSES, output_dict=True, zero_division=0)
    matriz = confusion_matrix(reais, previstos, labels=CLASSES)
    resultados = RAIZ / "resultados"
    resultados.mkdir(exist_ok=True)
    matriz_png(matriz, resultados / "qualidade_matriz_confusao.png")
    metricas = {
        "modelo_base": args.modelo,
        "tamanho_imagem_px": args.tamanho,
        "tempo_treino_min": round(duracao / 60, 1),
        "dispositivo": disp,
        "teste": {
            "acuracia": round(relatorio["accuracy"], 4),
            "por_classe": {c: {k: round(relatorio[c][k], 4) for k in ("precision", "recall", "f1-score", "support")}
                           for c in CLASSES},
            "f1_macro": round(relatorio["macro avg"]["f1-score"], 4),
        },
        "matriz_confusao": {"linhas_reais_colunas_previstas": CLASSES, "valores": matriz.tolist()},
    }
    (resultados / f"{args.nome}_metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    log.info("acurácia %.3f · F1 macro %.3f", relatorio["accuracy"], relatorio["macro avg"]["f1-score"])


if __name__ == "__main__":
    main()
