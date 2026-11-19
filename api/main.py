"""API de integração do Vai de Primeira.

/checar-documento usa o módulo de visão (visao/), /perguntar usa o Assistente da Jornada (genai/)
e /fila usa as leituras do totem gravadas pelo Node-RED (iot/). Endpoint sem o módulo disponível
devolve dados de demonstração no formato de docs/contratos.md, com "simulado": true.
VDP_MODO_DEMO=1 força os dados de demonstração em todos os endpoints.

Rodar:  uvicorn main:app --reload   →   http://127.0.0.1:8000/docs
"""

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import integracao_genai
import integracao_iot
import integracao_visao
import prontidao
import simulacao

# Grupos da documentação (/docs): cada rota aparece junto de quem a usa.
GRUPOS = [
    {"name": "Cidadão", "description": "Usadas pelo app do cidadão e pelo modo totem."},
    {"name": "Fila e totem", "description": "Espera nas unidades, com a leitura real do totem (IoT) quando existe."},
    {"name": "Sistema", "description": "Saúde da API."},
]

app = FastAPI(
    title="Vai de Primeira API",
    description=(
        "Integração entre app, totem, conferência de documentos, assistente e fila.\n\n"
        "⚙️ Quando um módulo está desligado (sem chave do LLM, sem modelo de visão ou sem leitura do totem), "
        "a rota responde **no mesmo formato** com `\"simulado\": true`."
    ),
    version="0.1.0",
    openapi_tags=GRUPOS,
    docs_url=None,  # a página /docs é montada abaixo, com o visual do projeto
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "list", "displayRequestDuration": True},
)

ESTILO_DOCS = """
@import url("https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css");
@import url("https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap");
body { background: #f2f4f7; }
.swagger-ui, .swagger-ui .info .title, .swagger-ui .opblock-tag, .swagger-ui .opblock .opblock-summary-description { font-family: "Atkinson Hyperlegible", Arial, sans-serif !important; }
.swagger-ui .topbar { display: none; }
.swagger-ui .information-container { background: #1f5fad; border-radius: 16px; padding: 24px 28px !important; margin-top: 20px; }
.swagger-ui .info { margin: 0; } .swagger-ui .info .title, .swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info a { color: #fff !important; }
.swagger-ui .info .title small { background: #fff !important; } .swagger-ui .info .title small pre { color: #1f5fad !important; }
.swagger-ui .info code { background: rgba(255,255,255,.18); color: #fff; }
.swagger-ui .opblock-tag { font-size: 22px; color: #1f2933; border-bottom: 1px solid #d0d5dd; }
.swagger-ui .opblock { border-radius: 12px; box-shadow: none; background: #fff !important; border-color: #d0d5dd !important; }
.swagger-ui .opblock .opblock-summary-method { border-radius: 8px; min-width: 70px; font-weight: 700; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: #1e7f4f; }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background: #1f5fad; }
.swagger-ui .opblock .opblock-summary-description { color: #1f2933; font-size: 15px; }
.swagger-ui .btn.execute { background: #1f5fad; border-color: #1f5fad; }
"""


@app.get("/docs", include_in_schema=False)
def documentacao() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url=app.openapi_url, title="Vai de Primeira API",
                               swagger_css_url="/docs-estilo.css",
                               swagger_ui_parameters=app.swagger_ui_parameters)


@app.get("/docs-estilo.css", include_in_schema=False)
def estilo_documentacao() -> Response:
    return Response(ESTILO_DOCS, media_type="text/css")

# Front em React + Vite roda em localhost (porta 5173 por padrão; aceita outra porta local).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def carregar_visao_primeiro():
    # No macOS, carregar o FAISS do assistente antes do PyTorch da visão derruba o processo (falha de
    # segmentação). Carregar a visão ao iniciar garante a ordem certa, qualquer que seja a primeira chamada.
    integracao_visao.obter()


TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 8 * 1024 * 1024  # 8 MB


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=1000)
    perfil: Literal["geral", "idoso", "baixa_escolaridade"] = "geral"


TipoDocumento = Literal["cin", "cnh", "cpf", "certidao", "comprovante_residencia", "desconhecido"]


class DocumentoConferido(BaseModel):
    tipo: TipoDocumento
    qualidade: Literal["ok", "borrado", "reflexo", "cortado"] = "ok"
    cpf_visivel: bool = False  # número de CPF lido pelo OCR no próprio documento


class PedidoProntidao(BaseModel):
    servico: Literal["cin", "cnh", "cadunico"]
    documentos: list[DocumentoConferido] = Field(default_factory=list, max_length=20)
    unidade_id: str | None = None
    orientado: bool = False


@app.get("/saude", tags=["Sistema"], summary="A API está no ar?")
def saude():
    return {"ok": True, "simulado": True, "hora": datetime.now().isoformat(timespec="seconds")}


@app.get("/fila", tags=["Fila e totem"], summary="Espera agora em cada unidade · app, totem, assistente",
         description="**Usada por:** app · totem · assistente.\n\nLeitura real do totem nas unidades com sensor (`origem: sensor`); estimativa nas demais.",
         responses={200: {"content": {"application/json": {"example": {"simulado": False, "atualizado_em": "2026-11-18T15:24:00", "unidades": [
             {"id": "centro", "nome": "Central Centro", "pessoas": 5, "espera_min": 9, "status": "tranquila", "origem": "sensor", "lido_em": "2026-11-18 15:23:59"},
             {"id": "leste", "nome": "Central Leste", "pessoas": 9, "espera_min": 16, "status": "tranquila", "origem": "simulado"}]}}}}})
