"""Conferência de documentos: detector → recorte → qualidade → tipo (OCR).

Uso em código:
    from conferencia import Conferencia
    conf = Conferencia()
    resultado = conf.analisar(imagem_bgr)          # imagem do OpenCV
    resultado = conf.analisar_arquivo("foto.jpg")

Saída no formato de POST /checar-documento (docs/contratos.md), com dois campos extras
por documento: "caixa" [x0, y0, x1, y1] em pixels e "confianca_qualidade".

Limiares (justificativa no README do módulo):
  CONF_DETECTOR = 0.50   abaixo disso a caixa é descartada
  CONF_QUALIDADE = 0.60  abaixo disso a orientação pede uma nova foto, sem afirmar o defeito
"""
import logging
import re
import time
import unicodedata
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

log = logging.getLogger("conferencia")
RAIZ = Path(__file__).resolve().parents[1]
MODELOS = RAIZ / "modelos"

CONF_DETECTOR = 0.50
CONF_QUALIDADE = 0.60
TAM_DETECTOR = 640
TAM_QUALIDADE = 224
RECORTE = (448, 288)
MAX_DOCUMENTOS = 4

DICAS = {
    "ok": None,
    "borrado": "A foto ficou tremida. Apoie o celular e tire de novo.",
    "reflexo": "Tem reflexo no papel. Incline um pouco ou fuja da luz direta.",
    "cortado": "Uma parte do documento ficou fora da foto. Afaste um pouco o celular.",
}
DICA_INCERTA = "Não deu para conferir com segurança. Tire outra foto em um lugar bem iluminado."

# Palavras-chave para identificar documentos brasileiros pelo texto (sem acento, maiúsculas).
PALAVRAS_TIPO = [
    ("cnh", ["HABILITACAO", "CARTEIRA NACIONAL DE HABILITACAO", "PERMISSAO PARA DIRIGIR"]),
    ("cin", ["CARTEIRA DE IDENTIDADE", "REGISTRO GERAL", "IDENTIDADE NACIONAL"]),
    ("certidao", ["CERTIDAO DE NASCIMENTO", "CERTIDAO DE CASAMENTO", "CERTIDAO", "REGISTRO CIVIL"]),
    ("cpf", ["CADASTRO DE PESSOAS FISICAS", "CADASTRO DE PESSOA FISICA"]),
    ("comprovante_residencia", ["FATURA", "CONTA DE ENERGIA", "CONTA DE AGUA", "VENCIMENTO", "CONSUMO"]),
]


def _normalizar(texto: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.upper().split())


_CPF_NO_TEXTO = re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\b")


def tipo_por_texto(texto: str) -> str:
    alvo = _normalizar(texto)
    for tipo, palavras in PALAVRAS_TIPO:
        if any(p in alvo for p in palavras):
            return tipo
    return "desconhecido"


def _peso(nome: str) -> Path:
    """Usa visao/modelos/<nome>.pt; se ainda não existir, o último treino em runs/."""
    preferido = MODELOS / f"{nome}.pt"
    if preferido.exists():
        return preferido
    reserva = RAIZ / "runs" / nome / "weights" / "best.pt"
    if reserva.exists():
        return reserva
    raise FileNotFoundError(f"pesos de '{nome}' não encontrados em {preferido} nem em {reserva}")


