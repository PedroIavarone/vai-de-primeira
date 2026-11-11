"""Liga o endpoint /perguntar ao Assistente da Jornada (genai/src/agente.py).

O assistente é carregado na primeira chamada. Sem a chave do Groq, sem as bibliotecas
ou com VDP_MODO_DEMO=1, a API continua respondendo com dados de demonstração.
"""
import logging
import sys
from pathlib import Path

from integracao_visao import modo_demo

log = logging.getLogger("integracao_genai")
_PASTA_GENAI = Path(__file__).resolve().parents[1] / "genai" / "src"
_assistente = None
_indisponivel = False


def obter():
    global _assistente, _indisponivel
    if modo_demo() or _indisponivel:
        return None
    if _assistente is None:
        try:
            if str(_PASTA_GENAI) not in sys.path:
                sys.path.insert(0, str(_PASTA_GENAI))
            from agente import Assistente
            _assistente = Assistente()
        except Exception as erro:
            log.warning("assistente indisponível, usando dados de demonstração: %s", erro)
            _indisponivel = True
            return None
    return _assistente


def responder(pergunta: str, perfil: str) -> dict | None:
    assistente = obter()
    if assistente is None:
        return None
    r = assistente.perguntar(pergunta, perfil)
    return {
        "simulado": False,
        "servico": r.get("servico"),
        "resposta": r.get("resposta", ""),
        "documentos_necessarios": r.get("documentos_necessarios", []),
        "gratuito": r.get("gratuito"),
        "fontes": r.get("fontes", []),
        "urls": r.get("urls", []),
        "encaminhar_para": r.get("encaminhar_para"),
    }
