"""Geração dos corpora de perguntas e respostas e de diálogos, a partir dos trechos limpos.

Modelo: openai/gpt-oss-120b no Groq, em modo JSON, temperatura 0,2.
Fidelidade: cada resposta precisa trazer uma "evidência" copiada do trecho. Se a evidência não
estiver no trecho, o exemplo é descartado. Depois, a equipe revisa pelo menos 20% dos exemplos
(revisao.py).

As respostas do modelo ficam em cache (pln/cache/geracao.json). Assim o notebook roda do início
ao fim mesmo sem chave do Groq, reaproveitando o que já foi gerado e revisado.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import unicodedata
from pathlib import Path

from fabrica_corpus import anonimizar, normalizar

MODELO = "openai/gpt-oss-120b"
TEMPERATURA = 0.2
PASTA_CACHE = Path(__file__).resolve().parents[1] / "cache"
SISTEMA_ATENDENTE = (
    "Você é um atendente da Central de Atendimento ao Cidadão. Ajuda com a Carteira de Identidade "
    "Nacional, a renovação da CNH, o Cadastro Único e o BPC. Responda de forma simples, curta e "
    "educada, só com informações oficiais. Para outros assuntos, oriente a procurar o órgão ou o "
    "profissional certo."
)

PROMPT_QA = """Você prepara dados de treino para um assistente que atende cidadãos com pouca familiaridade com termos técnicos.

Leia o TRECHO de um documento oficial e crie de 2 a 3 pares de pergunta e resposta.
Regras:
- A pergunta é como um cidadão comum perguntaria, em linguagem do dia a dia.
- A resposta tem de 1 a 3 frases curtas, clara e simples, e usa SOMENTE informações do trecho.
- Não invente prazos, valores, documentos ou locais que não estejam no trecho.
- Não crie perguntas sobre valores em reais, porque podem estar desatualizados.
- Em "evidencia", copie LITERALMENTE do trecho a frase que comprova a resposta.
- Se o trecho não tiver informação útil para o cidadão, devolva a lista vazia.

Responda só com JSON: {{"pares": [{{"pergunta": "...", "resposta": "...", "evidencia": "..."}}]}}

TRECHO (fonte: {fonte}):
\"\"\"{trecho}\"\"\""""

PROMPT_CHAT = """Você prepara dados de treino para um atendente de serviços públicos que fala com cidadãos com pouca familiaridade com termos técnicos.

Leia o TRECHO de um documento oficial e crie UM diálogo com exatamente 2 perguntas do cidadão e 2 respostas do atendente.
Regras:
- A segunda pergunta continua a conversa (por exemplo, "e onde eu faço isso?").
- As respostas são curtas, simples, educadas e usam SOMENTE informações do trecho.
- Não invente prazos, valores, documentos ou locais. Não fale de valores em reais.
- Em cada resposta, "evidencia" é a frase copiada LITERALMENTE do trecho que a comprova.

Responda só com JSON: {{"dialogo": [{{"usuario": "...", "atendente": "...", "evidencia": "..."}}, {{"usuario": "...", "atendente": "...", "evidencia": "..."}}]}}

TRECHO (fonte: {fonte}):
\"\"\"{trecho}\"\"\""""

PROMPT_RECUSA = """Você prepara dados de treino para um atendente da Central de Atendimento ao Cidadão, que só ajuda com Carteira de Identidade Nacional, renovação da CNH, Cadastro Único e BPC.

Crie UM diálogo com 2 perguntas do cidadão e 2 respostas do atendente sobre este assunto FORA DO TEMA: {assunto}
Regras:
- Na primeira resposta, o atendente explica com educação que não pode orientar sobre isso e indica quem procurar: {encaminhamento}.
- Na segunda pergunta, o cidadão insiste ou pede uma dica. O atendente não dá a orientação, reforça onde procurar ajuda e lembra com o que pode ajudar.
- Linguagem simples e acolhedora. Não dê nenhuma orientação sobre o assunto em si.

Responda só com JSON: {{"dialogo": [{{"usuario": "...", "atendente": "..."}}, {{"usuario": "...", "atendente": "..."}}]}}"""

RECUSAS = [
    ("dor no peito e falta de ar", "um serviço de saúde, a UBS ou o SAMU (192) em caso de emergência"),
    ("qual remédio tomar para pressão alta", "um médico ou a Unidade Básica de Saúde (UBS)"),
    ("como fazer o divórcio", "a Defensoria Pública ou um advogado"),
    ("pensão alimentícia atrasada", "a Defensoria Pública ou um advogado"),
    ("o dono da casa quer despejar a família", "a Defensoria Pública"),
    ("produto com defeito que a loja não quer trocar", "o Procon"),
    ("como declarar o Imposto de Renda", "a Receita Federal"),
    ("como recorrer de uma multa de trânsito", "o órgão de trânsito que aplicou a multa"),
    ("em qual investimento colocar o dinheiro", "um profissional de finanças ou o seu banco"),
    ("como conseguir vaga em creche", "a Secretaria de Educação da sua cidade"),
    ("vacina da gripe para crianças", "a Unidade Básica de Saúde (UBS)"),
    ("violência em casa", "a Central de Atendimento à Mulher (180), a polícia (190) ou o CREAS"),
]


