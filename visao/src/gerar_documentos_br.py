"""Gera fotos sintéticas de documentos brasileiros FICTÍCIOS para ajustar o detector.

Por que existe: o detector foi treinado só com documentos estrangeiros (MIDV-2020). No teste de campo
com documentos brasileiros fictícios (teste_campo/), ele achou o documento em apenas 1 de 20 imagens.
Aqui criamos modelos de CIN, CNH, certidão, CPF e comprovante de residência com dados inventados e
marca "ESPÉCIME", e os colocamos sobre fundos variados com perspectiva, rotação, luz, desfoque e
reflexo. A caixa de cada documento sai em formato YOLO.

Nenhum dado real: nomes, números e datas são sorteados de listas fictícias. Os fundos são
procedurais (ruído, gradiente, listras, ladrilhos e liso). Nenhum imita o fundo ondulado das imagens do
teste de campo, para que o teste continue medindo generalização.

Uso:
  python gerar_documentos_br.py --destino ../datasets/br_sintetico --treino 600 --validacao 150
"""
import argparse
import math
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTES = "/System/Library/Fonts/Supplemental"
NOMES = ["MARIA EXEMPLO DA SILVA", "JOSE FICTICIO SOUZA", "ANA TESTE PEREIRA", "JOAO MODELO SANTOS",
         "FRANCISCA ESPECIME LIMA", "PEDRO EXEMPLO COSTA", "LUCIA FICTICIA ROCHA", "CARLOS TESTE ALVES"]
CIDADES = ["EXEMPLO/SP", "MODELO/MG", "FICTICIA/BA", "TESTE/RS", "ESPECIME/PE"]


def fonte(tamanho, negrito=False):
    nome = "Arial Bold.ttf" if negrito else "Arial.ttf"
    return ImageFont.truetype(f"{FONTES}/{nome}", tamanho)


def data():
    return f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1940, 2010)}"


def numero(n):
    return "".join(random.choice("0123456789") for _ in range(n))


def campos(d: ImageDraw.ImageDraw, x, y, pares, larg, cor_rotulo=(90, 90, 90)):
    for rotulo, valor in pares:
        d.text((x, y), rotulo, fill=cor_rotulo, font=fonte(14))
        d.text((x, y + 17), valor, fill=(20, 20, 20), font=fonte(22, True))
        y += 52
    return y


def marca_especime(img):
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    d.text((img.width * 0.25, img.height * 0.35), "ESPÉCIME", fill=(200, 30, 30, 90), font=fonte(int(img.width / 7), True))
    camada = camada.rotate(random.uniform(-30, 30), center=(img.width / 2, img.height / 2))
    return Image.alpha_composite(img.convert("RGBA"), camada).convert("RGB")


def cartao(titulo, cor, linhas_extra):
    """Cartão no formato ID-1 (CIN, CNH, CPF): 856 x 540 px."""
    img = Image.new("RGB", (856, 540), tuple(random.randint(235, 250) for _ in range(3)))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 856, 95], fill=cor)
    d.text((30, 18), titulo, fill="white", font=fonte(34, True))
    d.text((30, 62), "REPÚBLICA FEDERATIVA DO BRASIL · DOCUMENTO FICTÍCIO", fill="white", font=fonte(16))
    d.rectangle([30, 125, 230, 385], fill=(205, 210, 215), outline=(150, 150, 150))
    d.ellipse([90, 160, 170, 240], fill=(160, 165, 170))
    d.rectangle([75, 250, 185, 380], fill=(160, 165, 170))
    campos(d, 260, 120, [("NOME", random.choice(NOMES)), ("CPF", f"{numero(3)}.{numero(3)}.{numero(3)}-{numero(2)}"),
                         ("DATA DE NASCIMENTO", data())] + linhas_extra, 560)
    d.text((30, 470), "<<ESPECIME<<" + numero(10) + "<<<<<<<<<<<<<<<", fill=(60, 60, 60), font=fonte(20))
    return marca_especime(img)


def cin():
    return cartao("CARTEIRA DE IDENTIDADE NACIONAL", random.choice([(31, 95, 173), (25, 80, 150), (40, 110, 190)]),
                  [("NATURALIDADE", random.choice(CIDADES))])


