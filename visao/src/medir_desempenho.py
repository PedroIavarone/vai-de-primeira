"""Mede latência por imagem e FPS da Conferência por vídeo.

Separa o tempo de cada etapa (detector, qualidade, OCR) em imagens do conjunto de teste
e grava visao/resultados/desempenho.json com hardware, resolução e estatísticas.

Uso:
  python src/medir_desempenho.py --imagens 100
"""
import argparse
import json
import platform
import statistics
import subprocess
import time
from pathlib import Path

import cv2

from conferencia import TAM_DETECTOR, TAM_QUALIDADE, Conferencia

RAIZ = Path(__file__).resolve().parents[1]


def hardware() -> str:
    try:
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 2**30
        return f"{chip}, {mem:.0f} GB RAM, {platform.system()} {platform.release()}"
    except Exception:
        return platform.platform()


def resumo(ms: list[float]) -> dict:
    ordenado = sorted(ms)
    return {"media_ms": round(statistics.mean(ms), 1), "mediana_ms": round(statistics.median(ms), 1),
            "p95_ms": round(ordenado[int(len(ordenado) * 0.95) - 1], 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imagens", type=int, default=100)
    ap.add_argument("--ocr", type=int, default=20, help="quantas imagens medir com OCR (é bem mais lento)")
    args = ap.parse_args()

    conf = Conferencia()
    arquivos = sorted((RAIZ / "datasets/preparado/deteccao/images/teste").glob("*.jpg"))[: args.imagens]
    imagens = [cv2.imread(str(a)) for a in arquivos]
    for img in imagens[:5]:  # aquecimento: a primeira inferência inclui compilação e cache
        conf.analisar(img, identificar_tipo=False)

    t_det, t_qual, t_total = [], [], []
    for img in imagens:
        inicio = time.perf_counter()
        caixas = conf.detectar(img)
        t1 = time.perf_counter()
        for (x0, y0, x1, y1), _ in caixas:
            conf.avaliar_qualidade(img[y0:y1, x0:x1])
        t2 = time.perf_counter()
        t_det.append((t1 - inicio) * 1000)
        t_qual.append((t2 - t1) * 1000)
        t_total.append((t2 - inicio) * 1000)

    t_ocr = []
    primeira = conf.detectar(imagens[0])
    if primeira:  # aquecimento do OCR: a primeira chamada carrega o modelo de leitura
        x0, y0, x1, y1 = primeira[0][0]
        conf.identificar_tipo(imagens[0][y0:y1, x0:x1])
    for img in imagens[: args.ocr]:
        caixas = conf.detectar(img)
        if caixas:
            x0, y0, x1, y1 = caixas[0][0]
            inicio = time.perf_counter()
            conf.identificar_tipo(img[y0:y1, x0:x1])
            t_ocr.append((time.perf_counter() - inicio) * 1000)

    h, w = imagens[0].shape[:2]
    saida = {
        "hardware": hardware(),
        "dispositivo_inferencia": conf.dispositivo,
        "imagens_medidas": len(imagens),
        "resolucao_entrada_px": f"{w}x{h} (redimensionada para {TAM_DETECTOR} px no detector e {TAM_QUALIDADE} px na qualidade)",
        "detector": resumo(t_det),
        "qualidade": resumo(t_qual),
        "modo_video_detector_mais_qualidade": {**resumo(t_total), "fps": round(1000 / statistics.mean(t_total), 1)},
        "ocr_tipo_documento_cpu": resumo(t_ocr) if t_ocr else None,
        "observacao": "No modo vídeo o OCR roda só uma vez por documento, não em todo quadro.",
    }
    (RAIZ / "resultados" / "desempenho.json").write_text(json.dumps(saida, indent=2, ensure_ascii=False))
    print(json.dumps(saida, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
