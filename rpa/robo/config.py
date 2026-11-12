"""Configuração do robô. Chaves e senhas vêm do .env da raiz, nunca do código."""
import logging
import os
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1]
RAIZ = PASTA.parent
SAIDA = PASTA / "saida"
BASE_PADRAO = PASTA / "dados" / "cidadaos.xlsx"
BANCO = SAIDA / "avisos.sqlite"

DIAS_AVISO_CNH = 30
ANOS_CADUNICO_DESATUALIZADO = 2
DIAS_NASCIMENTO = 60
IDADE_BPC = 65
HORARIO_AGENDADO = "07:00"

DOMINIOS_OFICIAIS = ("gov.br",)  # gov.br e qualquer subdomínio (sp.gov.br, detran.sp.gov.br...)
LINKS_SERVICO = {
    "cnh_vencendo": "https://www.poupatempo.sp.gov.br",
    "cnh_vencida": "https://www.poupatempo.sp.gov.br",
    "cadunico_desatualizado": "https://www.gov.br/mds/pt-br/acoes-e-programas/cadastro-unico",
    "nascimento": "https://www.gov.br/pt-br/servicos/inscrever-se-no-cadastro-unico-para-programas-sociais-do-governo-federal",
    "bpc_possivel": "https://www.gov.br/inss/pt-br/direitos-e-deveres/beneficios-assistenciais/beneficio-assistencial-a-pessoa-idosa-bpc-loas",
}

LLM_MODELO = "openai/gpt-oss-20b"
LLM_TIMEOUT_S = 20
HTTP_TIMEOUT_S = 8
TENTATIVAS = 3
ESPERA_INICIAL_S = 1.0


def carregar_env():
    arquivo = RAIZ / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                nome, valor = linha.split("=", 1)
                os.environ.setdefault(nome.strip(), valor.strip().strip('"'))


def smtp():
    """Sem usuário configurado, usa a caixa de teste local (servidor_email_teste.py)."""
    if os.getenv("SMTP_USER"):
        return {"host": os.getenv("SMTP_HOST", "smtp.gmail.com"), "porta": int(os.getenv("SMTP_PORT", "587")),
                "usuario": os.getenv("SMTP_USER"), "senha": os.getenv("SMTP_PASSWORD", ""), "tls": True}
    return {"host": "127.0.0.1", "porta": int(os.getenv("RPA_SMTP_TESTE_PORTA", "1025")),
            "usuario": "", "senha": "", "tls": False}


def configurar_log(nome_execucao: str) -> Path:
    (SAIDA / "logs").mkdir(parents=True, exist_ok=True)
    arquivo = SAIDA / "logs" / f"{nome_execucao}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.FileHandler(arquivo, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    for ruidoso in ("httpx", "httpcore", "groq", "urllib3"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    return arquivo


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")
