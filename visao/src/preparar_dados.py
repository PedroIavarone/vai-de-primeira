"""Prepara o MIDV-2020 (photo) para os dois modelos da Conferência por vídeo.

Saídas em visao/datasets/preparado/:
  manifesto.csv     uma linha por foto: tipo, número, celular, condição, cantos e conjunto
  deteccao/         dataset YOLO (1 classe: documento), imagens redimensionadas
  qualidade/        dataset de classificação: ok, borrado, reflexo, cortado

Divisão sem vazamento: cada foto do MIDV-2020 mostra um documento único. A divisão
treino/validação/teste é feita por documento, estratificada por tipo e condição de
captura, e todas as variações sintéticas de uma foto ficam no mesmo conjunto dela.

Uso:
  python src/preparar_dados.py --origem datasets/photo --destino datasets/preparado
"""
import argparse
import csv
import json
import logging
import random
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("preparar_dados")

# Condição de captura pelo número da foto (readme oficial do MIDV-2020).
CONDICOES = [
    (range(0, 10), "distorcao_projetiva", "iphone_xr"), (range(10, 20), "distorcao_projetiva", "samsung_s10"),
    (range(20, 25), "documentos_no_fundo", "iphone_xr"), (range(25, 30), "documentos_no_fundo", "samsung_s10"),
    (range(30, 35), "teclado_no_fundo", "iphone_xr"), (range(35, 40), "teclado_no_fundo", "samsung_s10"),
    (range(40, 45), "luz_natural_externa", "iphone_xr"), (range(45, 50), "luz_natural_externa", "samsung_s10"),
    (range(50, 55), "mesa_no_fundo", "iphone_xr"), (range(55, 60), "mesa_no_fundo", "samsung_s10"),
    (range(60, 65), "reflexo_de_luz", "iphone_xr"), (range(65, 70), "reflexo_de_luz", "samsung_s10"),
    (range(70, 80), "pouca_luz", "iphone_xr"), (range(80, 90), "pouca_luz", "samsung_s10"),
    (range(90, 95), "tecido_no_fundo", "iphone_xr"), (range(95, 100), "tecido_no_fundo", "samsung_s10"),
]
# Alvo 70/15/15. Como cada grupo (tipo, condição) tem 5 ou 10 fotos e precisa de pelo menos
# 1 foto em validação e 1 em teste, a divisão real fica em 640/180/180 (64/18/18).
PROPORCAO = {"treino": 0.70, "validacao": 0.15, "teste": 0.15}
LADO_MAX = 1024                 # redimensionamento das imagens do detector
TAM_QUALIDADE = (448, 288)      # recorte do documento (largura, altura)


def condicao_de(numero: int) -> tuple[str, str]:
    for faixa, condicao, celular in CONDICOES:
        if numero in faixa:
            return condicao, celular
    raise ValueError(f"número de foto fora do padrão: {numero}")


def ler_cantos(arquivo_json: Path) -> dict[str, np.ndarray]:
    """Lê as anotações (formato VIA) e devolve {nome_da_imagem: 4 cantos do documento}."""
    dados = json.loads(arquivo_json.read_text(encoding="utf-8"))
    meta = dados.get("_via_img_metadata", dados)
    cantos = {}
    for item in meta.values():
        for regiao in item.get("regions", []):
            atributos = regiao.get("region_attributes", {})
            forma = regiao.get("shape_attributes", {})
            if atributos.get("field_name") == "doc_quad" and "all_points_x" in forma:
                pts = np.array(list(zip(forma["all_points_x"], forma["all_points_y"])), dtype=np.float32)
                if len(pts) == 4:
                    cantos[item["filename"]] = pts
    return cantos


def dividir(registros: list[dict], semente: int) -> None:
    """Estratifica por (tipo, condição) e sorteia o conjunto de cada documento."""
    grupos: dict[tuple, list[dict]] = {}
    for r in registros:
        grupos.setdefault((r["tipo"], r["condicao"]), []).append(r)
    rng = random.Random(semente)
    for itens in grupos.values():
        rng.shuffle(itens)
        n = len(itens)
        n_val = max(1, round(n * PROPORCAO["validacao"]))
        n_teste = max(1, round(n * PROPORCAO["teste"]))
        for i, r in enumerate(itens):
            r["conjunto"] = "validacao" if i < n_val else "teste" if i < n_val + n_teste else "treino"