def fila():
    """Leitura real do totem (banco do IoT) nas unidades com sensor; estimativa nas demais."""
    return integracao_iot.mesclar(simulacao.fila_agora(), integracao_iot.leituras_recentes())


@app.get("/fila/{unidade_id}", tags=["Fila e totem"], summary="Espera agora numa unidade · app", description="**Usada por:** app.")
def fila_unidade(unidade_id: str):
    for unidade in fila()["unidades"]:
        if unidade["id"] == unidade_id:
            return {"simulado": unidade["origem"] == "simulado", **unidade}
    raise HTTPException(status_code=404, detail=f"Unidade '{unidade_id}' não encontrada.")


@app.post("/checar-documento", tags=["Cidadão"], summary="Confere a foto de um documento · app, assistente",
          description="**Usada por:** app · assistente.\n\nDevolve o tipo, a qualidade (ok, borrado, reflexo, cortado), a confiança, a caixa e uma dica.",
          responses={200: {"content": {"application/json": {"example": {"simulado": False, "documentos": [
              {"tipo": "certidao", "cpf_visivel": False, "confianca": 0.963, "qualidade": "reflexo", "confianca_qualidade": 0.999,
               "dica": "Tem reflexo no papel. Incline um pouco ou fuja da luz direta.", "caixa": [431, 106, 1173, 1074]}], "latencia_ms": 2699}}}}})
async def checar_documento(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in TIPOS_IMAGEM:
        raise HTTPException(status_code=415, detail="Envie uma imagem JPG, PNG ou WEBP.")
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="A imagem chegou vazia.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=413, detail="Imagem maior que 8 MB.")
    conferencia = integracao_visao.obter()
    if conferencia is None:
        return simulacao.checar_documento(arquivo.filename or "", conteudo)
    try:
        resultado = conferencia.analisar_bytes(conteudo)
    except ValueError:
        raise HTTPException(status_code=400, detail="Não foi possível ler a imagem enviada.")
    if not resultado["documentos"]:
        resultado["dica"] = "Nenhum documento encontrado. Coloque o documento inteiro na foto, sobre uma superfície lisa."
    return {"simulado": False, **resultado}


@app.post("/perguntar", tags=["Cidadão"], summary="Pergunta ao Assistente da Jornada · app, totem",
          description="**Usada por:** app · totem.\n\nResposta com base em páginas oficiais, sempre com a fonte.",
          responses={200: {"content": {"application/json": {"example": {"simulado": False, "servico": "cin",
              "resposta": "Para a primeira via da CIN, leve a certidão de nascimento ou de casamento. A emissão é gratuita.",
              "documentos_necessarios": ["certidão de nascimento ou de casamento (original)"], "gratuito": True,
              "fontes": ["cin_govbr_perguntas"], "urls": ["https://www.gov.br/gestao/pt-br/identidade-nacional"],
              "encaminhar_para": "Instituto de Identificação do seu estado"}}}}})
def perguntar(dados: Pergunta):
    resultado = integracao_genai.responder(dados.pergunta, dados.perfil)
    return resultado if resultado is not None else simulacao.responder(dados.pergunta, dados.perfil)


@app.post("/prontidao", tags=["Cidadão"], summary="Calcula o Índice de Prontidão (0 a 100) · app",
          description="**Usada por:** app · totem.\n\nRegra explicável em `prontidao.py`: documentos (até 60, só foto boa de documento obrigatório), "
                      "fila (até 25) e orientação (até 15). **Regra rigorosa:** fila e orientação só somam com todos os documentos obrigatórios ok. "
                      "Na CIN, o CPF impresso na certidão (`cpf_visivel`) vale como CPF.",
          responses={200: {"content": {"application/json": {"example": {"simulado": True, "servico": "cin", "indice": 80, "faixa": "pronta",
              "componentes": {"documentos": 60, "fila": 5, "orientacao": 15}, "documentos_completos": True, "obrigatorios": ["certidao", "cpf"],
              "pendencias": ["A fila está longa (cerca de 52 min). Vale escolher outro horário ou outra unidade."],
              "versao_regra": "2.0"}}}}})
def calcular_prontidao(pedido: PedidoProntidao):
    """Índice de Prontidão (0 a 100): chance de resolver na primeira ida. Regras em prontidao.py."""
    espera_min = None
    simulado = False
    if pedido.unidade_id:
        fila_atual = fila()  # mesma fonte do /fila: sensor quando houver, estimativa nas demais
        unidade = next((u for u in fila_atual["unidades"] if u["id"] == pedido.unidade_id), None)
        if unidade is None:
            raise HTTPException(status_code=404, detail=f"Unidade '{pedido.unidade_id}' não encontrada.")
        espera_min = unidade["espera_min"]
        simulado = unidade.get("origem") == "simulado"
    resultado = prontidao.calcular(
        pedido.servico, [d.model_dump() for d in pedido.documentos], espera_min, pedido.orientado
    )
    return {"simulado": simulado, **resultado}
