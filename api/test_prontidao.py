"""Testes do Índice de Prontidão. Rodar: python -m pytest -q"""

import os

os.environ["VDP_MODO_DEMO"] = "1"  # testes determinísticos: sem carregar os modelos de visão

from fastapi.testclient import TestClient

import prontidao
from main import app

cliente = TestClient(app)


CERTIDAO_COM_CPF = {"tipo": "certidao", "qualidade": "ok", "cpf_visivel": True}


def test_tudo_certo_da_100():
    r = prontidao.calcular("cin", [CERTIDAO_COM_CPF], espera_min=10, orientado=True)
    assert r["indice"] == 100 and r["faixa"] == "pronta" and r["pendencias"] == []


def test_sem_documento_nada_conta():
    r = prontidao.calcular("cnh", [], espera_min=None, orientado=True)
    assert r["indice"] == 0 and r["faixa"] == "nao_pronta"
    assert r["componentes"] == {"documentos": 0, "fila": 0, "orientacao": 0}


def test_foto_com_problema_vale_zero_e_explica():
    r = prontidao.calcular("cin", [{"tipo": "certidao", "qualidade": "reflexo"}], espera_min=10, orientado=True)
    assert r["indice"] == 0 and r["faixa"] == "nao_pronta"
    assert any("reflexo" in p for p in r["pendencias"])


def test_vale_a_melhor_conferencia_do_mesmo_documento():
    docs = [{"tipo": "certidao", "qualidade": "borrado"}, CERTIDAO_COM_CPF]
    assert prontidao.calcular("cin", docs, 10, True)["indice"] == 100


def test_documento_que_nao_e_do_servico_nao_conta():
    r = prontidao.calcular("cin", [{"tipo": "cnh", "qualidade": "ok"}], 10, True)
    assert r["indice"] == 0


def test_cin_sem_cpf_na_certidao_pede_o_cpf():
    r = prontidao.calcular("cin", [{"tipo": "certidao", "qualidade": "ok"}], 10, True)
    assert r["componentes"]["documentos"] == 30 and r["indice"] == 30
    assert any("CPF" in p for p in r["pendencias"])
    com_cpf = prontidao.calcular("cin", [{"tipo": "certidao", "qualidade": "ok"}, {"tipo": "cpf", "qualidade": "ok"}], 10, True)
    assert com_cpf["indice"] == 100


def test_sequencia_da_demonstracao():
    docs, indices = [], []
    for d in [{"tipo": "certidao", "qualidade": "reflexo"}, {"tipo": "cin", "qualidade": "borrado"}, CERTIDAO_COM_CPF]:
        docs.append(d)
        indices.append(prontidao.calcular("cin", docs, 50, True)["indice"])
    assert indices == [0, 0, 80]


def test_fila_longa_tira_pontos():
    curta = prontidao.calcular("cin", [CERTIDAO_COM_CPF], 10, False)["componentes"]["fila"]
    media = prontidao.calcular("cin", [CERTIDAO_COM_CPF], 30, False)["componentes"]["fila"]
    longa = prontidao.calcular("cin", [CERTIDAO_COM_CPF], 90, False)["componentes"]["fila"]
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
    assert dados["simulado"] is False and dados["indice"] == 0


def test_endpoint_valida_entrada():
    assert cliente.post("/prontidao", json={"servico": "passaporte"}).status_code == 422
    assert cliente.post("/prontidao", json={"servico": "cin", "unidade_id": "nao-existe"}).status_code == 404
    ruim = {"servico": "cin", "documentos": [{"tipo": "certidao", "qualidade": "rasgado"}]}
    assert cliente.post("/prontidao", json=ruim).status_code == 422
