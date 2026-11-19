"""Interface da Fábrica de Corpus (Gradio): do upload dos documentos aos três arquivos JSONL.

Uso:
  python src/app.py        →   http://127.0.0.1:7861
No Colab, o notebook abre a mesma interface com app.launch(share=True, **VISUAL).
"""
import html
import json
import re
import tempfile
from pathlib import Path

import gradio as gr

import fabrica_corpus as fc
from gerar_corpus import executar

# ---------------------------------------------------------------- identidade visual (mesmos tokens do app)
TEMA = gr.themes.Base(
    primary_hue=gr.themes.Color(c50="#e8f0fb", c100="#d3e2f6", c200="#a9c5ec", c300="#7ea7e1", c400="#4f84cc",
                                c500="#1f5fad", c600="#1b549a", c700="#174a87", c800="#123a6b", c900="#0e2c52",
                                c950="#0a1f3a"),
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Atkinson Hyperlegible"), "Arial", "sans-serif"],
    radius_size="lg",
).set(
    body_background_fill="#f2f4f7", block_background_fill="#ffffff", block_border_color="#d0d5dd",
    body_text_color="#1f2933", block_label_text_color="#1f2933", input_background_fill="#ffffff",
    button_primary_background_fill="#1f5fad", button_primary_background_fill_hover="#174a87",
    button_primary_text_color="#ffffff",
)

LOGO = ('<svg class="logo" viewBox="0 0 116 116" width="52" height="52" role="img" aria-label="Vai de Primeira">'
        '<rect x="8" y="8" width="100" height="100" rx="24" fill="#FFFFFF"/>'
        '<path d="M32 60 L52 80 L86 38" fill="none" stroke="#1F5FAD" stroke-width="13" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>')

CSS = """
#topo .identidade { display: flex; align-items: center; gap: 16px; } #topo .logo { flex: none; } #topo .marca { font-size: 13px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: #d3e2f6; margin: 0 0 2px; }
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; font-size: 16px; }
#topo { background: #1f5fad; color: #fff; border-radius: 16px; padding: 18px 24px; display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
#topo h1 { color: #fff; margin: 0; font-size: 26px; } #topo p { color: #e8f0fb; margin: 2px 0 0; }
.etapas { margin-left: auto; display: flex; gap: 8px; align-items: center; font-weight: 700; }
.etapa { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: rgba(255,255,255,.14); }
.etapa i { font-style: normal; width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; background: rgba(255,255,255,.25); font-size: 14px; }
.etapa.feita i { background: #1e7f4f; } .etapa.atual { background: #fff; color: #1f5fad; } .etapa.atual i { background: #1f5fad; color: #fff; }
.seta-etapa { opacity: .7; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.kpi { background: #fff; border: 1px solid #d0d5dd; border-radius: 14px; padding: 16px 18px; }
.kpi .t { color: #667085; font-size: 15px; } .kpi .v { font-size: 40px; font-weight: 700; color: #1f5fad; line-height: 1.1; } .kpi .d { color: #667085; font-size: 14px; }
.kpi.ok { background: #eef8f2; border-color: #1e7f4f; } .kpi.ok .v { color: #1e7f4f; }
.kpi.alerta { background: #fdf1f0; border-color: #b42318; } .kpi.alerta .v { color: #b42318; }
.cartao { background: #fff; border: 1px solid #d0d5dd; border-radius: 14px; padding: 16px 18px; }
.cartao h3 { margin: 0 0 10px; font-size: 18px; }
.cartao table { width: 100%; border-collapse: collapse; font-size: 15px; }
.cartao th { text-align: left; color: #667085; font-weight: 700; padding: 6px 8px; border-bottom: 1px solid #d0d5dd; }
.cartao td { padding: 8px; border-bottom: 1px solid #eef0f3; }
.chip { display: inline-block; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; border: 1.5px solid #1f5fad; color: #1f5fad; text-transform: uppercase; }
.chip.pdf { border-color: #a84a08; color: #a84a08; }
.menos { color: #1e7f4f; font-weight: 700; }
.amostra { border: 1px solid #d0d5dd; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; font-size: 15px; }
.amostra.recusa { background: #fdf1f0; border-color: #f3c6c1; }
.abaixo { float: right; font-size: 13px; font-weight: 700; color: #a84a08; border: 1.5px solid #a84a08; border-radius: 999px; padding: 2px 10px; }
.pronto { float: right; font-size: 13px; font-weight: 700; color: #1e7f4f; border: 1.5px solid #1e7f4f; border-radius: 999px; padding: 2px 10px; }
.vazio { color: #667085; }
"""

JS_CLARO = "() => { document.body.classList.remove('dark'); }"
VISUAL = {"theme": TEMA, "css": CSS, "js": JS_CLARO}

PADROES_PESSOAIS = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}|[\w.+-]+@[\w-]+\.[\w.]+|\(?\d{2}\)?\s?9\d{4}-\d{4}")


