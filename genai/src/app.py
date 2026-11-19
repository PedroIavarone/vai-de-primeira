"""Interface de teste do Assistente da Jornada (Gradio), com a identidade visual do Vai de Primeira.

Uso:
  python src/app.py        →   http://127.0.0.1:7860
Para conferir fotos de documentos, deixe a API rodando em http://127.0.0.1:8000.
"""
import html
from urllib.parse import urlparse

import gradio as gr

from agente import Assistente

assistente = Assistente()

# Perguntas de exemplo, mostradas como atalhos acima do campo.
ATALHOS = [
    ("O que levo para a identidade?", "O que eu preciso levar para tirar a nova carteira de identidade?"),
    ("Quanto custa renovar a CNH?", "Quanto custa renovar a CNH?"),
    ("Como peço o BPC?", "Tenho 67 anos e moro sozinha. Como peço o BPC?"),
    ("Qual unidade tem menos fila?", "Qual unidade está com menos fila agora?"),
]

# Perfis com nome de gente; o valor interno continua o mesmo do agente.
PERFIS = [
    ("Padrão · completa, com fontes", "geral"),
    ("Pessoa idosa · passo a passo, sem pressa", "idoso"),
    ("Linguagem simples · frases curtas", "baixa_escolaridade"),
]

# ---------------------------------------------------------------- identidade visual (mesmos tokens do app)
TEMA = gr.themes.Base(
    primary_hue=gr.themes.Color(c50="#e8f0fb", c100="#d3e2f6", c200="#a9c5ec", c300="#7ea7e1", c400="#4f84cc",
                                c500="#1f5fad", c600="#1b549a", c700="#174a87", c800="#123a6b", c900="#0e2c52",
                                c950="#0a1f3a"),
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Atkinson Hyperlegible"), "Arial", "sans-serif"],
    radius_size="lg",
).set(
    body_background_fill="#f2f4f7",
    block_background_fill="#ffffff",
    block_border_color="#d0d5dd",
    block_label_text_color="#1f2933",
    body_text_color="#1f2933",
    button_primary_background_fill="#1f5fad",
    button_primary_background_fill_hover="#174a87",
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="#ffffff",
    button_secondary_border_color="#1f5fad",
    button_secondary_text_color="#1f5fad",
    input_background_fill="#ffffff",
)

LOGO = ('<svg class="logo" viewBox="0 0 116 116" width="52" height="52" role="img" aria-label="Vai de Primeira">'
        '<rect x="8" y="8" width="100" height="100" rx="24" fill="#FFFFFF"/>'
        '<path d="M32 60 L52 80 L86 38" fill="none" stroke="#1F5FAD" stroke-width="13" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>')

CSS = """
#topo { display: flex; align-items: center; gap: 18px; } #topo .logo { flex: none; } #topo .marca { font-size: 13px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: #d3e2f6; margin: 0 0 2px; }
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; font-size: 17px; }
#topo { background: #1f5fad; color: #fff; border-radius: 16px; padding: 22px 28px; }
#topo h1 { color: #fff; margin: 0; font-size: 30px; }
#topo p { color: #e8f0fb; margin: 6px 0 0; font-size: 17px; }
.atalho { border: 1.5px solid #1f5fad !important; border-radius: 999px !important; font-size: 15px !important; color: #1f5fad !important; background: #fff !important; }
.atalho:hover { background: #e8f0fb !important; }
#resposta-card { background: #fff; border: 1px solid #d0d5dd; border-radius: 16px; padding: 22px 24px; min-height: 260px; }
.r-selo { display: inline-block; font-weight: 700; font-size: 14px; padding: 3px 12px; border-radius: 999px; border: 1.5px solid; margin-bottom: 10px; }
.r-gratis { color: #1e7f4f; } .r-custo { color: #a84a08; }
.r-texto { font-size: 18px; line-height: 1.55; color: #1f2933; }
.r-titulo { font-weight: 700; margin: 14px 0 6px; color: #1f2933; }
.r-lista { margin: 0; padding-left: 22px; } .r-lista li { margin-bottom: 4px; }
.r-procure { margin-top: 12px; background: #e8f0fb; border-radius: 10px; padding: 10px 14px; }
.r-fontes { margin-top: 14px; font-size: 15px; } .r-fontes a { color: #1f5fad; font-weight: 700; margin-right: 14px; }
.r-rodape { margin-top: 12px; font-size: 14px; color: #667085; }
.r-vazio { color: #667085; font-size: 17px; }
"""

