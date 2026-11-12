"""Fábrica de Corpus: transforma documentos públicos em texto limpo, anonimizado e segmentado.

Etapas (na ordem em que são aplicadas):
  1. ingestão      PDF, TXT, DOCX, HTML e texto colado, guardando a origem de cada documento
  2. extração      pdfplumber, python-docx, BeautifulSoup e detecção de codificação para TXT
  3. limpeza       cabeçalhos e rodapés repetidos, número de página, URLs soltas, caracteres
                   estranhos, letras espaçadas, hifenização no fim da linha e linhas repetidas
  4. normalização  UTF-8 (NFC), espaços, quebras de linha e aspas, preservando acentos,
                   pontuação e maiúsculas. Sem remover stopwords e sem stemming
  5. anonimização  CPF, e-mail, telefone e nomes de pessoas (spaCy pt_core_news_md + regras)
  6. segmentação   trechos de 256 a 512 tokens, cortando só no fim de frase ou parágrafo

Os corpora de perguntas e respostas e de diálogos são gerados em geracao.py.
"""
from __future__ import annotations

import hashlib
import io
import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import tiktoken

FORMATOS = {".pdf": "pdf", ".txt": "txt", ".docx": "docx", ".html": "html", ".htm": "html"}
TOKENS_MIN, TOKENS_MAX, TOKENS_ALVO = 256, 512, 400
_codificador = tiktoken.get_encoding("cl100k_base")


def contar_tokens(texto: str) -> int:
    return len(_codificador.encode(texto))


# ---------------------------------------------------------------- 1 e 2. ingestão e extração
@dataclass
class Documento:
    fonte: str                    # nome do arquivo de origem, vai no campo "fonte" dos corpora
    formato: str                  # pdf, txt, docx, html ou colado
    paginas: list[str]            # texto extraído por página (PDF) ou em uma página só
    texto: str = ""               # texto depois da limpeza, normalização e anonimização
    log: dict = field(default_factory=dict)

    @property
    def bruto(self) -> str:
        return "\n".join(self.paginas)


def _ler_pdf(dados: bytes) -> list[str]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(dados)) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def _ler_docx(dados: bytes) -> list[str]:
    import docx

    doc = docx.Document(io.BytesIO(dados))
    linhas = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        estilo = (p.style.name or "").lower() if p.style is not None else ""
        if estilo.startswith(("heading", "título", "titulo", "title")):
            linhas.append(f"\n## {t}")
        elif "list" in estilo or "lista" in estilo:
            linhas.append(f"- {t}")
        else:
            linhas.append(t)
    for tabela in doc.tables:
        for linha in tabela.rows:
            celulas = [c.text.strip() for c in linha.cells if c.text.strip()]
            if celulas:
                linhas.append(" | ".join(dict.fromkeys(celulas)))
    return ["\n".join(linhas)]


def _ler_txt(dados: bytes) -> list[str]:
    for codificacao in ("utf-8-sig", "utf-8"):
        try:
            return [dados.decode(codificacao)]
        except UnicodeDecodeError:
            pass
    from charset_normalizer import from_bytes

    melhor = from_bytes(dados).best()
    return [str(melhor) if melhor else dados.decode("latin-1")]


_REMOVER_HTML = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "button", "svg", "iframe"]
_CLASSES_RUIDO = re.compile(r"(menu|breadcrumb|rodape|footer|header|social|share|compartilh|cookie|banner|navega)", re.I)
_BLOCOS_HTML = ["h1", "h2", "h3", "h4", "p", "li", "td", "dt", "dd"]


def _ler_html(dados: bytes) -> list[str]:
    from bs4 import BeautifulSoup

    sopa = BeautifulSoup(dados, "html.parser")
    for tag in sopa(_REMOVER_HTML):
        tag.decompose()
    for tag in sopa.find_all(attrs={"class": _CLASSES_RUIDO}):
        # nunca remove o body nem um ancestral do conteúdo principal
        if tag.name in ("html", "body") or tag.select_one("#content, main, article"):
            continue
        tag.decompose()
    candidatos = [sopa.select_one(s) for s in ("#content-core", "#content", "article", "main", "#conteudo")]
    candidatos = [c for c in candidatos if c and len(c.get_text(" ", strip=True)) > 300]
    raiz = candidatos[0] if candidatos else (sopa.body or sopa)
    linhas = []
    for bloco in raiz.find_all(_BLOCOS_HTML):
        if bloco.find(_BLOCOS_HTML):  # só o bloco mais interno, para não repetir texto
            continue
        t = " ".join(bloco.get_text(" ", strip=True).split())
        if len(t) < 3:
            continue
        if bloco.name in ("h1", "h2", "h3", "h4"):
            t = f"\n## {t}"
        elif bloco.name == "li":
            t = f"- {t}"
        linhas.append(t)
    return ["\n".join(linhas)]


