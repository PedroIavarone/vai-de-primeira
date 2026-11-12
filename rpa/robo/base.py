"""Leitura e validação da base de cidadãos (planilha .xlsx ou .csv, dados fictícios).

Linhas com dado inválido não derrubam a execução: vão para a fila de revisão humana com o motivo.
"""
from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger("base")
COLUNAS = ["id", "nome", "email", "municipio", "regiao", "idade", "cnh_validade", "cadunico_atualizado_em",
           "recebe_bpc", "filho_nascido_em", "link_informado", "consentiu_avisos"]
OBRIGATORIAS = ["id", "nome", "municipio", "idade", "consentiu_avisos"]
_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


@dataclass
class Cidadao:
    id: str
    nome: str
    email: str
    municipio: str
    regiao: str
    idade: int
    cnh_validade: date | None
    cadunico_atualizado_em: date | None
    recebe_bpc: bool
    filho_nascido_em: date | None
    link_informado: str
    consentiu_avisos: bool
    problemas: list[str] = field(default_factory=list)

    @property
    def primeiro_nome(self) -> str:
        return self.nome.split()[0] if self.nome else ""


def _data(valor) -> date | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError(f"data inválida: {texto!r}")


def _booleano(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor or "").strip().lower()
    if texto in ("sim", "s", "true", "1", "verdadeiro", "yes"):
        return True
    if texto in ("nao", "não", "n", "false", "0", "falso", "no", ""):
        return False
    raise ValueError(f"valor sim/não inválido: {valor!r}")


def _linhas(caminho: Path) -> list[dict]:
    if caminho.suffix.lower() == ".csv":
        with open(caminho, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    from openpyxl import load_workbook

    planilha = load_workbook(caminho, read_only=True, data_only=True).active
    linhas = planilha.iter_rows(values_only=True)
    cabecalho = [str(c).strip() if c is not None else "" for c in next(linhas)]
    return [dict(zip(cabecalho, valores)) for valores in linhas if any(v not in (None, "") for v in valores)]


def ler_base(caminho: Path) -> tuple[list[Cidadao], list[dict]]:
    """Devolve os cidadãos válidos e a lista de linhas para revisão humana."""
    if not caminho.exists():
        raise FileNotFoundError(f"base de cidadãos não encontrada: {caminho}")
    linhas = _linhas(caminho)
    faltando = [c for c in OBRIGATORIAS if linhas and c not in linhas[0]]
    if faltando:
        raise ValueError(f"colunas obrigatórias ausentes na base: {', '.join(faltando)}")

    cidadaos, revisao, vistos = [], [], set()
    for numero, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        bruto = {c: linha.get(c) for c in COLUNAS}
        try:
            ident = str(bruto["id"] or "").strip()
            if not ident:
                raise ValueError("id vazio")
            if ident in vistos:
                raise ValueError(f"id repetido: {ident}")
            try:
                idade = int(float(bruto["idade"]))
            except (TypeError, ValueError):
                raise ValueError(f"idade inválida: {bruto['idade']!r}")
            if not 0 <= idade <= 120:
                raise ValueError(f"idade fora do intervalo: {idade}")
            consentiu = _booleano(bruto["consentiu_avisos"])
            email = str(bruto["email"] or "").strip()
            c = Cidadao(
                id=ident, nome=str(bruto["nome"] or "").strip(), email=email,
                municipio=str(bruto["municipio"] or "").strip(), regiao=str(bruto["regiao"] or "").strip() or "Sem região",
                idade=idade, cnh_validade=_data(bruto["cnh_validade"]),
                cadunico_atualizado_em=_data(bruto["cadunico_atualizado_em"]),
                recebe_bpc=_booleano(bruto["recebe_bpc"]), filho_nascido_em=_data(bruto["filho_nascido_em"]),
                link_informado=str(bruto["link_informado"] or "").strip(), consentiu_avisos=consentiu,
            )
            if consentiu and not _EMAIL.match(email):
                raise ValueError(f"e-mail inválido para quem pediu avisos: {email!r}")
            vistos.add(ident)
            cidadaos.append(c)
        except (ValueError, TypeError) as erro:
            log.warning("linha %d da base vai para revisão humana: %s", numero, erro)
            revisao.append({"id": str(bruto.get("id") or f"linha {numero}"), "motivo": f"dado inválido: {erro}",
                            "etapa": "leitura da base"})
    log.info("base lida: %d cidadãos válidos, %d linhas para revisão humana", len(cidadaos), len(revisao))
    return cidadaos, revisao
