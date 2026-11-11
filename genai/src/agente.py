"""Assistente da Jornada: agente com recuperação de documentos oficiais e ferramentas.

Fluxo de cada pergunta:
  1. mascara dados pessoais (CPF, e-mail, telefone) antes de qualquer chamada externa;
  2. o LLM (Groq) decide quais ferramentas usar e em que ordem:
       buscar_requisitos · consultar_fila · checar_documento · verificar_link
  3. a resposta final sai em formato estruturado (o mesmo de POST /perguntar),
     baseada apenas nos trechos recuperados e com as fontes citadas.
Se o LLM falhar ou devolver algo inválido, o assistente responde com uma mensagem
segura e os trechos encontrados, sem inventar.

Uso:
  from agente import Assistente
  Assistente().perguntar("O que preciso para tirar a identidade nova?", perfil="idoso")
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from base_conhecimento import BaseConhecimento

log = logging.getLogger("agente")
RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")
API_URL = os.getenv("VDP_API_URL", "http://127.0.0.1:8000")
MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")                   # escreve a resposta final
MODELO_FERRAMENTAS = os.getenv("GROQ_MODEL_FERRAMENTAS", "openai/gpt-oss-20b")  # decide as ferramentas
# Dois modelos dividem o limite do plano gratuito (8 mil tokens por minuto por modelo).
MAX_RODADAS = 3
TRECHOS_POR_BUSCA = 6
CARACTERES_POR_TRECHO = 1000  # janela mais relevante de cada trecho; cabe no limite de tokens do plano gratuito

DOMINIOS_OFICIAIS = ("gov.br",)  # cobre gov.br, sp.gov.br, detran.sp.gov.br, inss.gov.br, mds.gov.br etc.

PERFIS = {
    "geral": "Use linguagem clara e direta.",
    "idoso": "A pessoa é idosa. Use frases curtas, palavras simples, sem siglas sem explicação, e vá passo a passo.",
    "baixa_escolaridade": "A pessoa lê com dificuldade. Use frases muito curtas e palavras do dia a dia. Nada de termos técnicos.",
}

SISTEMA = """Você é o Assistente da Jornada do Vai de Primeira. Ajuda cidadãos brasileiros a resolver,
na primeira ida, três serviços: Carteira de Identidade Nacional (CIN), renovação da CNH e Cadastro Único,
além de orientar sobre o BPC, que depende do Cadastro Único.

Regras obrigatórias:
1. Responda SOMENTE com informações dos trechos oficiais retornados pela ferramenta buscar_requisitos.
   Sempre chame buscar_requisitos antes de responder sobre um serviço.
2. Se os trechos não trouxerem a resposta, diga que não encontrou a informação e indique o canal oficial.
   Nunca invente documento, valor, prazo ou regra.
3. Você NÃO decide se a pessoa tem direito a um benefício. Explique os requisitos e encaminhe para o órgão.
4. Fora do escopo (saúde, questões jurídicas, outros assuntos): não responda o mérito; oriente a procurar
   UBS, Defensoria Pública, CRAS ou o órgão adequado.
5. Se a pessoa mencionar um site ou link, use verificar_link. Serviços públicos não são cobrados por sites
   de terceiros.