def topo(etapa_atual: int) -> str:
    nomes = ["Enviar", "Processar", "Revisar"]
    itens = []
    for n, nome in enumerate(nomes, 1):
        classe = "feita" if n < etapa_atual else "atual" if n == etapa_atual else ""
        marca = "✓" if n < etapa_atual else str(n)
        itens.append(f"<span class='etapa {classe}'><i>{marca}</i>{nome}</span>")
    return (f"<div id='topo'><div class='identidade'>{LOGO}<div><p class='marca'>Vai de Primeira</p><h1>Fábrica de Corpus</h1><p>documentos oficiais → corpus limpo e anonimizado</p></div></div>"
            f"<div class='etapas'>{'<span class=seta-etapa>→</span>'.join(itens)}</div></div>")


def kpis(rel: dict, n_docs: int, gerou: bool, restantes: int) -> str:
    qa, chat = rel["corpus_qa"], rel["corpus_chat"]
    cartoes = [
        ("Trechos limpos", rel["corpus_texto"]["exemplos"], f"de {n_docs} documento{'s' if n_docs != 1 else ''}", ""),
        ("Pares pergunta e resposta", qa["exemplos"], "gerados pelo LLM · cache" if gerou else "geração desligada", ""),
        ("Diálogos", chat["exemplos"], f"{chat.get('recusas', 0)} deles são recusas" if gerou else "geração desligada", ""),
        ("Dados pessoais restantes", restantes, "CPF, e-mail e telefone conferidos nos arquivos", "ok" if restantes == 0 else "alerta"),
    ]
    return "<div class='kpis'>" + "".join(
        f"<div class='kpi {c}'><div class='t'>{t}</div><div class='v'>{v}</div><div class='d'>{d}</div></div>"
        for t, v, d, c in cartoes) + "</div>"


def milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def tabela_documentos(rel: dict) -> str:
    linhas = []
    for d in rel["documentos"]:
        antes, depois = d["tokens_brutos"], d["tokens_limpos"]
        queda = round(100 * (antes - depois) / antes) if antes else 0
        reducao = f"−{queda}%" if queda > 0 else "0%"
        tipos = d["anonimizacao"]
        mascarados = (f"<b>{sum(tipos.values())}</b> <span class='menos'>" + " · ".join(f"{k.lower()} {v}" for k, v in tipos.items()) + "</span>") if tipos else "0"
        linhas.append(f"<tr><td>{html.escape(d['fonte'])}</td><td><span class='chip {d['formato']}'>{d['formato']}</span></td>"
                      f"<td>{d['paginas']}</td><td>{milhar(antes)} → <b>{milhar(depois)}</b> <span class='menos'>{reducao}</span></td>"
                      f"<td>{mascarados}</td></tr>")
    return ("<div class='cartao'><h3>Documentos lidos</h3><table><tr><th>Fonte</th><th>Formato</th><th>Págs.</th>"
            "<th>Tokens antes → depois</th><th>Mascarados</th></tr>" + "".join(linhas) + "</table></div>")


def painel_amostras(rel: dict) -> str:
    blocos = []
    for a in rel["corpus_qa"]["amostras"][:2]:
        blocos.append(f"<div class='amostra'><b>P:</b> {html.escape(a['instruction'])}<br><b>R:</b> {html.escape(a['output'])}</div>")
    for c in rel["corpus_chat"]["amostras"]:
        usuario = next((m["content"] for m in c["messages"] if m["role"] == "user"), "")
        atendente = next((m["content"] for m in c["messages"] if m["role"] == "assistant"), "")
        if any(p in atendente.lower() for p in ("não posso", "nao posso", "procure", "recomendo")):
            blocos.append(f"<div class='amostra recusa'><b>Recusa:</b> “{html.escape(usuario)}”<br>{html.escape(atendente[:220])}</div>")
            break
    corpo = "".join(blocos) or "<p class='vazio'>Ligue a geração para ver perguntas e diálogos.</p>"
    return f"<div class='cartao'><h3>Amostra · pares e recusa</h3>{corpo}</div>"


def tabela_qualidade(rel: dict) -> str:
    nomes = {"corpus_texto": "trechos", "corpus_qa": "pares P&R", "corpus_chat": "diálogos"}
    linhas = "".join(
        f"<tr><td>{nomes[n]}</td><td>{rel[n]['exemplos']}</td><td>{rel[n]['media_tokens']}</td><td>{rel[n]['min_tokens']}</td>"
        f"<td>{rel[n]['max_tokens']}</td><td>{rel[n]['duplicatas_removidas']}</td></tr>".replace(".", ",")
        for n in nomes)
    minimos = {"corpus_texto": 50, "corpus_qa": 100, "corpus_chat": 30}
    atingiu = all(rel[n]["exemplos"] >= m for n, m in minimos.items())
    selo = ("<span class='pronto'>Mínimos atingidos · pronto para treinar</span>" if atingiu
            else "<span class='abaixo'>Abaixo do mínimo (50 trechos, 100 pares, 30 diálogos)</span>")
    return (f"<div class='cartao'><h3>Relatório de qualidade {selo}</h3>"
            "<table><tr><th>Corpus</th><th>Exemplos</th><th>Média de tokens</th><th>Mín.</th><th>Máx.</th>"
            "<th>Duplicatas removidas</th></tr>" + linhas + "</table></div>")