_LEITORES = {"pdf": _ler_pdf, "docx": _ler_docx, "txt": _ler_txt, "html": _ler_html}


def ler_arquivo(nome: str, dados: bytes) -> Documento:
    formato = FORMATOS.get(Path(nome).suffix.lower())
    if formato is None:
        raise ValueError(f"formato não suportado: {nome} (use PDF, TXT, DOCX ou HTML)")
    return Documento(Path(nome).name, formato, _LEITORES[formato](dados))


def ler_caminho(caminho: str | Path) -> Documento:
    caminho = Path(caminho)
    return ler_arquivo(caminho.name, caminho.read_bytes())


def ler_texto_colado(texto: str, nome: str = "texto_colado") -> Documento:
    return Documento(nome, "colado", [texto])


# ---------------------------------------------------------------- 3. limpeza
_NUM_PAGINA = re.compile(r"^\s*(?:p[áa]g(?:ina)?\.?\s*)?\d{1,3}(?:\s*(?:de|/)\s*\d{1,3})?(?:\s+\d{1,3})?\s*$", re.I)
_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.I)
_SO_URL = re.compile(r"^\s*(?:[-•]\s*)?(?:https?://|www\.)\S+\s*$", re.I)
_LETRAS_ESPACADAS = re.compile(r"(?<!\S)(?:[^\W_] ){3,}[^\W_](?!\S)")
_INVISIVEIS = dict.fromkeys(map(ord, "­​‌‍⁠﻿�"), None)
_MARCADORES = re.compile(r"^\s*[•▪●◦○■□➢➤►✓✔]\s*", re.M)


def _juntar_hifen(m: re.Match) -> str:
    """"documen-/to" vira "documento", mas "salário-/mínimo" continua com hífen."""
    esquerda, direita = m.group(1), m.group(2)
    vocabulario = _modelo_nomes().vocab
    if not vocabulario.has_vector(esquerda + direita) and vocabulario.has_vector(f"{esquerda}-{direita}".lower()):
        return f"{esquerda}-{direita}"
    return esquerda + direita


def _assinatura(linha: str) -> str:
    return re.sub(r"\d+", "#", linha.strip().lower())


def _cabecalhos_e_rodapes(paginas: list[str]) -> set[str]:
    """Linhas que se repetem no topo ou no fim de pelo menos metade das páginas."""
    if len(paginas) < 3:
        return set()
    contagem = Counter()
    for pagina in paginas:
        linhas = [l for l in pagina.splitlines() if l.strip()]
        contagem.update({_assinatura(l) for l in linhas[:2] + linhas[-2:]})
    return {a for a, n in contagem.items() if n >= len(paginas) / 2}


def _juntar_linhas_quebradas(texto: str) -> str:
    """No PDF cada linha visual vira uma quebra. Junta as linhas que continuam a mesma frase."""
    saida = []
    for linha in texto.splitlines():
        anterior = saida[-1] if saida else ""
        continua = (
            anterior and linha.strip() and not anterior.startswith("## ")
            and not re.match(r"^\s*(?:-|\d{1,3}[.)])\s", linha)
            and not re.search(r"[.!?:;]$", anterior.strip())
            and (linha.strip()[0].islower() or len(anterior) > 45)
        )
        if continua:
            saida[-1] = anterior.rstrip() + " " + linha.strip()
        else:
            saida.append(linha)
    return "\n".join(saida)


