"""Caixa de e-mail de teste: um servidor SMTP local que guarda cada mensagem em saida/caixa_de_teste/.

Evita mandar aviso para qualquer endereço real. Só usa a biblioteca padrão.
Uso:  python servidor_email_teste.py            (porta 1025)
"""
import socketserver
import sys
import threading
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent / "saida" / "caixa_de_teste"


class _Sessao(socketserver.StreamRequestHandler):
    def _responder(self, texto: str):
        self.wfile.write((texto + "\r\n").encode())

    def handle(self):
        self._responder("220 caixa de teste Vai de Primeira")
        dados = None
        while True:
            linha = self.rfile.readline()
            if not linha:
                return
            if dados is not None:
                if linha in (b".\r\n", b".\n"):
                    PASTA.mkdir(parents=True, exist_ok=True)
                    nome = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".eml"
                    (PASTA / nome).write_bytes(b"".join(dados))
                    dados = None
                    self._responder("250 mensagem guardada")
                else:
                    dados.append(linha[1:] if linha.startswith(b"..") else linha)
                continue
            comando = linha.decode(errors="replace").strip().upper()
            if comando.startswith(("HELO", "EHLO")):
                self._responder("250 ola")
            elif comando.startswith(("MAIL FROM", "RCPT TO", "RSET", "NOOP")):
                self._responder("250 ok")
            elif comando == "DATA":
                dados = []
                self._responder("354 envie a mensagem e termine com uma linha com ponto")
            elif comando == "QUIT":
                self._responder("221 tchau")
                return
            else:
                self._responder("502 comando nao suportado")


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def iniciar(porta: int = 1025) -> Servidor:
    """Sobe o servidor numa thread (usado pelo main.py quando não há SMTP configurado)."""
    servidor = Servidor(("127.0.0.1", porta), _Sessao)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 1025
    print(f"caixa de teste em 127.0.0.1:{porta}, mensagens em {PASTA}")
    Servidor(("127.0.0.1", porta), _Sessao).serve_forever()
