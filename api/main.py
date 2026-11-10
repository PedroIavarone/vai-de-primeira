"""API de integração do Vai de Primeira.

Endpoints ainda não ligados ao módulo definitivo (iot/, visao/, genai/) devolvem
dados de demonstração no formato de docs/contratos.md, com "simulado": true.

Rodar:  uvicorn main:app --reload   →   http://127.0.0.1:8000/docs
"""

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import prontidao
import simulacao

app = FastAPI(
    title="Vai de Primeira API",
    description="Integração entre app, totem, conferência de documentos, assistente e fila.",
    version="0.1.0",
)

# Front em React + Vite roda em localhost:5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 8 * 1024 * 1024  # 8 MB


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=1000)
    perfil: Literal["geral", "idoso", "baixa_escolaridade"] = "geral"


TipoDocumento = Literal["cin", "cnh", "cpf", "certidao", "comprovante_residencia", "desconhecido"]


class DocumentoConferido(BaseModel):
    tipo: TipoDocumento
    qualidade: Literal["ok", "borrado", "reflexo", "cortado"] = "ok"


class PedidoProntidao(BaseModel):
    servico: Literal["cin", "cnh", "cadunico"]
    documentos: list[DocumentoConferido] = Field(default_factory=list, max_length=20)
    unidade_id: str | None = None
    orientado: bool = False


@app.get("/saude")
def saude():
    return {"ok": True, "simulado": True, "hora": datetime.now().isoformat(timespec="seconds")}


@app.get("/fila")
def fila():
    # TODO(João): trocar pela leitura do banco alimentado pelo Node-RED.
    return simulacao.fila_agora()


@app.get("/fila/{unidade_id}")
def fila_unidade(unidade_id: str):
    for unidade in simulacao.fila_agora()["unidades"]:
        if unidade["id"] == unidade_id:
            return {"simulado": True, **unidade}
    raise HTTPException(status_code=404, detail=f"Unidade '{unidade_id}' não encontrada.")


@app.post("/checar-documento")
async def checar_documento(arquivo: UploadFile = File(...)):
    # TODO(Pedro): trocar pelo pipeline de visao/ (YOLO + qualidade + OCR).
    if arquivo.content_type not in TIPOS_IMAGEM:
        raise HTTPException(status_code=415, detail="Envie uma imagem JPG, PNG ou WEBP.")
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="A imagem chegou vazia.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=413, detail="Imagem maior que 8 MB.")
    return simulacao.checar_documento(arquivo.filename or "", conteudo)


@app.post("/perguntar")
def perguntar(dados: Pergunta):
    # TODO(Pedro): trocar pelo agente de genai/ (RAG sobre o corpus de pln/).
    return simulacao.responder(dados.pergunta, dados.perfil)


@app.post("/prontidao")
def calcular_prontidao(pedido: PedidoProntidao):
    """Índice de Prontidão (0 a 100): chance de resolver na primeira ida. Regras em prontidao.py."""
    espera_min = None
    simulado = False
    if pedido.unidade_id:
        fila_atual = fila()  # usa a mesma fonte do /fila (hoje simulada, depois o banco do IoT)
        unidade = next((u for u in fila_atual["unidades"] if u["id"] == pedido.unidade_id), None)
        if unidade is None:
            raise HTTPException(status_code=404, detail=f"Unidade '{pedido.unidade_id}' não encontrada.")
        espera_min = unidade["espera_min"]
        simulado = fila_atual.get("simulado", False)
    resultado = prontidao.calcular(
        pedido.servico, [d.model_dump() for d in pedido.documentos], espera_min, pedido.orientado
    )
    return {"simulado": simulado, **resultado}
