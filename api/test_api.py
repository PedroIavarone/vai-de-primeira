"""Testes da API simulada. Rodar: python -m pytest -q  (ou python test_api.py)"""

import os
from datetime import datetime

os.environ["VDP_MODO_DEMO"] = "1"  # testes determinísticos: sem carregar os modelos de visão

from fastapi.testclient import TestClient

import simulacao
from main import app

cliente = TestClient(app)


def test_saude():
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_fila_formato_e_status():
    dados = cliente.get("/fila").json()
    assert dados["simulado"] is True
    assert {u["id"] for u in dados["unidades"]} == {"centro", "leste", "movel-norte"}
    for u in dados["unidades"]:
        assert u["status"] in {"tranquila", "moderada", "cheia"}


def test_fila_pico_maior_que_manha_cedo():
    cedo = simulacao.fila_agora(datetime(2026, 11, 14, 8, 0))["unidades"][0]["pessoas"]
    pico = simulacao.fila_agora(datetime(2026, 11, 14, 13, 0))["unidades"][0]["pessoas"]
    assert pico > cedo


def test_fila_unidade_inexistente():
    assert cliente.get("/fila/nao-existe").status_code == 404


def test_checar_documento_pista_no_nome():
    r = cliente.post("/checar-documento",
                     files={"arquivo": ("certidão_reflexo.jpg", b"imagem-fake", "image/jpeg")})
    doc = r.json()["documentos"][0]
    assert r.status_code == 200
    assert doc["tipo"] == "certidao" and doc["qualidade"] == "reflexo" and doc["dica"]


def test_checar_documento_rejeita_nao_imagem():
    r = cliente.post("/checar-documento", files={"arquivo": ("a.pdf", b"x", "application/pdf")})
    assert r.status_code == 415


def test_checar_documento_rejeita_vazio():
    r = cliente.post("/checar-documento", files={"arquivo": ("a.png", b"", "image/png")})
    assert r.status_code == 400


def test_perguntar_cin_idoso():
    r = cliente.post("/perguntar", json={"pergunta": "Como tiro a identidade nova?", "perfil": "idoso"})
    dados = r.json()
    assert dados["servico"] == "cin" and dados["gratuito"] is True and dados["fontes"]


def test_perguntar_fora_do_tema_encaminha():
    dados = cliente.post("/perguntar", json={"pergunta": "Preciso de um advogado para divórcio"}).json()
    assert dados["encaminhar_para"] == "Defensoria Pública"


def test_perguntar_site_pago_alerta_golpe():
    dados = cliente.post("/perguntar", json={"pergunta": "Tenho que pagar o site para renovar?"}).json()
    assert "sites falsos" in dados["resposta"]


def test_perguntar_valida_entrada():
    assert cliente.post("/perguntar", json={"pergunta": "oi", "perfil": "geral"}).status_code == 422
    assert cliente.post("/perguntar", json={"pergunta": "Quero a CNH", "perfil": "x"}).status_code == 422


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main(["-q", __file__]))


def test_fila_usa_leitura_do_sensor_quando_recente(tmp_path, monkeypatch):
    import sqlite3
    import integracao_iot

    banco = tmp_path / "iot.sqlite"
    with sqlite3.connect(banco) as con:
        con.execute("CREATE TABLE leituras_fila (id INTEGER PRIMARY KEY, unidade TEXT, pessoas INTEGER, espera_min INTEGER,"
                    " status TEXT, ts_dispositivo TEXT, recebido_em TEXT DEFAULT (datetime('now','localtime')))")
        con.execute("INSERT INTO leituras_fila (unidade, pessoas, espera_min, status) VALUES ('centro', 30, 54, 'cheia')")
        con.execute("INSERT INTO leituras_fila (unidade, pessoas, espera_min, status, recebido_em)"
                    " VALUES ('leste', 2, 4, 'tranquila', datetime('now','localtime','-2 hours'))")
    monkeypatch.setattr(integracao_iot, "modo_demo", lambda: False)
    reais = integracao_iot.leituras_recentes(banco)
    assert set(reais) == {"centro"}  # a leitura antiga da unidade leste é ignorada
    resultado = integracao_iot.mesclar(simulacao.fila_agora(), reais)
    centro = next(u for u in resultado["unidades"] if u["id"] == "centro")
    leste = next(u for u in resultado["unidades"] if u["id"] == "leste")
    assert (centro["pessoas"], centro["status"], centro["origem"]) == (30, "cheia", "sensor")
    assert leste["origem"] == "simulado" and resultado["simulado"] is True


def test_fila_sem_banco_usa_estimativa(tmp_path):
    import integracao_iot

    assert integracao_iot.leituras_recentes(tmp_path / "nao_existe.sqlite") == {}
