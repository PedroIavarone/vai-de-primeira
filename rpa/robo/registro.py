"""Registro em SQLite: impede aviso repetido (idempotência) e guarda o histórico de execuções."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import agora

_TABELAS = """
CREATE TABLE IF NOT EXISTS avisos_enviados (
    cidadao_id TEXT NOT NULL, tipo TEXT NOT NULL, referencia TEXT NOT NULL, enviado_em TEXT NOT NULL,
    origem_texto TEXT, PRIMARY KEY (cidadao_id, tipo, referencia));
CREATE TABLE IF NOT EXISTS revisao_humana (
    execucao TEXT NOT NULL, cidadao_id TEXT, etapa TEXT, motivo TEXT, criado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS execucoes (
    execucao TEXT PRIMARY KEY, inicio TEXT, fim TEXT, resumo TEXT);
"""


class Registro:
    def __init__(self, caminho: Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(caminho)
        self.con.executescript(_TABELAS)

    def ja_enviado(self, cidadao_id: str, tipo: str, referencia: str) -> bool:
        return self.con.execute("SELECT 1 FROM avisos_enviados WHERE cidadao_id=? AND tipo=? AND referencia=?",
                                (cidadao_id, tipo, referencia)).fetchone() is not None

    def marcar_enviado(self, cidadao_id: str, tipo: str, referencia: str, origem_texto: str):
        self.con.execute("INSERT OR IGNORE INTO avisos_enviados VALUES (?,?,?,?,?)",
                         (cidadao_id, tipo, referencia, agora(), origem_texto))
        self.con.commit()

    def revisao(self, execucao: str, itens: list[dict]):
        self.con.executemany("INSERT INTO revisao_humana VALUES (?,?,?,?,?)",
                             [(execucao, i.get("id"), i.get("etapa"), i.get("motivo"), agora()) for i in itens])
        self.con.commit()

    def execucao(self, execucao: str, inicio: str, resumo: dict):
        self.con.execute("INSERT OR REPLACE INTO execucoes VALUES (?,?,?,?)",
                         (execucao, inicio, agora(), json.dumps(resumo, ensure_ascii=False)))
        self.con.commit()

    def fechar(self):
        self.con.close()