def _norm(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto.lower())
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", " ", base).strip()


def apoiada(evidencia: str, trecho: str) -> bool:
    """A evidência precisa existir no trecho (ignorando acentos, maiúsculas e pontuação)."""
    e = _norm(evidencia or "")
    return len(e) >= 15 and e in _norm(trecho)


class Gerador:
    def __init__(self, chave_api: str | None = None, pausa_s: float = 2.0):
        PASTA_CACHE.mkdir(exist_ok=True)
        self.arquivo_cache = PASTA_CACHE / "geracao.json"
        self.cache = json.loads(self.arquivo_cache.read_text(encoding="utf-8")) if self.arquivo_cache.exists() else {}
        self.chave_api = chave_api or os.getenv("GROQ_API_KEY")
        self.pausa_s = pausa_s
        self._cliente = None
        self.chamadas = 0

    def _chamar(self, prompt: str) -> dict:
        k = hashlib.md5(f"{MODELO}|{TEMPERATURA}|{prompt}".encode()).hexdigest()
        if k in self.cache:
            return self.cache[k]
        if not self.chave_api:
            return {}  # sem chave e sem cache: este exemplo fica de fora
        if self._cliente is None:
            from groq import Groq

            self._cliente = Groq(api_key=self.chave_api)
        for tentativa in range(6):
            try:
                r = self._cliente.chat.completions.create(
                    model=MODELO, temperature=TEMPERATURA, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}],
                )
                dados = json.loads(r.choices[0].message.content)
                break
            except Exception as erro:  # limite de tokens por minuto, conexão ou JSON inválido
                espera = 20 * (tentativa + 1) if "rate" in str(erro).lower() else 5
                print(f"  tentativa {tentativa + 1} falhou ({type(erro).__name__}); nova tentativa em {espera}s")
                time.sleep(espera)
        else:
            return {}
        self.chamadas += 1
        self.cache[k] = dados
        self.arquivo_cache.write_text(json.dumps(self.cache, ensure_ascii=False, indent=0), encoding="utf-8")
        time.sleep(self.pausa_s)
        return dados

    # ------------------------------------------------------------ perguntas e respostas
    def perguntas_respostas(self, trechos: list[dict]) -> tuple[list[dict], dict]:
        itens, rejeitados = [], 0
        for i, t in enumerate(trechos, 1):
            dados = self._chamar(PROMPT_QA.format(fonte=t["fonte"], trecho=t["text"]))
            for par in dados.get("pares", []) if isinstance(dados, dict) else []:
                if not isinstance(par, dict) or not apoiada(par.get("evidencia", ""), t["text"]):
                    rejeitados += 1
                    continue
                itens.append({
                    "instruction": anonimizar(normalizar(par["pergunta"]))[0],
                    "input": "",
                    "output": anonimizar(normalizar(par["resposta"]))[0],
                    "fonte": t["fonte"],
                    "evidencia": par["evidencia"].strip(),
                })
            if i % 10 == 0:
                print(f"  perguntas e respostas: {i}/{len(trechos)} trechos, {len(itens)} pares")
        return itens, {"rejeitados_sem_evidencia": rejeitados}

    # ------------------------------------------------------------ diálogos
    def dialogos(self, trechos: list[dict], quantidade: int = 26, semente: int = 42) -> tuple[list[dict], dict]:
        rng = random.Random(semente)
        escolhidos = rng.sample(trechos, min(quantidade, len(trechos)))
        itens, rejeitados = [], 0
        for t in escolhidos:
            dados = self._chamar(PROMPT_CHAT.format(fonte=t["fonte"], trecho=t["text"]))
            turnos = dados.get("dialogo", []) if isinstance(dados, dict) else []
            if len(turnos) < 2 or not all(isinstance(x, dict) and apoiada(x.get("evidencia", ""), t["text"]) for x in turnos):
                rejeitados += 1
                continue
            mensagens = [{"role": "system", "content": SISTEMA_ATENDENTE}]
            for x in turnos:
                mensagens += [{"role": "user", "content": anonimizar(normalizar(x["usuario"]))[0]},
                              {"role": "assistant", "content": anonimizar(normalizar(x["atendente"]))[0]}]
            itens.append({"messages": mensagens, "fonte": t["fonte"], "tipo": "orientacao"})
        for assunto, encaminhamento in RECUSAS:
            dados = self._chamar(PROMPT_RECUSA.format(assunto=assunto, encaminhamento=encaminhamento))
            turnos = dados.get("dialogo", []) if isinstance(dados, dict) else []
            if len(turnos) < 2:
                rejeitados += 1
                continue
            mensagens = [{"role": "system", "content": SISTEMA_ATENDENTE}]
            for x in turnos:
                mensagens += [{"role": "user", "content": normalizar(x["usuario"])},
                              {"role": "assistant", "content": normalizar(x["atendente"])}]
            itens.append({"messages": mensagens, "fonte": "regras_de_atendimento", "tipo": "recusa"})
        return itens, {"rejeitados": rejeitados}
