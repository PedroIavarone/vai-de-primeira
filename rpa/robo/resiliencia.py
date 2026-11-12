"""Novas tentativas com espera crescente e registro em log."""
import logging
import time

from . import config

log = logging.getLogger("resiliencia")


def com_tentativas(funcao, *args, descricao: str, tentativas: int = config.TENTATIVAS,
                   espera_inicial: float = config.ESPERA_INICIAL_S, **kwargs):
    """Executa a função; se falhar, espera 1 s, 2 s, 4 s... e tenta de novo. Na última falha, relança o erro."""
    espera = espera_inicial
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:
            if tentativa == tentativas:
                log.error("%s falhou após %d tentativas: %s", descricao, tentativas, erro)
                raise
            log.warning("%s falhou (tentativa %d de %d): %s. Nova tentativa em %.0f s",
                        descricao, tentativa, tentativas, erro, espera)
            time.sleep(espera)
            espera *= 2
