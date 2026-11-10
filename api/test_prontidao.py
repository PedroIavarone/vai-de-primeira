"""Testes do Índice de Prontidão. Rodar: python -m pytest -q"""

from fastapi.testclient import TestClient

import prontidao
from main import app

cliente = TestClient(app)


def test_tudo_certo_da_100():
    r = prontidao.calcular("cin", [{"tipo": "certidao", "qualidade": "ok"}], espera_min=10, orientado=True)
    assert r["indice"] == 100 and r["faixa"] == "pronta" and r["pendencias"] == []


def test_nada_feito_e_fila_desconhecida():
    r = prontidao.calcular("cnh", [], espera_min=None, orientado=False)
    assert r["indice"] == 15 and r["faixa"] == "nao_pronta"
    assert len(r["pendencias"]) == 3  # CNH, comprovante e orientação


def test_documento_com_reflexo_vale_credito_parcial_e_explica():
    r = prontidao.calcular("cin", [{"tipo": "certidao", "qualidade": "reflexo"}], espera_min=10, orientado=True)
    assert r["componentes"]["documentos"] == 24  # 40% de 60
    assert r["indice"] == 64 and r["faixa"] == "quase"
    assert any("reflexo" in p for p in r["pendencias"])


def test_vale_a_melhor_conferencia_do_mesmo_documento():
    docs = [{"tipo": "certidao", "qualidade": "borrado"}, {"tipo": "certidao", "qualidade": "ok"}]
    assert prontidao.calcular("cin", docs, 10, True)["indice"] == 100


def test_documento_que_nao_e_do_servico_nao_conta():
    r = prontidao.calcular("cin", [{"tipo": "cnh", "qualidade": "ok"}], 10, True)
    assert r["componentes"]["documentos"] == 0


def test_fila_longa_tira_pontos():
    curta = prontidao.calcular("cin", [], 10, False)["componentes"]["fila"]
    media = prontidao.calcular("cin", [], 30, False)["componentes"]["fila"]
    longa = prontidao.calcular("cin", [], 90, False)["componentes"]["fila"]
    assert curta > media > longa


def test_endpoint_com_unidade():
    r = cliente.post("/prontidao", json={
        "servico": "cadunico", "unidade_id": "leste", "orientado": True,
        "documentos": [{"tipo": "cpf", "qualidade": "ok"}, {"tipo": "comprovante_residencia", "qualidade": "ok"}],
    })
    dados = r.json()
    assert r.status_code == 200 and dados["simulado"] is True
    assert dados["componentes"]["documentos"] == 60 and 0 <= dados["indice"] <= 100


def test_endpoint_sem_unidade_nao_e_simulado():
    dados = cliente.post("/prontidao", json={"servico": "cin"}).json()
    assert dados["simulado"] is False and dados["indice"] == 15


def test_endpoint_valida_entrada():
    assert cliente.post("/prontidao", json={"servico": "passaporte"}).status_code == 422
    assert cliente.post("/prontidao", json={"servico": "cin", "unidade_id": "nao-existe"}).status_code == 404
    ruim = {"servico": "cin", "documentos": [{"tipo": "certidao", "qualidade": "rasgado"}]}
    assert cliente.post("/prontidao", json=ruim).status_code == 422
