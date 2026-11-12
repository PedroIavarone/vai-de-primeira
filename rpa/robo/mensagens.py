"""Texto do aviso: gerado pelo LLM (Groq) e conferido; se falhar, usa um texto pronto.

Proteção de dados: o LLM recebe só a situação genérica (ex.: "a CNH vai vencer") e a faixa etária.
Nome, e-mail, datas e município nunca saem da máquina. O texto é escrito uma vez por tipo de aviso
e faixa etária e completado localmente com o nome e o motivo de cada pessoa.
"""
from __future__ import annotations

import logging
import os
import re

from . import config
from .regras import Aviso, link_oficial

log = logging.getLogger("mensagens")

TEMPLATES = {
    "cnh_vencendo": "Sua CNH está perto de vencer. Renove antes do prazo para continuar dirigindo, "
                    "pelos canais oficiais do Poupatempo.",
    "cnh_vencida": "Sua CNH está vencida. Procure os canais oficiais do Poupatempo para renovar antes de voltar a dirigir.",
    "cadunico_desatualizado": "Seu Cadastro Único precisa ser atualizado. Sem a atualização, benefícios podem ser "
                              "bloqueados. Procure o CRAS ou o posto do Cadastro Único da sua cidade.",
    "nascimento": "Parabéns pelo bebê! Inclua a criança no Cadastro Único da família e, se quiser, peça a Carteira "
                  "de Identidade Nacional dela, que é gratuita na primeira via.",
    "bpc_possivel": "Pessoas com 65 anos ou mais e renda familiar baixa podem ter direito ao BPC. Quem decide é o "
                    "INSS. Procure o CRAS da sua cidade para saber se é o seu caso.",
}
SITUACOES = {
    "cnh_vencendo": "a carteira de motorista (CNH) vai vencer nos próximos 30 dias",
    "cnh_vencida": "a carteira de motorista (CNH) já venceu",
    "cadunico_desatualizado": "o Cadastro Único da família está há mais de 2 anos sem atualização",
    "nascimento": "nasceu um bebê na família",
    "bpc_possivel": "a pessoa tem 65 anos ou mais e não recebe o BPC (só orientar, nunca afirmar o direito)",
}
ALERTA_LINK = ("Atenção: o site {site} não é um canal oficial do governo. Serviços oficiais não cobram por fora. "
               "Não informe dados nem pague nada nesse site.")
_PROIBIDO = re.compile(r"(você tem direito|garantid|aprovad|https?://|www\.)", re.I)
PROMPT = """Escreva um aviso curto (no máximo 3 frases) para um cidadão brasileiro com pouca familiaridade com termos técnicos.
Situação: {situacao}. Público: {faixa}.
Regras: linguagem simples e acolhedora; diga o que fazer e onde, citando SOMENTE os locais e canais que aparecem na base
oficial abaixo; não prometa direito a benefício; não invente valores, prazos, locais ou endereços; não inclua links;
não use nome nem datas.
Base oficial para o conteúdo: "{base}"
Responda só com o texto do aviso."""


def faixa_etaria(idade: int) -> str:
    return "idoso" if idade >= 60 else ("jovem" if idade < 30 else "adulto")


def _llm(prompt: str) -> str:
    from groq import Groq

    cliente = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=config.LLM_TIMEOUT_S, max_retries=0)
    r = cliente.chat.completions.create(model=config.LLM_MODELO, temperature=0.3,
                                        messages=[{"role": "user", "content": prompt}])
    return (r.choices[0].message.content or "").strip()


_LOCAIS = ("cartório", "cartorio", "prefeitura", "agência", "agencia", "detran", "poupatempo", "cras", "inss",
           "posto", "unidade", "secretaria", "portal", "aplicativo", "site", "telefone", "135", "ubs")


def texto_valido(texto: str, base: str) -> bool:
    """Tamanho razoável, sem promessa de direito, sem link e sem citar local que não está no texto oficial."""
    if not 20 <= len(texto) <= 600 or _PROIBIDO.search(texto):
        return False
    t, b = texto.lower(), base.lower()
    return not any(local in t and local not in b for local in _LOCAIS)


class Redator:
    def __init__(self, usar_llm: bool = True):
        self.usar_llm = usar_llm and bool(os.getenv("GROQ_API_KEY"))
        self.estatisticas = {"llm": 0, "template": 0, "llm_invalido": 0, "llm_erro": 0}
        self._cache: dict[tuple[str, str], tuple[str, str]] = {}
        if usar_llm and not self.usar_llm:
            log.warning("GROQ_API_KEY ausente: os avisos usam o texto pronto")

    def texto_do_aviso(self, tipo: str, faixa: str) -> tuple[str, str]:
        """Um texto por tipo de aviso e faixa etária, reaproveitado na execução. Devolve (texto, origem)."""
        if (tipo, faixa) in self._cache:
            return self._cache[(tipo, faixa)]
        resultado = self._redigir(tipo, faixa)
        self._cache[(tipo, faixa)] = resultado
        return resultado

    def _redigir(self, tipo: str, faixa: str) -> tuple[str, str]:
        base = TEMPLATES[tipo]
        if self.usar_llm:
            from .resiliencia import com_tentativas

            try:
                texto = com_tentativas(_llm, PROMPT.format(situacao=SITUACOES[tipo], faixa=faixa, base=base),
                                       descricao=f"LLM ({tipo})", tentativas=3, espera_inicial=5)
                texto = " ".join(texto.split())
                if texto_valido(texto, base):
                    self.estatisticas["llm"] += 1
                    return texto, "llm"
                self.estatisticas["llm_invalido"] += 1
                log.warning("resposta do LLM vazia ou fora das regras para %s; usando texto pronto", tipo)
            except Exception:
                self.estatisticas["llm_erro"] += 1
                log.warning("LLM indisponível para %s; usando texto pronto", tipo)
        self.estatisticas["template"] += 1
        return base, "template"


def montar_email(primeiro_nome: str, partes: list[tuple[Aviso, str]], link_suspeito: str, links_ok: dict,
                 links_servico: dict) -> tuple[str, str]:
    assunto = "Vai de Primeira: " + ("você tem um aviso" if len(partes) == 1 else f"você tem {len(partes)} avisos")
    linhas = [f"Olá, {primeiro_nome}!", ""]
    for aviso, texto in partes:
        linhas.append(f"- {texto}")
        linhas.append(f"  Por que você recebeu: {aviso.motivo.replace(' (apenas sinalização)', '')}.")
        link = links_servico.get(aviso.tipo)
        if link and links_ok.get(link):
            linhas.append(f"  Canal oficial: {link}")
    if link_suspeito and not link_oficial(link_suspeito):
        linhas += ["", ALERTA_LINK.format(site=link_suspeito)]
    linhas += ["", "Este aviso foi enviado porque você autorizou receber lembretes. Para não receber mais, responda SAIR.",
               "Central de Atendimento ao Cidadão · Vai de Primeira"]
    return assunto, "\n".join(linhas)