def limpar(doc: Documento) -> str:
    log = Counter()
    repetidas = _cabecalhos_e_rodapes(doc.paginas)
    linhas = []
    for pagina in doc.paginas:
        for linha in pagina.splitlines():
            if repetidas and _assinatura(linha) in repetidas:
                log["cabecalho_rodape"] += 1
                continue
            if _NUM_PAGINA.match(linha):
                log["numero_pagina"] += 1
                continue
            if _SO_URL.match(linha):
                log["url_solta"] += 1
                continue
            linhas.append(linha)
        linhas.append("")
    texto = "\n".join(linhas)

    texto = texto.translate(_INVISIVEIS)
    texto = "".join(c for c in texto if c in "\n\t" or unicodedata.category(c)[0] != "C")
    texto = _MARCADORES.sub("- ", texto).replace(" • ", " - ").replace("•", "-")
    texto, n = _LETRAS_ESPACADAS.subn(lambda m: m.group(0).replace(" ", ""), texto)
    log["letras_espacadas"] += n
    # URL no meio da frase vira só o domínio ("acesse gov.br"), que é o que o cidadão precisa
    texto, n = _URL.subn(lambda m: re.sub(r"^(?:https?://)?(?:www\.)?", "", m.group(0)).split("/")[0], texto)
    log["url_no_texto"] += n
    texto, n = re.subn(r"(\w+)-\n\s*([a-zà-ÿ]\w*)", _juntar_hifen, texto)
    log["hifenizacao"] += n
    texto, n = re.subn(r"\b([A-ZÀ-Ý][a-zà-ÿ]{2,}) \1\b", r"\1", texto)  # "Denúncia Denúncia" (rótulo duplicado no HTML)
    log["palavra_duplicada"] += n
    if doc.formato == "pdf":
        texto = _juntar_linhas_quebradas(texto)

    # linhas repetidas: seguidas, ou curtas sem pontuação final que aparecem 3 vezes ou mais (menus)
    frequencia = Counter(l.strip() for l in texto.splitlines() if l.strip())
    saida, vistas = [], set()
    for linha in texto.splitlines():
        t = linha.strip()
        if t and saida and t == saida[-1].strip():
            log["linha_repetida"] += 1
            continue
        # item de menu: curto, sem pontuação final e fora de lista (itens de lista repetidos são conteúdo)
        parece_menu = len(t) < 80 and not t.startswith(("## ", "- ")) and not re.search(r"[.!?:;,]$", t)
        if t and parece_menu and frequencia[t] >= 3:
            if t in vistas:  # mantém só a primeira ocorrência
                log["linha_repetida"] += 1
                continue
            vistas.add(t)
        saida.append(linha)
    doc.log["limpeza"] = dict(log)
    return "\n".join(saida)


# ---------------------------------------------------------------- 4. normalização
_ASPAS = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‟": '"',
                        "‘": "'", "’": "'", "‚": "'", "‛": "'", "´": "'", "`": "'",
                        "\u2010": "-", "\u2011": "-"})  # hífens tipográficos viram o hífen comum


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).replace("\r\n", "\n").replace("\r", "\n")
    texto = texto.translate(_ASPAS)
    texto = "".join(" " if unicodedata.category(c) == "Zs" or c == "\t" else c for c in texto)
    texto = re.sub(r" {2,}", " ", texto)
    texto = "\n".join(l.strip() for l in texto.splitlines())
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


# ---------------------------------------------------------------- 5. anonimização
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_CPF = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d])|(?<!\d)\d{11}(?!\d)")
_TELEFONE = re.compile(
    r"(?<![\d])(?:\+?55\s?)?(?:\(\d{2}\)\s?|\b\d{2}\s)(?:9\s?)?\d{4}[\s-]?\d{4}(?!\d)"  # com DDD
    r"|(?<![\d-])(?:9\s?)?\d{4}-\d{4}(?![\d-])"                                     # 9999-9999
)
_SERVICO_PUBLICO = re.compile(r"^(?:0800|0300|4004|4003)")  # números de atendimento público ficam
_TRATAMENTOS = re.compile(r"\b(?:Sr\.?|Sra\.?|Srta\.?|Dona|Dr\.?|Dra\.?|senhor|senhora)\s+$")
_CONECTORES = {"da", "de", "do", "das", "dos", "e"}
# Palavras de nomes de órgãos, documentos e programas: entidade com qualquer uma delas não é pessoa.
_PALAVRAS_INSTITUCIONAIS = {
    "carteira", "identidade", "nacional", "cadastro", "único", "unico", "benefício", "beneficio",
    "prestação", "prestacao", "continuada", "ministério", "ministerio", "secretaria", "departamento",
    "governo", "estado", "federal", "receita", "poupatempo", "detran", "instituto", "seguro", "social",
    "assistência", "assistencia", "desenvolvimento", "programa", "sistema", "registro", "civil",
    "habilitação", "habilitacao", "trânsito", "transito", "brasil", "são", "paulo", "inss", "cras",
    "creas", "sus", "cnh", "cin", "cpf", "rg", "bpc", "loas", "bolsa", "família", "familia", "meu",
    "gov", "mercosul", "previdência", "previdencia", "cidadania", "serviços", "servicos", "central",
    "atendimento", "unidade", "posto", "prefeitura", "município", "municipio", "lei", "decreto",
    "portaria", "certidão", "certidao", "nascimento", "casamento", "título", "titulo", "eleitor",
    "trabalho", "renda", "fale", "conosco", "aplicativo", "app", "whatsapp", "android", "ios",
    "formulário", "formulario", "renach", "transtorno", "espectro", "autista", "pessoa", "deficiência",
}
_nlp = None