def cnh():
    return cartao("CARTEIRA NACIONAL DE HABILITAÇÃO", random.choice([(30, 110, 70), (20, 90, 60), (45, 120, 80)]),
                  [("CATEGORIA · VALIDADE", f"AB · {data()}")])


def cpf():
    return cartao("CADASTRO DE PESSOAS FÍSICAS", random.choice([(30, 60, 120), (60, 60, 60)]), [])


def folha(titulo, pares, cabecalho=None):
    """Folha A4 em retrato (certidão, comprovante): 620 x 877 px."""
    img = Image.new("RGB", (620, 877), tuple(random.randint(238, 252) for _ in range(3)))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 600, 857], outline=(120, 120, 120), width=2)
    if cabecalho:
        d.rectangle([20, 20, 600, 90], fill=cabecalho)
    d.text((50, 40), titulo, fill=(20, 20, 20) if not cabecalho else "white", font=fonte(28, True))
    y = 120
    for rotulo, valor in pares:
        d.text((50, y), rotulo, fill=(100, 100, 100), font=fonte(15))
        d.text((50, y + 18), valor, fill=(20, 20, 20), font=fonte(21, True))
        d.line([50, y + 46, 570, y + 46], fill=(200, 200, 200))
        y += 62
    d.text((50, 820), "DOCUMENTO FICTÍCIO · SEM VALOR LEGAL", fill=(170, 30, 30), font=fonte(16, True))
    return marca_especime(img)


def certidao():
    tipo = random.choice(["NASCIMENTO", "CASAMENTO"])
    return folha(f"CERTIDÃO DE {tipo}", [("NOME", random.choice(NOMES)), ("MATRÍCULA", numero(32)),
                                         ("DATA", data()), ("LOCAL", random.choice(CIDADES)),
                                         ("FILIAÇÃO", random.choice(NOMES)), ("FILIAÇÃO", random.choice(NOMES)),
                                         ("AVERBAÇÕES", "NADA CONSTA"), ("CARTÓRIO", "REGISTRO CIVIL EXEMPLO")])


def comprovante():
    return folha("CONTA DE ENERGIA", [("TITULAR", random.choice(NOMES)), ("ENDEREÇO", "RUA EXEMPLO, " + numero(3)),
                                      ("VENCIMENTO", data()), ("CONSUMO", numero(3) + " kWh"),
                                      ("VALOR", "R$ " + numero(3) + "," + numero(2))],
                 cabecalho=random.choice([(230, 120, 20), (20, 120, 180), (90, 90, 90)]))


MODELOS = [cin, cnh, cpf, certidao, comprovante]