# O Gradio segue o tema escuro do sistema; o assistente fica sempre claro, como o app.
JS_CLARO = "() => { document.body.classList.remove('dark'); }"

VAZIO = "<div class='r-vazio'>A resposta aparece aqui, com o que levar, se é grátis e o site oficial.</div>"


def site(url):
    return urlparse(url).hostname.replace("www.", "") if url else ""


def cartao(r):
    """Monta a resposta: selo de custo, texto, o que levar, onde procurar e as fontes oficiais."""
    partes = []
    if r.get("gratuito") is not None:
        partes.append(f"<span class='r-selo {'r-gratis' if r['gratuito'] else 'r-custo'}'>"
                      f"{'Grátis' if r['gratuito'] else 'Tem custo'}</span>")
    partes.append(f"<div class='r-texto'>{html.escape(r['resposta'])}</div>")
    if r.get("documentos_necessarios"):
        itens = "".join(f"<li>{html.escape(d)}</li>" for d in r["documentos_necessarios"])
        partes.append(f"<div class='r-titulo'>Leve:</div><ul class='r-lista'>{itens}</ul>")
    if r.get("encaminhar_para"):
        partes.append(f"<div class='r-procure'><b>Onde:</b> {html.escape(r['encaminhar_para'])}</div>")
    if r.get("urls"):
        links = "".join(f"<a href='{html.escape(u)}' target='_blank' rel='noopener'>↗ {html.escape(site(u))}</a>"
                        for u in r["urls"] if u)
        partes.append(f"<div class='r-fontes'><b>Fontes oficiais:</b> {links}</div>")
    partes.append(f"<div class='r-rodape'>Ferramentas usadas: {html.escape(', '.join(r.get('ferramentas') or ['nenhuma']))}</div>")
    return "".join(partes)


def responder(pergunta, perfil, imagem):
    if not pergunta or len(pergunta.strip()) < 3:
        return "<div class='r-vazio'>Escreva sua pergunta.</div>"
    return cartao(assistente.perguntar(pergunta, perfil, imagem))


with gr.Blocks(title="Vai de Primeira · Assistente da Jornada") as app:
    gr.HTML(f"<div id='topo'>{LOGO}<div><p class='marca'>Vai de Primeira</p><h1>Assistente da Jornada</h1>"
            "<p>Identidade · CNH · Cadastro Único · BPC · respostas de páginas oficiais do governo</p></div></div>")
    with gr.Row():
        with gr.Column(scale=5):
            with gr.Row():
                botoes = [gr.Button(rotulo, size="sm", variant="secondary", elem_classes="atalho") for rotulo, _ in ATALHOS]
            pergunta = gr.Textbox(label="Sua pergunta", lines=2, placeholder="Ex.: o que eu levo para tirar a identidade nova?")
            perfil = gr.Radio(PERFIS, value="geral", label="Como prefere a resposta?")
            imagem = gr.Image(type="filepath", label="Foto de um documento (opcional)",
                              placeholder="Arraste aqui, escolha um arquivo ou use a câmera", sources=["upload", "webcam"])
            enviar = gr.Button("Perguntar", variant="primary", size="lg")
        with gr.Column(scale=6):
            gr.Markdown("**Resposta**")
            resposta = gr.HTML(VAZIO, elem_id="resposta-card")
    for botao, (_, texto) in zip(botoes, ATALHOS):
        botao.click(lambda t=texto: t, None, pergunta)
    enviar.click(responder, [pergunta, perfil, imagem], resposta)
    pergunta.submit(responder, [pergunta, perfil, imagem], resposta)

if __name__ == "__main__":
    app.launch(theme=TEMA, css=CSS, js=JS_CLARO)
