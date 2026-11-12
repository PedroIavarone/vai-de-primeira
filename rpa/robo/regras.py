"""Regras que decidem quem precisa de aviso. São explicáveis: cada aviso traz o motivo.

O robô nunca decide direito a benefício. "bpc_possivel" só sinaliza e orienta a procurar o CRAS.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from . import config
from .base import Cidadao


@dataclass(frozen=True)
class Aviso:
    tipo: str
    motivo: str
    referencia: str  # o que torna o aviso único (ex.: a validade da CNH). Base da idempotência.


def _anos_atras(hoje: date, anos: int) -> date:
    try:
        return hoje.replace(year=hoje.year - anos)
    except ValueError:  # 29 de fevereiro
        return hoje.replace(year=hoje.year - anos, day=28)


def avisos_para(c: Cidadao, hoje: date) -> list[Aviso]:
    avisos = []
    if c.cnh_validade:
        dias = (c.cnh_validade - hoje).days
        if 0 <= dias <= config.DIAS_AVISO_CNH:
            avisos.append(Aviso("cnh_vencendo", f"a CNH vence em {dias} dia(s), em {c.cnh_validade:%d/%m/%Y}",
                                c.cnh_validade.isoformat()))
        elif dias < 0:
            avisos.append(Aviso("cnh_vencida", f"a CNH venceu em {c.cnh_validade:%d/%m/%Y}", c.cnh_validade.isoformat()))
    if c.cadunico_atualizado_em:
        if c.cadunico_atualizado_em < _anos_atras(hoje, config.ANOS_CADUNICO_DESATUALIZADO):
            avisos.append(Aviso("cadunico_desatualizado",
                                f"o Cadastro Único não é atualizado desde {c.cadunico_atualizado_em:%d/%m/%Y}",
                                c.cadunico_atualizado_em.isoformat()))
    if c.filho_nascido_em and 0 <= (hoje - c.filho_nascido_em).days <= config.DIAS_NASCIMENTO:
        avisos.append(Aviso("nascimento", f"nascimento de filho em {c.filho_nascido_em:%d/%m/%Y}",
                            c.filho_nascido_em.isoformat()))
    if c.idade >= config.IDADE_BPC and not c.recebe_bpc:
        avisos.append(Aviso("bpc_possivel", f"tem {c.idade} anos e não recebe o BPC (apenas sinalização)",
                            f"idade>={config.IDADE_BPC}"))
    return avisos


def link_oficial(url: str) -> bool:
    """True se o endereço é de um domínio oficial (gov.br ou subdomínio)."""
    from urllib.parse import urlparse

    if not url:
        return False
    host = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in config.DOMINIOS_OFICIAIS)
