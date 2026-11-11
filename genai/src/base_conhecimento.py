"""Base de conhecimento do Assistente da Jornada (recuperação híbrida).

Fonte dos trechos, em ordem de preferência:
  1. pln/saida/corpus_texto.jsonl  (corpus limpo e anonimizado do módulo de PLN)
  2. genai/fontes/texto/*.txt      (páginas oficiais extraídas, base provisória)

Recuperação: busca semântica (multilingual-e5-small + FAISS) combinada com busca por
palavra (BM25) por Reciprocal Rank Fusion. A semântica encontra paráfrases ("RG novo"
→ "Carteira de Identidade Nacional"); o BM25 garante termos exatos (siglas, valores).

Uso:
  from base_conhecimento import BaseConhecimento
  base = BaseConhecimento()
  base.buscar("o que levar para tirar a identidade nova", k=4)
"""
import json
import logging
import pickle
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

log = logging.getLogger("base_conhecimento")
RAIZ = Path(__file__).resolve().parents[2]
CORPUS_PLN = RAIZ / "pln" / "saida" / "corpus_texto.jsonl"
FONTES = RAIZ / "genai" / "fontes" / "texto"
INDICE = RAIZ / "genai" / "indice"
MODELO_EMBEDDINGS = "intfloat/multilingual-e5-small"
PALAVRAS_POR_TRECHO = 220
SOBREPOSICAO = 40
RRF_K = 60


@dataclass
class Trecho:
    texto: str
    fonte: str
    servico: str
    url: str = ""


def _tokens(texto: str) -> list[str]:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", sem_acento)


def _dividir(texto: str) -> list[str]:
    """Junta parágrafos até ~220 palavras, com sobreposição para não cortar a ideia ao meio."""
    paragrafos = [p.strip() for p in re.split(r"\n(?=## )|\n{2,}", texto) if p.strip()]
    trechos, atual = [], []
    for p in paragrafos:
        palavras = p.split()
        if atual and len(atual) + len(palavras) > PALAVRAS_POR_TRECHO:
            trechos.append(" ".join(atual))
            atual = atual[-SOBREPOSICAO:]
        atual.extend(palavras)
        while len(atual) > PALAVRAS_POR_TRECHO * 1.5:  # parágrafo enorme: corta em janelas
            trechos.append(" ".join(atual[:PALAVRAS_POR_TRECHO]))
            atual = atual[PALAVRAS_POR_TRECHO - SOBREPOSICAO:]
    if atual:
        trechos.append(" ".join(atual))
    return trechos


def carregar_trechos() -> tuple[list[Trecho], str]:
    if CORPUS_PLN.exists():
        trechos = []
        for linha in CORPUS_PLN.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                item = json.loads(linha)
                fonte = item.get("fonte", "")
                trechos.append(Trecho(item["text"], fonte, item.get("servico", ""), item.get("url", "")))
        return trechos, "corpus do PLN"
    trechos = []
    for arq in sorted(FONTES.glob("*.txt")):
        bruto = arq.read_text(encoding="utf-8")
        cab, _, corpo = bruto.partition("\n\n")
        meta = dict(l.split(": ", 1) for l in cab.splitlines() if ": " in l)
        for t in _dividir(corpo):
            trechos.append(Trecho(t, arq.stem, meta.get("Serviço", ""), meta.get("URL", "")))
    return trechos, "páginas oficiais (provisório)"


class BaseConhecimento:
    def __init__(self, reconstruir: bool = False):
        from sentence_transformers import SentenceTransformer

        self.trechos, self.origem = carregar_trechos()
        if not self.trechos:
            raise RuntimeError("nenhum trecho encontrado: rode src/extrair_fontes.py ou gere o corpus do PLN")
        self.modelo = SentenceTransformer(MODELO_EMBEDDINGS)
        self.bm25 = BM25Okapi([_tokens(t.texto) for t in self.trechos])
        assinatura = (self.origem, len(self.trechos), sum(len(t.texto) for t in self.trechos))
        cache = INDICE / "vetores.pkl"
        if not reconstruir and cache.exists():
            salvo = pickle.loads(cache.read_bytes())
            if salvo["assinatura"] == assinatura:
                vetores = salvo["vetores"]
            else:
                vetores = None
        else:
            vetores = None
        if vetores is None:
            vetores = self.modelo.encode([f"passage: {t.texto}" for t in self.trechos],
                                         normalize_embeddings=True, batch_size=32, show_progress_bar=False)
            INDICE.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(pickle.dumps({"assinatura": assinatura, "vetores": vetores}))
        self.indice = faiss.IndexFlatIP(vetores.shape[1])
        self.indice.add(np.asarray(vetores, dtype=np.float32))
        log.info("%d trechos de %s", len(self.trechos), self.origem)

    def buscar(self, pergunta: str, k: int = 4, servico: str | None = None) -> list[dict]:
        n = len(self.trechos)
        q = self.modelo.encode([f"query: {pergunta}"], normalize_embeddings=True)
        _, ordem_sem = self.indice.search(np.asarray(q, dtype=np.float32), min(n, 30))
        notas_bm25 = self.bm25.get_scores(_tokens(pergunta))
        ordem_bm25 = np.argsort(-notas_bm25)[:30]
        fusao: dict[int, float] = {}
        for pos, i in enumerate(ordem_sem[0]):
            fusao[int(i)] = fusao.get(int(i), 0) + 1 / (RRF_K + pos + 1)
        for pos, i in enumerate(ordem_bm25):
            fusao[int(i)] = fusao.get(int(i), 0) + 1 / (RRF_K + pos + 1)
        melhores = sorted(fusao.items(), key=lambda x: -x[1])
        if servico:
            melhores = [m for m in melhores if self.trechos[m[0]].servico in (servico, "")] or melhores
        return [{"texto": self.trechos[i].texto, "fonte": self.trechos[i].fonte, "servico": self.trechos[i].servico,
                 "url": self.trechos[i].url, "relevancia": round(nota, 4)} for i, nota in melhores[:k]]
