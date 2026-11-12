"""Roda a Fábrica de Corpus do início ao fim e grava os resultados em pln/saida/.

Uso:
  python src/gerar_corpus.py                      # documentos de pln/entrada/
  python src/gerar_corpus.py --entrada outra/pasta

Saídas:
  saida/corpus_texto.jsonl   trechos limpos e anonimizados (256 a 512 tokens)
  saida/corpus_qa.jsonl      perguntas e respostas apoiadas no documento
  saida/corpus_chat.jsonl    diálogos com 2 ou mais trocas, incluindo recusas
  saida/relatorio_qualidade.json   estatísticas, duplicatas removidas e 5 exemplos de cada corpus
  revisao/revisao.csv        amostra de 20% para revisão humana (criada uma vez, preenchida à mão)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
from pathlib import Path

import fabrica_corpus as fc
from geracao import MODELO, PROMPT_CHAT, PROMPT_QA, PROMPT_RECUSA, Gerador

PASTA = Path(__file__).resolve().parents[1]
CAMPOS_QA = ("instruction", "input", "output", "fonte")
SEMENTE = 42

EXEMPLO_COLADO = (
    "Relato de atendimento: a Sra. Francisca Alves de Oliveira, CPF 529.982.247-25, procurou o CRAS "
    "acompanhada do filho Joaquim Pereira. Contato: (15) 99812-3456 ou francisca.oliveira@email.com. "
    "Para dúvidas sobre o BPC, ligue 135. Dados fictícios, criados para demonstrar a anonimização."
)


def carregar_env():
    arquivo = PASTA.parent / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                nome, valor = linha.split("=", 1)
                os.environ.setdefault(nome.strip(), valor.strip().strip('"'))


def salvar_jsonl(caminho: Path, itens: list[dict]):
    with open(caminho, "w", encoding="utf-8") as f:
        for item in itens:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- revisão humana
def _id(item: dict) -> str:
    return fc.chave(fc.texto_do_exemplo(item))[:10]


def criar_revisao(qa: list[dict], chat: list[dict], caminho: Path):
    rng = random.Random(SEMENTE)
    amostra_qa = rng.sample(qa, math.ceil(0.2 * len(qa)))
    amostra_chat = rng.sample(chat, math.ceil(0.2 * len(chat)))
    caminho.parent.mkdir(exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "tipo", "fonte", "pergunta", "resposta", "evidencia_no_documento",
                    "fiel", "resposta_corrigida", "observacao"])
        for i in amostra_qa:
            w.writerow([_id(i), "qa", i["fonte"], i["instruction"], i["output"], i.get("evidencia", ""), "", "", ""])
        for i in amostra_chat:
            msgs = [m for m in i["messages"] if m["role"] != "system"]
            w.writerow([_id(i), "chat", i["fonte"],
                        " / ".join(m["content"] for m in msgs if m["role"] == "user"),
                        " / ".join(m["content"] for m in msgs if m["role"] == "assistant"), "", "", "", ""])


def aplicar_revisao(qa: list[dict], chat: list[dict], caminho: Path) -> tuple[list, list, dict]:
    if not caminho.exists():
        return qa, chat, {"revisados": 0}
    with open(caminho, encoding="utf-8") as f:
        linhas = {l["id"]: l for l in csv.DictReader(f)}
    resumo = {"revisados": 0, "corrigidos": 0, "removidos": 0}

    def decidir(item):
        l = linhas.get(_id(item))
        if not l or not l["fiel"].strip():
            return item
        resumo["revisados"] += 1
        if l["resposta_corrigida"].strip() and "output" in item:
            resumo["corrigidos"] += 1
            return {**item, "output": l["resposta_corrigida"].strip()}
        if l["fiel"].strip().lower() in ("nao", "não", "n"):
            resumo["removidos"] += 1
            return None
        return item

    qa = [x for x in map(decidir, qa) if x]
    chat = [x for x in map(decidir, chat) if x]
    resumo["amostra"] = len(linhas)
    return qa, chat, resumo


# ---------------------------------------------------------------- pipeline
def executar(entrada: Path | None, saida: Path, documentos: list[fc.Documento] | None = None,
             gerar: bool = True, revisao: bool = True) -> dict:
    """gerar=False pula o LLM (só o corpus de texto). revisao=False não cria nem aplica a revisão humana."""
    carregar_env()
    saida.mkdir(parents=True, exist_ok=True)
    if documentos is None:
        arquivos = sorted(p for p in entrada.iterdir() if p.suffix.lower() in fc.FORMATOS)
        documentos = [fc.ler_caminho(p) for p in arquivos]
    for d in documentos:
        fc.processar(d)
        print(f"{d.fonte:40} {d.formato:6} {len(d.paginas):>3} pág.  {fc.contar_tokens(d.texto):>6} tokens")

    texto, dup_texto = fc.corpus_texto(documentos)
    gerador = Gerador()
    qa, info_qa, chat, info_chat = [], {}, [], {}
    if gerar:
        qa, info_qa = gerador.perguntas_respostas(texto)
        chat, info_chat = gerador.dialogos(texto)
    qa, dup_qa = fc.sem_duplicatas(qa, lambda i: i["instruction"])
    chat, dup_chat = fc.sem_duplicatas(chat, fc.texto_do_exemplo)

    info_revisao = {"revisados": 0}
    if revisao and qa:
        arquivo_revisao = PASTA / "revisao" / "revisao.csv"
        if not arquivo_revisao.exists():
            criar_revisao(qa, chat, arquivo_revisao)
        qa, chat, info_revisao = aplicar_revisao(qa, chat, arquivo_revisao)

    salvar_jsonl(saida / "corpus_texto.jsonl", texto)
    salvar_jsonl(saida / "corpus_qa.jsonl", [{k: i[k] for k in CAMPOS_QA} for i in qa])
    salvar_jsonl(saida / "corpus_chat.jsonl", [{"messages": i["messages"], "fonte": i["fonte"]} for i in chat])

    rng = random.Random(SEMENTE)
    anonimizado, contagem = fc.anonimizar(fc.normalizar(EXEMPLO_COLADO))
    relatorio = {
        "documentos": [{"fonte": d.fonte, "formato": d.formato, "paginas": len(d.paginas),
                        "tokens_brutos": fc.contar_tokens(d.bruto), "tokens_limpos": fc.contar_tokens(d.texto),
                        "limpeza": d.log.get("limpeza", {}), "anonimizacao": d.log.get("anonimizacao", {})}
                       for d in documentos],
        "corpus_texto": {**fc.estatisticas(texto, dup_texto), "amostras": rng.sample(texto, min(5, len(texto)))},
        "corpus_qa": {**fc.estatisticas(qa, dup_qa), **info_qa,
                      "amostras": [{k: i[k] for k in CAMPOS_QA} for i in rng.sample(qa, min(5, len(qa)))]},
        "corpus_chat": {**fc.estatisticas(chat, dup_chat), **info_chat,
                        "recusas": sum(1 for i in chat if i.get("tipo") == "recusa"),
                        "amostras": [{"messages": i["messages"], "fonte": i["fonte"]} for i in rng.sample(chat, min(5, len(chat)))]},
        "revisao_humana": info_revisao,
        "anonimizacao_exemplo": {"antes": EXEMPLO_COLADO, "depois": anonimizado, "mascarados": contagem},
        "geracao": {"modelo": MODELO, "temperatura": 0.2, "chamadas_novas": gerador.chamadas,
                    "prompts": {"perguntas_respostas": PROMPT_QA, "dialogos": PROMPT_CHAT, "recusas": PROMPT_RECUSA}},
        "tokenizador": "tiktoken cl100k_base",
    }
    (saida / "relatorio_qualidade.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    for nome in ("corpus_texto", "corpus_qa", "corpus_chat"):
        r = relatorio[nome]
        print(f"{nome:13} {r['exemplos']:>4} exemplos · média {r['media_tokens']} tokens · {r['duplicatas_removidas']} duplicatas removidas")
    return relatorio


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", type=Path, default=PASTA / "entrada")
    p.add_argument("--saida", type=Path, default=PASTA / "saida")
    a = p.parse_args()
    executar(a.entrada, a.saida)
