"""Conferência dos sites oficiais e envio de e-mail, com tempo limite e novas tentativas."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import requests

from . import config
from .resiliencia import com_tentativas

log = logging.getLogger("canais")


def site_no_ar(url: str) -> bool:
    """Confere se o link oficial que vai no aviso está respondendo. Se não estiver, o aviso sai sem o link."""
    def consultar():
        r = requests.get(url, timeout=config.HTTP_TIMEOUT_S, allow_redirects=True,
                         headers={"User-Agent": "VaiDePrimeira-RPA/1.0"}, stream=True)
        r.close()
        if r.status_code >= 500:
            raise ConnectionError(f"HTTP {r.status_code}")
        return True

    try:
        return com_tentativas(consultar, descricao=f"consulta a {url}")
    except Exception:
        log.warning("site oficial fora do ar ou lento: %s. Os avisos saem sem esse link", url)
        return False


def conferir_links(urls) -> dict[str, bool]:
    return {u: site_no_ar(u) for u in sorted(set(urls))}


class CaixaDeSaida:
    def __init__(self, smtp: dict, remetente: str = "avisos@vaideprimeira.local"):
        self.smtp, self.remetente = smtp, remetente

    def _enviar(self, mensagem: EmailMessage):
        with smtplib.SMTP(self.smtp["host"], self.smtp["porta"], timeout=10) as s:
            if self.smtp["tls"]:
                s.starttls()
            if self.smtp["usuario"]:
                s.login(self.smtp["usuario"], self.smtp["senha"])
            s.send_message(mensagem)

    def enviar(self, para: str, assunto: str, corpo: str, ident: str) -> None:
        """'ident' é o id do cidadão: o log registra o id, nunca o e-mail."""
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.remetente, para, assunto
        m.set_content(corpo)
        com_tentativas(self._enviar, m, descricao=f"envio do aviso de {ident}")