def redimensionar(img: np.ndarray, lado_max: int) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    escala = min(1.0, lado_max / max(h, w))
    if escala < 1.0:
        img = cv2.resize(img, (round(w * escala), round(h * escala)), interpolation=cv2.INTER_AREA)
    return img, escala


def recortar_caixa(img: np.ndarray, cantos: np.ndarray, rng: random.Random) -> np.ndarray:
    """Recorta a caixa retangular do documento, como o detector faz na hora do uso.

    Usa a caixa que envolve os 4 cantos, com margem aleatória de 0 a 8% em cada lado,
    para o classificador aprender com o mesmo tipo de recorte (com um pouco de fundo)
    que recebe do detector. Um documento retificado perfeito não representa o uso real.
    """
    h, w = img.shape[:2]
    x0, y0 = cantos.min(axis=0)
    x1, y1 = cantos.max(axis=0)
    bw, bh = x1 - x0, y1 - y0
    x0 = int(max(0, x0 - rng.uniform(0, 0.08) * bw))
    x1 = int(min(w, x1 + rng.uniform(0, 0.08) * bw))
    y0 = int(max(0, y0 - rng.uniform(0, 0.08) * bh))
    y1 = int(min(h, y1 + rng.uniform(0, 0.08) * bh))
    return cv2.resize(img[y0:y1, x0:x1], TAM_QUALIDADE, interpolation=cv2.INTER_AREA)