# ---------------------------------------------------------------- fundos procedurais
def fundo(h, w):
    tipo = random.choice(["ruido", "gradiente", "listras", "ladrilho", "liso"])
    base = np.array([random.randint(30, 220) for _ in range(3)], np.float32)
    if tipo == "liso":
        img = np.ones((h, w, 3), np.float32) * base
    elif tipo == "ruido":
        pequeno = np.random.rand(h // 16 + 1, w // 16 + 1, 3).astype(np.float32)
        img = cv2.resize(pequeno, (w, h), interpolation=cv2.INTER_CUBIC) * 80 + base - 40
    elif tipo == "gradiente":
        g = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
        outra = np.array([random.randint(30, 220) for _ in range(3)], np.float32)
        img = np.ones((h, w, 3), np.float32) * (base * (1 - g) + outra * g)
    elif tipo == "listras":
        periodo = random.randint(20, 120)
        x = np.arange(w)[None, :, None]
        img = np.ones((h, w, 3), np.float32) * base + (((x // periodo) % 2) * 40 - 20)
    else:  # ladrilho: quadrados alternados com rejunte
        lado = random.randint(40, 160)
        yy, xx = np.mgrid[0:h, 0:w]
        img = np.ones((h, w, 3), np.float32) * base + ((((yy // lado) + (xx // lado)) % 2) * 35 - 17)[..., None]
        img[(yy % lado) < 3] *= 0.6
        img[(xx % lado) < 3] *= 0.6
    img += np.random.randn(h, w, 3).astype(np.float32) * random.uniform(2, 8)
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- composição
def compor(documento: Image.Image, largura=1024):
    altura = int(largura * random.choice([0.75, 0.5625, 1.333]))
    tela = fundo(altura, largura)
    doc = cv2.cvtColor(np.array(documento), cv2.COLOR_RGB2BGR)
    dh, dw = doc.shape[:2]
    escala = random.uniform(0.35, 0.85) * min(largura / dw, altura / dh)
    w, h = dw * escala, dh * escala
    cx = random.uniform(0.3, 0.7) * largura
    cy = random.uniform(0.3, 0.7) * altura
    ang = math.radians(random.uniform(-25, 25))
    cantos = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
    cantos = cantos @ rot.T + [cx, cy]
    cantos += np.random.uniform(-0.06, 0.06, cantos.shape) * [w, h]  # perspectiva
    # às vezes o documento sai um pouco da foto (cortado)
    if random.random() < 0.15:
        cantos += [random.choice([-1, 1]) * w * 0.3, 0]
    origem = np.float32([[0, 0], [dw, 0], [dw, dh], [0, dh]])
    m = cv2.getPerspectiveTransform(origem, cantos.astype(np.float32))
    warp = cv2.warpPerspective(doc, m, (largura, altura))
    mascara = cv2.warpPerspective(np.ones((dh, dw), np.uint8) * 255, m, (largura, altura))
    # sombra suave
    sombra = cv2.GaussianBlur(mascara, (0, 0), 12)
    sombra = np.roll(sombra, (8, 8), axis=(0, 1)).astype(np.float32) / 255 * 0.35
    tela = (tela * (1 - sombra[..., None])).astype(np.uint8)
    tela[mascara > 0] = warp[mascara > 0]

    # luz, reflexo e desfoque
    tela = cv2.convertScaleAbs(tela, alpha=random.uniform(0.6, 1.25), beta=random.uniform(-30, 25))
    if random.random() < 0.3:
        gx, gy = random.uniform(0, largura), random.uniform(0, altura)
        yy, xx = np.mgrid[0:altura, 0:largura]
        brilho = np.exp(-(((xx - gx) ** 2) + ((yy - gy) ** 2)) / (2 * (random.uniform(40, 160) ** 2)))
        tela = np.clip(tela + brilho[..., None] * random.uniform(120, 220), 0, 255).astype(np.uint8)
    if random.random() < 0.25:
        k = random.choice([5, 9, 13])
        tela = cv2.GaussianBlur(tela, (k, k), 0)
    if random.random() < 0.5:
        _, enc = cv2.imencode(".jpg", tela, [cv2.IMWRITE_JPEG_QUALITY, random.randint(45, 90)])
        tela = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    x0, y0 = np.clip(cantos.min(0), 0, [largura, altura])
    x1, y1 = np.clip(cantos.max(0), 0, [largura, altura])
    caixa = ((x0 + x1) / 2 / largura, (y0 + y1) / 2 / altura, (x1 - x0) / largura, (y1 - y0) / altura)
    return tela, caixa


def gerar(destino: Path, conjunto: str, quantidade: int):
    (destino / "images" / conjunto).mkdir(parents=True, exist_ok=True)
    (destino / "labels" / conjunto).mkdir(parents=True, exist_ok=True)
    for i in range(quantidade):
        modelo = MODELOS[i % len(MODELOS)]
        img, (cx, cy, w, h) = compor(modelo(), largura=random.choice([1024, 800, 640]))
        nome = f"br_{conjunto}_{i:04d}"
        cv2.imwrite(str(destino / "images" / conjunto / f"{nome}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (destino / "labels" / conjunto / f"{nome}.txt").write_text(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", type=Path, default=Path(__file__).resolve().parents[1] / "datasets" / "br_sintetico")
    ap.add_argument("--treino", type=int, default=600)
    ap.add_argument("--validacao", type=int, default=150)
    ap.add_argument("--semente", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.semente)
    np.random.seed(a.semente)
    gerar(a.destino, "treino", a.treino)
    gerar(a.destino, "validacao", a.validacao)
    print(f"{a.treino} + {a.validacao} imagens em {a.destino}")