def _modelo_nomes():
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("pt_core_news_md", disable=["lemmatizer"])
    return _nlp


def _cpf_valido(digitos: str) -> bool:
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], range(tamanho + 1, 1, -1)))
        if (soma * 10 % 11) % 10 != int(digitos[tamanho]):
            return False
    return True


def _parece_pessoa(ent, texto: str) -> bool:
    palavras = ent.text.split()
    if any(p.lower().strip(".,") in _PALAVRAS_INSTITUCIONAIS for p in palavras) or re.search(r"\d", ent.text):
        return False
    if any(p.isupper() and len(p) > 1 for p in palavras):  # siglas
        return False
    nucleo = [t for t in ent if t.text.lower() not in _CONECTORES]
    if not nucleo or not all(t.text[0].isupper() and t.pos_ == "PROPN" for t in nucleo):
        return False
    if len({t.text.lower() for t in nucleo}) < len(nucleo):  # palavra repetida não é nome
        return False
    if len(nucleo) >= 2:
        return True
    return bool(_TRATAMENTOS.search(texto[max(0, ent.start_char - 12):ent.start_char]))


def anonimizar(texto: str) -> tuple[str, dict]:
    """Mascara dados pessoais. Devolve o texto e a contagem por tipo."""
    contagem = Counter()

    def _mascara(rotulo):
        def trocar(m):
            contagem[rotulo] += 1
            return f"[{rotulo}]"
        return trocar

    texto = _EMAIL.sub(_mascara("EMAIL"), texto)

    def trocar_cpf(m):
        so_digitos = re.sub(r"\D", "", m.group(0))
        if "." in m.group(0) or _cpf_valido(so_digitos):
            contagem["CPF"] += 1
            return "[CPF]"
        return m.group(0)

    texto = _CPF.sub(trocar_cpf, texto)

    def trocar_telefone(m):
        if _SERVICO_PUBLICO.match(re.sub(r"\D", "", m.group(0))):
            return m.group(0)
        contagem["TELEFONE"] += 1
        return "[TELEFONE]"

    texto = _TELEFONE.sub(trocar_telefone, texto)

    nlp = _modelo_nomes()
    partes, inicio = [], 0
    for ent in nlp(texto).ents:
        if ent.label_ == "PER" and _parece_pessoa(ent, texto):
            partes.append(texto[inicio:ent.start_char] + "[NOME]")
            inicio = ent.end_char
            contagem["NOME"] += 1
    texto = "".join(partes) + texto[inicio:]
    return texto, dict(contagem)


# ---------------------------------------------------------------- 6. segmentação
_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[\"(]?[A-ZÀ-Ý0-9])")


def _unidades(texto: str) -> list[str]:
    """Parágrafos (linhas); um parágrafo maior que o limite é quebrado em frases."""
    unidades = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith("## "):
            linha = linha[3:]
        if contar_tokens(linha) <= TOKENS_MAX:
            unidades.append(linha)
            continue
        for frase in _FIM_DE_FRASE.split(linha):
            if contar_tokens(frase) <= TOKENS_MAX:
                unidades.append(frase)
            else:  # frase gigante (raro): corta por palavras
                palavras, atual = frase.split(), []
                for p in palavras:
                    if contar_tokens(" ".join(atual + [p])) > TOKENS_MAX:
                        unidades.append(" ".join(atual))
                        atual = []
                    atual.append(p)
                unidades.append(" ".join(atual))
    return unidades


def _juntar(unidades: list[str]) -> str:
    return "\n".join(unidades)


