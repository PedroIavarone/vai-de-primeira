"""Testes do /checar-documento com os modelos reais de visão.

São pulados se os pesos (visao/modelos/) ou as bibliotecas de visão não estiverem
instalados. Rodar: python -m pytest -q test_visao_real.py
"""
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
PESOS = RAIZ / "visao" / "modelos"
FOTOS = RAIZ / "visao" / "datasets" / "preparado" / "deteccao" / "images" / "teste"

pytestmark = pytest.mark.skipif(
    not (PESOS / "detector.pt").exists() or importlib.util.find_spec("ultralytics") is None,
    reason="modelos de visão não instalados",
)


@pytest.fixture(scope="module")
def cliente(monkeypatch_module):
    monkeypatch_module.delenv("VDP_MODO_DEMO", raising=False)
    import integracao_visao
    integracao_visao._indisponivel = False
    from main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _jpg(imagem) -> bytes:
    return cv2.imencode(".jpg", imagem)[1].tobytes()


@pytest.mark.skipif(not FOTOS.exists(), reason="fotos de teste do MIDV-2020 não baixadas")
def test_foto_real_detecta_documento(cliente):
    foto = sorted(FOTOS.glob("*_1[0-9].jpg"))[0]  # distorção projetiva, condição difícil
    r = cliente.post("/checar-documento", files={"arquivo": (foto.name, foto.read_bytes(), "image/jpeg")})
    dados = r.json()
    assert r.status_code == 200 and dados["simulado"] is False
    doc = dados["documentos"][0]
    assert doc["confianca"] >= 0.5 and doc["qualidade"] in {"ok", "borrado", "reflexo", "cortado"}
    assert len(doc["caixa"]) == 4


def test_imagem_sem_documento_orienta(cliente):
    vazia = np.full((480, 640, 3), 230, np.uint8)
    dados = cliente.post("/checar-documento", files={"arquivo": ("vazia.jpg", _jpg(vazia), "image/jpeg")}).json()
    assert dados["simulado"] is False and dados["documentos"] == [] and "Nenhum documento" in dados["dica"]


def test_arquivo_corrompido_da_400(cliente):
    r = cliente.post("/checar-documento", files={"arquivo": ("x.jpg", b"nao-e-imagem", "image/jpeg")})
    assert r.status_code == 400