6. Se a pessoa perguntar sobre fila ou espera, use consultar_fila.
7. Não peça nem repita dados pessoais.
Perfil da pessoa: {perfil}"""

SERVICOS = Literal["cin", "cnh", "cadunico", "bpc"]


class RespostaJornada(BaseModel):
    resposta: str = Field(description="Resposta final ao cidadão, em português, no tom do perfil")
    servico: Optional[SERVICOS] = Field(None, description="Serviço principal da pergunta, se houver")
    documentos_necessarios: list[str] = Field(default_factory=list, description="Documentos citados nos trechos")
    gratuito: Optional[bool] = Field(None, description="True/False só se os trechos disserem; senão null")
    fontes: list[str] = Field(default_factory=list, description="Nomes das fontes usadas (campo 'fonte' dos trechos)")
    encaminhar_para: Optional[str] = Field(None, description="Órgão para onde encaminhar, se a pergunta sair do escopo")


# ---------- proteção de dados ----------
PADROES_PII = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
]


def mascarar(texto: str) -> str:
    for padrao, marca in PADROES_PII:
        texto = padrao.sub(marca, texto)
    return texto


def janela_relevante(texto: str, pergunta: str, tamanho: int = CARACTERES_POR_TRECHO) -> str:
    """Devolve a janela do trecho com mais palavras da pergunta (em vez de cortar sempre o começo)."""
    if len(texto) <= tamanho:
        return texto
    palavras = {p for p in re.findall(r"\w{4,}", pergunta.lower())}
    melhor, melhor_nota = 0, -1
    for inicio in range(0, len(texto) - tamanho + 1, 100):
        janela = texto[inicio:inicio + tamanho].lower()
        nota = sum(janela.count(p) for p in palavras)
        if nota > melhor_nota:
            melhor, melhor_nota = inicio, nota
    return texto[melhor:melhor + tamanho]


# ---------- ferramentas ----------
_base: BaseConhecimento | None = None
_ultimas_fontes: list[dict] = []


def base() -> BaseConhecimento:
    global _base
    if _base is None:
        _base = BaseConhecimento()
    return _base


@tool
def buscar_requisitos(pergunta: str, servico: Optional[SERVICOS] = None) -> str:
    """Busca trechos de documentos oficiais sobre CIN, CNH, Cadastro Único ou BPC.
    Use sempre antes de responder sobre um serviço. 'servico' filtra a busca quando for claro."""
    trechos = base().buscar(pergunta, k=TRECHOS_POR_BUSCA, servico=servico)
    _ultimas_fontes.extend(trechos)
    return json.dumps([{"fonte": t["fonte"], "url": t["url"], "texto": janela_relevante(t["texto"], pergunta)} for t in trechos], ensure_ascii=False)


@tool
def consultar_fila() -> str:
    """Consulta a espera atual nas unidades de atendimento."""
    try:
        r = httpx.get(f"{API_URL}/fila", timeout=5)
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False)
    except Exception as erro:
        log.warning("fila indisponível: %s", erro)
        return json.dumps({"erro": "informação de fila indisponível no momento"})


@tool
def checar_documento(caminho_imagem: str) -> str:
    """Confere a foto de um documento enviada pelo cidadão (legível, borrado, reflexo ou cortado)."""
    try:
        caminho = Path(caminho_imagem)
        with open(caminho, "rb") as f:
            r = httpx.post(f"{API_URL}/checar-documento", files={"arquivo": (caminho.name, f, "image/jpeg")}, timeout=30)
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False)
    except Exception as erro:
        log.warning("conferência indisponível: %s", erro)
        return json.dumps({"erro": "não foi possível conferir o documento agora"})


@tool
def verificar_link(url: str) -> str:
    """Verifica se um site ou link é um canal oficial do governo."""
    host = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
    oficial = any(host == d or host.endswith(f".{d}") for d in DOMINIOS_OFICIAIS)
    return json.dumps({"dominio": host, "oficial": oficial,
                       "orientacao": "Canal oficial." if oficial else
                       "Não é um site oficial do governo. Não pague nem informe seus dados."}, ensure_ascii=False)


FERRAMENTAS = {f.name: f for f in (buscar_requisitos, consultar_fila, checar_documento, verificar_link)}


def resposta_segura(motivo: str) -> dict:
    fontes = list(dict.fromkeys(t["fonte"] for t in _ultimas_fontes))[:3]
    return {"resposta": "Não consegui montar a resposta agora. Confira as informações no canal oficial do serviço "
                        "ou procure a central de atendimento.",
            "servico": None, "documentos_necessarios": [], "gratuito": None, "fontes": fontes,
            "encaminhar_para": None, "erro": motivo}


class Assistente:
    def __init__(self):
        from langchain_groq import ChatGroq

        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("GROQ_API_KEY não configurada no .env")
        self.llm = ChatGroq(model=MODELO, temperature=0, max_retries=3, timeout=60)
        roteador = ChatGroq(model=MODELO_FERRAMENTAS, temperature=0, max_retries=3, timeout=60)
        self.com_ferramentas = roteador.bind_tools(list(FERRAMENTAS.values()))
        base()  # carrega o índice na criação, não na primeira pergunta

    def _resposta_final(self, texto: str, perfil: str, resultados: list[tuple[str, str]]) -> RespostaJornada:
        """Passo final em chamada separada, sem histórico de ferramentas, com JSON validado aqui."""
        contexto = "\n\n".join(f"[{nome}]\n{saida}" for nome, saida in resultados) or "(nenhuma ferramenta usada)"
        campos = ("resposta (texto), servico (cin, cnh, cadunico, bpc ou null), documentos_necessarios (lista), "
                  "gratuito (true, false ou null), fontes (lista com o campo 'fonte' dos trechos usados), "
                  "encaminhar_para (órgão ou null)")
        mensagens = [
            SystemMessage(SISTEMA.format(perfil=PERFIS.get(perfil, PERFIS["geral"]))),
            HumanMessage(f"Pergunta do cidadão:\n{texto}\n\nResultados das ferramentas:\n{contexto}\n\n"
                         f"Escreva a resposta final usando só esses resultados. Responda apenas com um objeto JSON "
                         f"com as chaves: {campos}."),
        ]
        bruto = self.llm.invoke(mensagens, response_format={"type": "json_object"}).content
        dados = json.loads(bruto)
        if isinstance(dados.get("properties"), dict) and "resposta" not in dados:  # o modelo devolveu o schema "embrulhado"
            dados = dados["properties"]
        for campo in ("fontes", "documentos_necessarios"):  # às vezes vêm objetos no lugar de textos
            dados[campo] = [i.get("fonte") or i.get("nome") or next(iter(i.values()), "") if isinstance(i, dict) else str(i)
                            for i in (dados.get(campo) or [])]
        return RespostaJornada.model_validate(dados)

    def perguntar(self, pergunta: str, perfil: str = "geral", imagem: str | None = None) -> dict:
        _ultimas_fontes.clear()
        self.ultimo_contexto = []
        texto = mascarar(pergunta.strip())
        if imagem:
            texto += f"\n(O cidadão enviou a foto de um documento: {imagem})"
        mensagens = [SystemMessage(SISTEMA.format(perfil=PERFIS.get(perfil, PERFIS["geral"]))), HumanMessage(texto)]
        ferramentas_usadas, resultados = [], []
        try:
            for _ in range(MAX_RODADAS):
                msg: AIMessage = self.com_ferramentas.invoke(mensagens)
                mensagens.append(msg)
                if not msg.tool_calls:
                    break
                for chamada in msg.tool_calls:
                    ferramenta = FERRAMENTAS.get(chamada["name"])
                    saida = ferramenta.invoke(chamada["args"]) if ferramenta else json.dumps({"erro": "ferramenta desconhecida"})
                    ferramentas_usadas.append(chamada["name"])
                    resultados.append((chamada["name"], saida))
                    mensagens.append(ToolMessage(saida, tool_call_id=chamada["id"]))
            final = self._resposta_final(texto, perfil, resultados)
            if not final.resposta.strip():
                return {**resposta_segura("resposta vazia do modelo"), "ferramentas": ferramentas_usadas}
            dados = final.model_dump()
            conhecidas = {t["fonte"] for t in _ultimas_fontes}
            dados["fontes"] = [f for f in dados["fontes"] if f in conhecidas] or list(dict.fromkeys(
                t["fonte"] for t in _ultimas_fontes))[:2]
            url_de = {t["fonte"]: t["url"] for t in _ultimas_fontes}
            dados["urls"] = [url_de.get(f, "") for f in dados["fontes"]]  # mesma ordem das fontes
            dados["ferramentas"] = ferramentas_usadas
            self.ultimo_contexto = [t["texto"] for t in _ultimas_fontes]  # usado na avaliação de fidelidade
            return dados
        except Exception as erro:
            log.error("falha no assistente: %s", erro)
            return {**resposta_segura(type(erro).__name__), "ferramentas": ferramentas_usadas}