def processar(arquivos, texto_colado, gerar):
    documentos = [fc.ler_arquivo(Path(a).name, Path(a).read_bytes()) for a in (arquivos or [])]
    if texto_colado and texto_colado.strip():
        documentos.append(fc.ler_texto_colado(texto_colado))
    if not documentos:
        raise gr.Error("Envie pelo menos um arquivo (PDF, TXT, DOCX ou HTML) ou cole um texto.")
    saida = Path(tempfile.mkdtemp(prefix="corpus_"))
    relatorio = executar(None, saida, documentos=documentos, gerar=gerar, revisao=True)  # aplica revisao/revisao.csv aos exemplos já revisados

    arquivos_saida = [str(saida / f"{n}.jsonl") for n in ("corpus_texto", "corpus_qa", "corpus_chat")]
    restantes = sum(len(PADROES_PESSOAIS.findall(Path(a).read_text(encoding="utf-8"))) for a in arquivos_saida)

    primeiro = documentos[0]
    antes_depois = (f"**Limpeza · documento `{primeiro.fonte}`**\n\n**Antes (texto extraído):**\n```\n{primeiro.bruto[:900]}\n```\n"
                    f"**Depois (limpo, normalizado e anonimizado):**\n```\n{primeiro.texto[:900]}\n```")
    colado = next((d for d in documentos if d.formato == "colado"), None)
    if colado:  # mostra a anonimização do próprio texto colado
        antes, depois = colado.bruto, colado.texto
    else:
        exemplo = relatorio["anonimizacao_exemplo"]
        antes, depois = exemplo["antes"], exemplo["depois"]
    anonimizacao = f"**Anonimização · antes:** {antes}\n\n**Depois:** {depois}"
    return (topo(3), kpis(relatorio, len(documentos), gerar, restantes), tabela_documentos(relatorio),
            painel_amostras(relatorio), tabela_qualidade(relatorio), antes_depois, anonimizacao, arquivos_saida,
            *[json.dumps(relatorio[n]["amostras"], ensure_ascii=False, indent=2)
              for n in ("corpus_texto", "corpus_qa", "corpus_chat")])


with gr.Blocks(title="Fábrica de Corpus · Vai de Primeira") as app:
    cabecalho = gr.HTML(topo(1))
    with gr.Row():
        with gr.Column(scale=3):
            arquivos = gr.File(label="Documentos (PDF, TXT, DOCX ou HTML)", file_count="multiple",
                               file_types=[".pdf", ".txt", ".docx", ".html", ".htm"])
            texto_colado = gr.Textbox(label="Ou cole um texto", lines=4)
            gerar = gr.Checkbox(value=True, label="Gerar perguntas e respostas e diálogos com o LLM (usa o cache quando existir)")
            botao = gr.Button("Gerar corpus", variant="primary", size="lg")
        with gr.Column(scale=5):
            numeros = gr.HTML("<p class='vazio'>Envie os documentos e clique em <b>Gerar corpus</b>. Os números aparecem aqui.</p>")
    with gr.Row():
        with gr.Column(scale=5):
            documentos = gr.HTML()
            baixar = gr.File(label="⬇ Baixar corpora (JSONL)", file_count="multiple")
        with gr.Column(scale=3):
            amostras = gr.HTML()
    qualidade = gr.HTML()
    with gr.Accordion("Antes e depois da limpeza e da anonimização", open=True):
        with gr.Row():
            limpeza = gr.Markdown()
            anonimizacao = gr.Markdown()
    with gr.Accordion("5 exemplos aleatórios de cada corpus", open=True):
        with gr.Tabs():
            with gr.Tab("Texto puro"):
                aleat_texto = gr.Code(language="json", label="corpus_texto.jsonl")
            with gr.Tab("Perguntas e respostas"):
                aleat_qa = gr.Code(language="json", label="corpus_qa.jsonl")
            with gr.Tab("Diálogos"):
                aleat_chat = gr.Code(language="json", label="corpus_chat.jsonl")
    botao.click(lambda: topo(2), None, cabecalho).then(
        processar, [arquivos, texto_colado, gerar],
        [cabecalho, numeros, documentos, amostras, qualidade, limpeza, anonimizacao, baixar, aleat_texto, aleat_qa, aleat_chat])

if __name__ == "__main__":
    app.launch(server_port=7861, **VISUAL)
