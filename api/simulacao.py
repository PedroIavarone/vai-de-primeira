"""Respostas simuladas da API, no formato de docs/contratos.md.

Serve para o front e o vídeo funcionarem antes dos módulos reais.
Os textos sobre serviços são simplificados: a versão real vem do corpus
de pln/ e deve sempre ser conferida na fonte oficial.
"""

import hashlib
import math
import os
import unicodedata
from datetime import datetime

UNIDADES = [
    {"id": "centro", "nome": "Central Centro", "base": 22},
    {"id": "leste", "nome": "Central Leste", "base": 8},
    {"id": "movel-norte", "nome": "Unidade Móvel Norte", "base": 4},
]
MINUTOS_POR_PESSOA = 1.8


def _status(espera_min: int) -> str:
    if espera_min <= 20:
        return "tranquila"
    if espera_min <= 45:
        return "moderada"
    return "cheia"


def fila_agora(agora: datetime | None = None) -> dict:
    """Lotação que sobe no fim da manhã e no começo da tarde, como numa unidade real."""
    agora = agora or datetime.now()
    if os.environ.get("VDP_HORA_FILA"):  # demonstração: fixa a hora da simulação (ex.: 13 = pico)
        agora = agora.replace(hour=int(os.environ["VDP_HORA_FILA"]), minute=0)
    hora = agora.hour + agora.minute / 60
    pico = max(0.0, math.sin((hora - 8) / 10 * math.pi))  # 0 às 8h, máximo às 13h, 0 às 18h
    unidades = []
    for u in UNIDADES:
        pessoas = round(u["base"] * (0.4 + pico))
        espera = round(pessoas * MINUTOS_POR_PESSOA)
        unidades.append({
            "id": u["id"], "nome": u["nome"], "pessoas": pessoas,
            "espera_min": espera, "status": _status(espera),
        })
    return {"simulado": True, "atualizado_em": agora.isoformat(timespec="seconds"), "unidades": unidades}


DICAS = {
    "ok": None,
    "borrado": "A foto ficou tremida. Apoie o celular e tire de novo.",
    "reflexo": "Tem reflexo no papel. Incline um pouco ou fuja da luz direta.",
    "cortado": "Uma parte do documento ficou fora da foto. Afaste um pouco o celular.",
}
PALAVRAS_TIPO = {
    "cnh": "cnh", "habilitacao": "cnh", "cin": "cin", "identidade": "cin", "rg": "cin",
    "cpf": "cpf", "certidao": "certidao", "comprovante": "comprovante_residencia",
    "conta": "comprovante_residencia",
}


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def checar_documento(nome_arquivo: str, conteudo: bytes) -> dict:
    """Simulação controlável pelo nome do arquivo, útil para gravar a demo.

    Ex.: 'certidao_reflexo.jpg' → certidão com reflexo; 'cnh.png' → CNH ok.
    Sem pista no nome, o resultado é estável para a mesma imagem.
    """
    nome = _sem_acento(nome_arquivo)
    tipo = next((t for chave, t in PALAVRAS_TIPO.items() if chave in nome), None)
    qualidade = next((q for q in ("borrado", "reflexo", "cortado") if q in nome), None)

    semente = int(hashlib.sha256(conteudo).hexdigest()[:8], 16)
    if tipo is None:
        tipo = ["cin", "cnh", "cpf", "certidao", "comprovante_residencia"][semente % 5]
    if qualidade is None:
        qualidade = ["ok", "ok", "ok", "reflexo", "borrado", "cortado"][semente % 6]
    confianca = round(0.72 + (semente % 25) / 100, 2)

    return {
        "simulado": True,
        "latencia_ms": 60 + semente % 60,
        "documentos": [{"tipo": tipo, "confianca": confianca, "qualidade": qualidade, "dica": DICAS[qualidade]}],
    }


SERVICOS = {
    "cin": {
        "palavras": ["identidade", "cin", "rg", "carteira de identidade"],
        "resposta": "Para tirar a Carteira de Identidade Nacional, leve a certidão de nascimento ou de casamento. "
                    "O número da nova identidade é o próprio CPF. A primeira via é gratuita.",
        "documentos": ["Certidão de nascimento ou de casamento", "CPF (se já tiver)"],
        "gratuito": True,
        "fontes": ["cin_govbr.html"],
    },
    "cnh": {
        "palavras": ["cnh", "habilitacao", "carteira de motorista", "renovar"],
        "resposta": "Para renovar a CNH, você precisa da CNH atual, de um documento de identidade e de um "
                    "comprovante de residência, além de fazer o exame médico. A renovação tem taxas do Detran.",
        "documentos": ["CNH atual", "Documento de identidade com foto", "Comprovante de residência recente"],
        "gratuito": False,
        "fontes": ["renovacao_cnh_detran.html"],
    },
    "cadunico": {
        "palavras": ["cadastro unico", "cadunico", "bolsa familia", "bpc", "beneficio"],
        "resposta": "Para se inscrever no Cadastro Único, a pessoa responsável pela família leva o CPF ou o título "
                    "de eleitor, e os outros moradores levam um documento de cada um. É gratuito. O pedido do "
                    "benefício é avaliado pelo órgão responsável.",
        "documentos": ["CPF ou título de eleitor do responsável", "Um documento de cada morador",
                       "Comprovante de residência (se tiver)"],
        "gratuito": True,
        "fontes": ["cartilha_cadunico.pdf"],
    },
}
FORA_DO_TEMA = {
    "Defensoria Pública": ["advogado", "processo", "justica", "divorcio", "pensao"],
    "UBS": ["doenca", "remedio", "febre", "dor", "medico"],
}
AVISO_SIMULADO = " (Resposta simulada: confirme sempre no órgão oficial.)"


def responder(pergunta: str, perfil: str) -> dict:
    texto = _sem_acento(pergunta)

    for destino, palavras in FORA_DO_TEMA.items():
        if any(p in texto for p in palavras):
            return {
                "simulado": True, "servico": None,
                "resposta": f"Esse assunto eu não consigo responder com segurança. Procure a {destino}, "
                            "que vai te orientar direitinho.",
                "documentos_necessarios": [], "gratuito": None, "fontes": [], "encaminhar_para": destino,
            }

    if "pag" in texto and ("site" in texto or "link" in texto):
        return {
            "simulado": True, "servico": None,
            "resposta": "Cuidado: há sites falsos que cobram por serviços públicos. Não pague nenhum site que "
                        "não seja o canal oficial do governo. Se quiser, me mande o link que eu confiro.",
            "documentos_necessarios": [], "gratuito": None, "fontes": [], "encaminhar_para": None,
        }

    for chave, servico in SERVICOS.items():
        if any(p in texto for p in servico["palavras"]):
            resposta = servico["resposta"]
            if perfil in ("idoso", "baixa_escolaridade"):
                lista = "; ".join(servico["documentos"])
                resposta = f"Vou te explicar bem simples. Leve: {lista}. " + (
                    "Não precisa pagar nada." if servico["gratuito"] else "Tem uma taxa para pagar.")
            return {
                "simulado": True, "servico": chave, "resposta": resposta + AVISO_SIMULADO,
                "documentos_necessarios": servico["documentos"], "gratuito": servico["gratuito"],
                "fontes": servico["fontes"], "encaminhar_para": None,
            }

    return {
        "simulado": True, "servico": None,
        "resposta": "Ainda não sei responder isso. Por enquanto eu ajudo com a identidade nova (CIN), a renovação "
                    "da CNH e o Cadastro Único.",
        "documentos_necessarios": [], "gratuito": None, "fontes": [], "encaminhar_para": None,
    }