# ---------- degradações sintéticas (cada uma com intensidade sorteada) ----------
def borrar(img, rng):
    if rng.random() < 0.5:  # desfoque de movimento (mão tremendo)
        k = rng.choice([9, 13, 17, 21])
        kernel = np.zeros((k, k), np.float32)
        kernel[k // 2, :] = 1.0 / k
        centro = (k / 2 - 0.5, k / 2 - 0.5)
        kernel = cv2.warpAffine(kernel, cv2.getRotationMatrix2D(centro, rng.uniform(0, 180), 1.0), (k, k))
        return cv2.filter2D(img, -1, kernel / max(kernel.sum(), 1e-6))
    s = rng.uniform(2.5, 5.0)  # desfoque de foco
    return cv2.GaussianBlur(img, (0, 0), s)


def refletir(img, rng):
    h, w = img.shape[:2]
    mascara = np.zeros((h, w), np.float32)
    cx, cy = rng.uniform(0.15, 0.85) * w, rng.uniform(0.15, 0.85) * h
    eixos = (int(rng.uniform(0.12, 0.30) * w), int(rng.uniform(0.10, 0.25) * h))
    cv2.ellipse(mascara, (int(cx), int(cy)), eixos, rng.uniform(0, 180), 0, 360, 1.0, -1)
    mascara = cv2.GaussianBlur(mascara, (0, 0), rng.uniform(8, 18))
    intensidade = rng.uniform(0.75, 0.98)
    branco = np.full_like(img, 255, dtype=np.float32)
    saida = img.astype(np.float32) * (1 - mascara[..., None] * intensidade) + branco * mascara[..., None] * intensidade
    return np.clip(saida, 0, 255).astype(np.uint8)


def cortar(img, rng):
    h, w = img.shape[:2]
    saida = img.copy()
    lado = rng.choice(["esquerda", "direita", "topo", "base"])
    frac = rng.uniform(0.18, 0.40)
    fundo = tuple(int(v) for v in rng.choice([(40, 40, 40), (120, 110, 100), (200, 200, 200)]))
    if lado == "esquerda":
        saida[:, : int(w * frac)] = fundo
    elif lado == "direita":
        saida[:, w - int(w * frac):] = fundo
    elif lado == "topo":
        saida[: int(h * frac), :] = fundo
    else:
        saida[h - int(h * frac):, :] = fundo
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", type=Path, required=True, help="pasta extraída do photo.tar")
    ap.add_argument("--destino", type=Path, required=True)
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rng = random.Random(args.semente)

    registros = []
    for arq in sorted((args.origem / "annotations").glob("*.json")):
        tipo = arq.stem
        cantos = ler_cantos(arq)
        for nome, pts in sorted(cantos.items()):
            caminho = args.origem / "images" / tipo / nome
            if not caminho.exists():
                log.warning("imagem anotada não encontrada: %s", caminho)
                continue
            numero = int(Path(nome).stem)
            condicao, celular = condicao_de(numero)
            registros.append({"tipo": tipo, "numero": numero, "arquivo": str(caminho), "celular": celular,
                              "condicao": condicao, "cantos": pts})
    if not registros:
        raise SystemExit("Nenhuma anotação encontrada. Confira o caminho de --origem.")
    log.info("%d fotos anotadas em %d tipos de documento", len(registros), len({r["tipo"] for r in registros}))

    dividir(registros, args.semente)
    det, qual = args.destino / "deteccao", args.destino / "qualidade"
    for conj in PROPORCAO:
        (det / "images" / conj).mkdir(parents=True, exist_ok=True)
        (det / "labels" / conj).mkdir(parents=True, exist_ok=True)
        for classe in ("ok", "borrado", "reflexo", "cortado"):
            (qual / conj / classe).mkdir(parents=True, exist_ok=True)

    contagem = {}
    for r in registros:
        img = cv2.imread(r["arquivo"])
        if img is None:
            log.warning("não foi possível ler %s", r["arquivo"])
            continue
        base = f"{r['tipo']}_{r['numero']:02d}"
        conj = r["conjunto"]

        # Detector: imagem redimensionada + caixa a partir dos 4 cantos.
        menor, escala = redimensionar(img, LADO_MAX)
        h, w = menor.shape[:2]
        pts = r["cantos"] * escala
        x0, y0 = np.clip(pts.min(axis=0), 0, [w, h])
        x1, y1 = np.clip(pts.max(axis=0), 0, [w, h])
        cv2.imwrite(str(det / "images" / conj / f"{base}.jpg"), menor, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (det / "labels" / conj / f"{base}.txt").write_text(
            f"0 {(x0 + x1) / 2 / w:.6f} {(y0 + y1) / 2 / h:.6f} {(x1 - x0) / w:.6f} {(y1 - y0) / h:.6f}\n")

        # Qualidade: recorte da caixa do documento e variações, todas no mesmo conjunto da foto.
        doc = recortar_caixa(img, r["cantos"], rng)
        if r["condicao"] == "reflexo_de_luz":
            variacoes = {"reflexo": doc}  # reflexo real da captura; não vira exemplo "ok"
        else:
            variacoes = {"ok": doc, "reflexo": refletir(doc, rng)}
        variacoes["borrado"] = borrar(doc, rng)
        variacoes["cortado"] = cortar(doc, rng)
        for classe, im in variacoes.items():
            cv2.imwrite(str(qual / conj / classe / f"{base}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
            contagem[(conj, classe)] = contagem.get((conj, classe), 0) + 1

    with open(args.destino / "manifesto.csv", "w", newline="", encoding="utf-8") as f:
        campos = ["tipo", "numero", "celular", "condicao", "conjunto", "arquivo", "cantos"]
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for r in registros:
            escritor.writerow({**{k: r[k] for k in campos if k != "cantos"},
                               "cantos": json.dumps(np.round(r["cantos"], 1).tolist())})
    (det / "dados.yaml").write_text(
        f"path: {det.resolve()}\ntrain: images/treino\nval: images/validacao\ntest: images/teste\nnames:\n  0: documento\n")

    for conj in PROPORCAO:
        n = sum(1 for r in registros if r["conjunto"] == conj)
        classes = ", ".join(f"{c} {contagem.get((conj, c), 0)}" for c in ("ok", "borrado", "reflexo", "cortado"))
        log.info("%-9s %4d fotos · qualidade: %s", conj, n, classes)


if __name__ == "__main__":
    main()
