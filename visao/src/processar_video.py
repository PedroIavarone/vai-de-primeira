"""Processa um vídeo (ou uma sequência de imagens) quadro a quadro.

Para cada quadro: detector + qualidade, desenho das caixas e FPS medido na tela.
O tipo do documento (OCR) é lido uma vez a cada --intervalo-ocr quadros, porque é lento.
Gera um vídeo anotado e um CSV com o resultado de cada quadro.

Uso:
  python src/processar_video.py --entrada meu_video.mp4 --saida resultados/video_anotado.mp4
  python src/processar_video.py --sequencia datasets/preparado/deteccao/images/teste --saida resultados/sequencia_anotada.mp4
"""
import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np

from conferencia import Conferencia, desenhar

LARGURA, ALTURA = 1280, 720


def quadros_de_sequencia(pasta: Path, por_imagem: int, limite: int):
    """Simula o monitoramento contínuo: cada imagem fica alguns quadros na tela."""
    for arq in sorted(pasta.glob("*.jpg"))[:limite]:
        img = cv2.imread(str(arq))
        h, w = img.shape[:2]
        escala = min(LARGURA / w, ALTURA / h)
        tela = np.full((ALTURA, LARGURA, 3), 245, np.uint8)
        menor = cv2.resize(img, (int(w * escala), int(h * escala)))
        y, x = (ALTURA - menor.shape[0]) // 2, (LARGURA - menor.shape[1]) // 2
        tela[y:y + menor.shape[0], x:x + menor.shape[1]] = menor
        for _ in range(por_imagem):
            yield tela


def quadros_de_video(caminho: Path):
    cap = cv2.VideoCapture(str(caminho))
    if not cap.isOpened():
        raise SystemExit(f"não foi possível abrir o vídeo: {caminho}")
    while True:
        ok, quadro = cap.read()
        if not ok:
            break
        yield quadro
    cap.release()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--entrada", type=Path, help="arquivo de vídeo")
    grupo.add_argument("--sequencia", type=Path, help="pasta de imagens")
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--por-imagem", type=int, default=12, help="quadros por imagem na sequência")
    ap.add_argument("--limite", type=int, default=30, help="máximo de imagens da sequência")
    ap.add_argument("--fps-saida", type=float, default=24.0)
    ap.add_argument("--intervalo-ocr", type=int, default=0, help="0 desliga o OCR no vídeo")
    args = ap.parse_args()

    conf = Conferencia()
    conf.analisar(np.full((ALTURA, LARGURA, 3), 245, np.uint8), identificar_tipo=False)  # aquecimento
    fonte =(quadros_de_video(args.entrada) if args.entrada
             else quadros_de_sequencia(args.sequencia, args.por_imagem, args.limite))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    escritor, tempos, linhas = None, [], []
    tipo_atual = "desconhecido"

    for i, quadro in enumerate(fonte):
        inicio = time.perf_counter()
        usar_ocr = args.intervalo_ocr > 0 and i % args.intervalo_ocr == 0
        resultado = conf.analisar(quadro, identificar_tipo=usar_ocr)
        ms = (time.perf_counter() - inicio) * 1000
        tempos.append(ms)
        if usar_ocr and resultado["documentos"]:
            tipo_atual = resultado["documentos"][0]["tipo"]

        anotado = desenhar(quadro, resultado)
        fps = 1000 / (sum(tempos[-30:]) / len(tempos[-30:]))
        cv2.putText(anotado, f"{fps:.1f} FPS | {ms:.0f} ms", (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (31, 41, 51), 2)
        if escritor is None:
            h, w = anotado.shape[:2]
            escritor = cv2.VideoWriter(str(args.saida), cv2.VideoWriter_fourcc(*"mp4v"), args.fps_saida, (w, h))
        escritor.write(anotado)

        doc = resultado["documentos"][0] if resultado["documentos"] else None
        linhas.append({"quadro": i, "ms": round(ms, 1), "documentos": len(resultado["documentos"]),
                       "qualidade": doc["qualidade"] if doc else "", "confianca_qualidade": doc["confianca_qualidade"] if doc else "",
                       "tipo": tipo_atual if doc else ""})

    if escritor:
        escritor.release()
    with open(args.saida.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    media = sum(tempos) / len(tempos)
    print(f"{len(tempos)} quadros · {media:.1f} ms por quadro · {1000 / media:.1f} FPS · vídeo: {args.saida}")


if __name__ == "__main__":
    main()
