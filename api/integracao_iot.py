"""Liga GET /fila ao banco do módulo IoT (iot/dados/iot.sqlite, alimentado pelo Node-RED).

Usa a leitura mais recente de cada unidade com sensor, se tiver chegado nos últimos 15 minutos.
Unidades sem sensor ou sem leitura recente continuam com a estimativa de demonstração, marcadas
com "origem": "simulado".
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from integracao_visao import modo_demo

log = logging.getLogger("integracao_iot")
BANCO = Path(os.getenv("VDP_IOT_BANCO", Path(__file__).resolve().parents[1] / "iot" / "dados" / "iot.sqlite"))
VALIDADE_MIN = 15

_CONSULTA = f"""
SELECT unidade, pessoas, espera_min, status, recebido_em FROM leituras_fila AS l
WHERE recebido_em >= datetime('now', 'localtime', '-{VALIDADE_MIN} minutes')
  AND id = (SELECT MAX(id) FROM leituras_fila WHERE unidade = l.unidade)
"""


def leituras_recentes(banco: Path | None = None) -> dict[str, dict]:
    """{unidade: leitura} das unidades com sensor e leitura recente. Vazio se o banco não existir."""
    banco = banco or BANCO
    if modo_demo() or not banco.exists():
        return {}
    try:
        with sqlite3.connect(f"file:{banco}?mode=ro", uri=True, timeout=2) as con:
            con.row_factory = sqlite3.Row
            return {r["unidade"]: dict(r) for r in con.execute(_CONSULTA)}
    except sqlite3.Error as erro:
        log.warning("banco do IoT indisponível, usando estimativa: %s", erro)
        return {}


def mesclar(estimativa: dict, reais: dict[str, dict]) -> dict:
    """Troca a estimativa pela leitura real nas unidades com sensor."""
    unidades = []
    for u in estimativa["unidades"]:
        r = reais.get(u["id"])
        if r:
            unidades.append({**u, "pessoas": r["pessoas"], "espera_min": r["espera_min"], "status": r["status"],
                             "origem": "sensor", "lido_em": r["recebido_em"]})
        else:
            unidades.append({**u, "origem": "simulado"})
    return {**estimativa, "simulado": any(u["origem"] == "simulado" for u in unidades), "unidades": unidades}
