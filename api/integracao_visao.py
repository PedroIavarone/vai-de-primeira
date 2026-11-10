"""Liga o endpoint /checar-documento ao módulo de visão (visao/src/conferencia.py).

O modelo é carregado na primeira chamada, não na subida da API. Se os pesos ou as
bibliotecas de visão não estiverem disponíveis, ou se VDP_MODO_DEMO=1, a API continua
respondendo com dados de demonstração.
"""
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("integracao_visao")
_PASTA_VISAO = Path(__file__).resolve().parents[1] / "visao" / "src"
_conferencia = None
_indisponivel = False


def modo_demo() -> bool:
    return os.getenv("VDP_MODO_DEMO") == "1"


def obter():
    """Devolve a instância de Conferencia, ou None se a visão real não puder ser usada."""
    global _conferencia, _indisponivel
    if modo_demo() or _indisponivel:
        return None
    if _conferencia is None:
        try:
            if str(_PASTA_VISAO) not in sys.path:
                sys.path.insert(0, str(_PASTA_VISAO))
            from conferencia import Conferencia
            _conferencia = Conferencia()
        except Exception as erro:
            log.warning("visão real indisponível, usando dados de demonstração: %s", erro)
            _indisponivel = True
            return None
    return _conferencia