class Conferencia:
    def __init__(self, dispositivo: str | None = None):
        self.dispositivo = dispositivo or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.detector = YOLO(str(_peso("detector")))
        self.qualidade = YOLO(str(_peso("qualidade")))
        self._ocr = None
        log.info("conferência carregada (%s)", self.dispositivo)

    # ---------- etapas ----------
    def detectar(self, imagem: np.ndarray) -> list[tuple[list[int], float]]:
        r = self.detector.predict(imagem, imgsz=TAM_DETECTOR, conf=CONF_DETECTOR,
                                  device=self.dispositivo, verbose=False)[0]
        caixas = [(list(map(int, b.xyxy[0].tolist())), float(b.conf[0])) for b in r.boxes]
        return sorted(caixas, key=lambda c: -c[1])[:MAX_DOCUMENTOS]

    def avaliar_qualidade(self, recorte: np.ndarray) -> tuple[str, float]:
        r = self.qualidade.predict(cv2.resize(recorte, RECORTE), imgsz=TAM_QUALIDADE,
                                   device=self.dispositivo, verbose=False)[0]
        return self.qualidade.names[int(r.probs.top1)], float(r.probs.top1conf)

    def identificar_tipo(self, recorte: np.ndarray) -> str:
        return self.ler_documento(recorte)[0]

    def ler_documento(self, recorte: np.ndarray) -> tuple[str, bool]:
        """Tipo do documento pelo OCR e se um número de CPF aparece impresso nele (ex.: certidões novas)."""
        if self._ocr is None:
            try:
                import easyocr
                self._ocr = easyocr.Reader(["pt"], gpu=False, verbose=False)
            except Exception as erro:  # OCR é opcional: sem ele o tipo fica "desconhecido"
                log.warning("OCR indisponível (%s); tipo = desconhecido", erro)
                self._ocr = False
        if not self._ocr:
            return "desconhecido", False
        texto = " ".join(self._ocr.readtext(recorte, detail=0, paragraph=True))
        return tipo_por_texto(texto), bool(_CPF_NO_TEXTO.search(texto))

    # ---------- uso ----------
    def analisar(self, imagem: np.ndarray, identificar_tipo: bool = True) -> dict:
        inicio = time.perf_counter()
        documentos = []
        for (x0, y0, x1, y1), conf_det in self.detectar(imagem):
            recorte = imagem[y0:y1, x0:x1]
            if recorte.size == 0:
                continue
            qualidade, conf_q = self.avaliar_qualidade(recorte)
            dica = DICAS[qualidade] if conf_q >= CONF_QUALIDADE else DICA_INCERTA
            tipo, tem_cpf = self.ler_documento(recorte) if identificar_tipo else ("desconhecido", False)
            documentos.append({
                "tipo": tipo,
                "cpf_visivel": tem_cpf,
                "confianca": round(conf_det, 3),
                "qualidade": qualidade,
                "confianca_qualidade": round(conf_q, 3),
                "dica": dica,
                "caixa": [x0, y0, x1, y1],
            })
        return {"documentos": documentos, "latencia_ms": round((time.perf_counter() - inicio) * 1000)}

    def analisar_arquivo(self, caminho, identificar_tipo: bool = True) -> dict:
        imagem = cv2.imread(str(caminho))
        if imagem is None:
            raise ValueError(f"não foi possível ler a imagem: {caminho}")
        return self.analisar(imagem, identificar_tipo)

    def analisar_bytes(self, conteudo: bytes, identificar_tipo: bool = True) -> dict:
        imagem = cv2.imdecode(np.frombuffer(conteudo, np.uint8), cv2.IMREAD_COLOR)
        if imagem is None:
            raise ValueError("o arquivo enviado não é uma imagem válida")
        return self.analisar(imagem, identificar_tipo)


COR = {"ok": (79, 127, 30), "borrado": (8, 74, 168), "reflexo": (8, 74, 168), "cortado": (8, 74, 168)}


def desenhar(imagem: np.ndarray, resultado: dict) -> np.ndarray:
    """Desenha caixas e rótulos (usado no vídeo e nas figuras do relatório)."""
    saida = imagem.copy()
    esp = max(2, imagem.shape[1] // 400)
    for d in resultado["documentos"]:
        x0, y0, x1, y1 = d["caixa"]
        cor = COR[d["qualidade"]]
        cv2.rectangle(saida, (x0, y0), (x1, y1), cor, esp)
        rotulo = f"{d['qualidade']} {d['confianca_qualidade']:.0%} | doc {d['confianca']:.0%}"
        escala = max(0.5, imagem.shape[1] / 1400)
        (tw, th), _ = cv2.getTextSize(rotulo, cv2.FONT_HERSHEY_SIMPLEX, escala, esp)
        cv2.rectangle(saida, (x0, max(0, y0 - th - 12)), (x0 + tw + 10, y0), cor, -1)
        cv2.putText(saida, rotulo, (x0 + 5, y0 - 6), cv2.FONT_HERSHEY_SIMPLEX, escala, (255, 255, 255), esp)
    return saida
