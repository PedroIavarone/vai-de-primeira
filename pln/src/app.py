"""Interface da Fábrica de Corpus (Gradio): do upload dos documentos aos três arquivos JSONL.

Uso:
  python src/app.py        →   http://127.0.0.1:7861
"""
import json
import tempfile
from pathlib import Path

import gradio as gr

import fabrica_corpus as fc
from gerar_corpus import executar


def _tabela_documentos(relatorio: dict) -> list[list]:
    linhas = []
    for d in relatorio["documentos"]:
        mascarados = ", ".join(f"{k}: {v}" for k, v in d["anonimizacao"].items()) or "nenhum"
        linhas.append([d["fonte"], d["formato"], d["paginas"], d["tokens_brutos"], d["tokens_limpos"], mascarados])
    return linhas


def _tabela_estatisticas(relatorio: dict) -> list[list]:
    return [[nome.replace("corpus_", ""), r["exemplos"], r["media_tokens"], r["min_tokens"], r["max_tokens"],
             r["duplicatas_removidas"]]
            for nome, r in ((n, relatorio[n]) for n in ("corpus_texto", "corpus_qa", "corpus_chat"))]


def processar(arquivos, texto_colado, gerar):
    documentos = [fc.ler_arquivo(Path(a).name, Path(a).read_bytes()) for a in (arquivos or [])]
    if texto_colado and texto_colado.strip():
        documentos.append(fc.ler_texto_colado(texto_colado))
    if not documentos:
        raise gr.Error("Envie pelo menos um arquivo (PDF, TXT, DOCX ou HTML) ou cole um texto.")
    saida = Path(tempfile.mkdtemp(prefix="corpus_"))
    relatorio = executar(None, saida, documentos=documentos, gerar=gerar, revisao=True)  # aplica revisao/revisao.csv aos exemplos já revisados

    primeiro = documentos[0]
    antes_depois = (f"**Documento:** `{primeiro.fonte}`\n\n**Antes (texto extraído):**\n```\n{primeiro.bruto[:900]}\n```\n"
                    f"**Depois (limpo, normalizado e anonimizado):**\n```\n{primeiro.texto[:900]}\n```")
    colado = next((d for d in documentos if d.formato == "colado"), None)
    if colado:  # mostra a anonimização do próprio texto colado
        antes, depois = colado.bruto, colado.texto
    else:
        exemplo = relatorio["anonimizacao_exemplo"]
        antes, depois = exemplo["antes"], exemplo["depois"]
    anonimizacao = f"**Anonimização · antes:** {antes}\n\n**Depois:** {depois}"
    amostras = {n: relatorio[n]["amostras"] for n in ("corpus_texto", "corpus_qa", "corpus_chat")}
    arquivos_saida = [str(saida / f"{n}.jsonl") for n in ("corpus_texto", "corpus_qa", "corpus_chat")]
    return (_tabela_documentos(relatorio), antes_depois, anonimizacao, _tabela_estatisticas(relatorio),
            json.dumps(amostras, ensure_ascii=False, indent=2), arquivos_saida)


with gr.Blocks(title="Fábrica de Corpus · Vai de Primeira") as app:
    gr.Markdown("# Fábrica de Corpus\nTransforma documentos oficiais sobre **Carteira de Identidade Nacional, CNH, "
                "Cadastro Único e BPC** em corpora limpos e anonimizados para treinar um modelo pequeno.")
    with gr.Row():
        with gr.Column():
            arquivos = gr.File(label="Documentos (PDF, TXT, DOCX ou HTML)", file_count="multiple",
                               file_types=[".pdf", ".txt", ".docx", ".html", ".htm"])
            texto_colado = gr.Textbox(label="Ou cole um texto", lines=5)
            gerar = gr.Checkbox(value=True, label="Gerar perguntas e respostas e diálogos com o LLM (usa o cache quando existir)")
            botao = gr.Button("Gerar corpus", variant="primary")
        with gr.Column():
            baixar = gr.File(label="Corpora gerados (JSONL)", file_count="multiple")
    documentos = gr.Dataframe(headers=["fonte", "formato", "páginas", "tokens antes", "tokens depois", "dados mascarados"],
                              label="Documentos lidos")
    with gr.Row():
        limpeza = gr.Markdown()
        anonimizacao = gr.Markdown()
    estatisticas = gr.Dataframe(headers=["corpus", "exemplos", "média de tokens", "mín.", "máx.", "duplicatas removidas"],
                                label="Relatório de qualidade")
    amostras = gr.Code(label="5 exemplos aleatórios de cada corpus", language="json")
    botao.click(processar, [arquivos, texto_colado, gerar],
                [documentos, limpeza, anonimizacao, estatisticas, amostras, baixar])

if __name__ == "__main__":
    app.launch(server_port=7861)