def segmentar(texto: str) -> list[str]:
    """Divide o texto em trechos de 256 a 512 tokens, sempre entre parágrafos ou frases.

    Programação dinâmica sobre as unidades: escolhe os cortes que deixam todos os trechos dentro
    do intervalo e o mais perto possível de 400 tokens. Se não houver divisão possível (texto
    curto demais), usa a divisão gulosa.
    """
    unidades = _unidades(texto)
    if not unidades:
        return []
    tamanhos = [contar_tokens(u) for u in unidades]
    if sum(tamanhos) <= TOKENS_MAX:
        return [_juntar(unidades)]
    n, infinito = len(unidades), float("inf")
    custo, corte = [0.0] + [infinito] * n, [0] * (n + 1)
    for fim in range(1, n + 1):
        soma = 0
        for inicio in range(fim - 1, -1, -1):
            soma += tamanhos[inicio] + 1  # +1 pela quebra de linha
            if soma > TOKENS_MAX + 8:
                break
            if soma >= TOKENS_MIN and custo[inicio] + (soma - TOKENS_ALVO) ** 2 < custo[fim]:
                custo[fim], corte[fim] = custo[inicio] + (soma - TOKENS_ALVO) ** 2, inicio
    if custo[n] < infinito:
        blocos, fim = [], n
        while fim > 0:
            blocos.append(unidades[corte[fim]:fim])
            fim = corte[fim]
        trechos = [_juntar(b) for b in reversed(blocos)]
        if all(TOKENS_MIN <= contar_tokens(t) <= TOKENS_MAX for t in trechos):
            return trechos
    return _segmentar_guloso(unidades)


def _segmentar_guloso(unidades: list[str]) -> list[str]:
    blocos, atual = [], []
    for u in unidades:
        if atual and contar_tokens(_juntar(atual + [u])) > TOKENS_MAX:
            blocos.append(atual)
            atual = []
        atual.append(u)
        if contar_tokens(_juntar(atual)) >= TOKENS_ALVO:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    # o último bloco pequeno é juntado ao anterior ou o par é redividido ao meio
    if len(blocos) > 1 and contar_tokens(_juntar(blocos[-1])) < TOKENS_MIN:
        par = blocos[-2] + blocos[-1]
        if contar_tokens(_juntar(par)) <= TOKENS_MAX:
            blocos[-2:] = [par]
        else:
            melhor = min(range(1, len(par)), key=lambda i: abs(contar_tokens(_juntar(par[:i])) - contar_tokens(_juntar(par[i:]))))
            blocos[-2:] = [par[:melhor], par[melhor:]]
    return [_juntar(b) for b in blocos]


# ---------------------------------------------------------------- pipeline e qualidade
def processar(doc: Documento) -> Documento:
    texto = normalizar(limpar(doc))
    doc.texto, doc.log["anonimizacao"] = anonimizar(texto)
    return doc


def chave(texto: str) -> str:
    """Assinatura para achar duplicatas: ignora maiúsculas, acentos, pontuação e espaços."""
    base = unicodedata.normalize("NFD", texto.lower())
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return hashlib.md5(re.sub(r"[\W_]+", " ", base).strip().encode()).hexdigest()


def sem_duplicatas(itens: list[dict], campo) -> tuple[list[dict], int]:
    vistos, saida = set(), []
    for item in itens:
        k = chave(campo(item))
        if k not in vistos:
            vistos.add(k)
            saida.append(item)
    return saida, len(itens) - len(saida)


def corpus_texto(documentos: list[Documento]) -> tuple[list[dict], int]:
    trechos = [{"text": t, "fonte": d.fonte} for d in documentos for t in segmentar(d.texto)]
    return sem_duplicatas(trechos, lambda i: i["text"])


def texto_do_exemplo(item: dict) -> str:
    if "messages" in item:
        return "\n".join(m["content"] for m in item["messages"])
    if "instruction" in item:
        return f"{item['instruction']}\n{item.get('input', '')}\n{item['output']}".strip()
    return item["text"]


def estatisticas(itens: list[dict], removidas: int) -> dict:
    tokens = [contar_tokens(texto_do_exemplo(i)) for i in itens] or [0]
    return {
        "exemplos": len(itens),
        "media_tokens": round(statistics.mean(tokens), 1),
        "min_tokens": min(tokens),
        "max_tokens": max(tokens),
        "duplicatas_removidas": removidas,
        "por_fonte": dict(Counter(i["fonte"] for i in itens)),
    }
