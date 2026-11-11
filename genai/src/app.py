"""Interface de teste do Assistente da Jornada (Gradio).

Uso:
  python src/app.py        →   http://127.0.0.1:7860
Para conferir fotos de documentos, deixe a API rodando em http://127.0.0.1:8000.
"""
import gradio as gr

from agente import Assistente

assistente = Assistente()
EXEMPLOS = [
    ["O que eu preciso levar para tirar a nova carteira de identidade?", "idoso"],
    ["Quanto custa renovar a CNH?", "geral"],
    ["Tenho 67 anos e moro sozinha. Como peço o BPC?", "idoso"],
    ["Achei um site que cobra R$ 89 para renovar a CNH. Posso pagar?", "geral"],
    ["Qual unidade está com menos fila agora?", "geral"],
]


def responder(pergunta, perfil, imagem):
    if not pergunta or len(pergunta.strip()) < 3:
        return "Escreva sua pergunta.", ""
    r = assistente.perguntar(pergunta, perfil, imagem)
    detalhes = []
    if r.get("documentos_necessarios"):
        detalhes.append("**Documentos:** " + "; ".join(r["documentos_necessarios"]))
    if r.get("gratuito") is not None:
        detalhes.append("**Gratuito:** " + ("sim" if r["gratuito"] else "não"))
    if r.get("encaminhar_para"):
        detalhes.append(f"**Procure:** {r['encaminhar_para']}")
    if r.get("urls"):
        detalhes.append("**Fontes oficiais:** " + " · ".join(f"[{f}]({u})" for f, u in zip(r["fontes"], r["urls"])))
    detalhes.append(f"_Ferramentas usadas: {', '.join(r.get('ferramentas') or ['nenhuma'])}_")
    return r["resposta"], "\n\n".join(detalhes)


with gr.Blocks(title="Vai de Primeira · Assistente da Jornada") as app:
    gr.Markdown("# Assistente da Jornada\nTire dúvidas sobre **Carteira de Identidade Nacional, renovação da CNH, "
                "Cadastro Único e BPC**. As respostas vêm de páginas oficiais do governo.")
    with gr.Row():
        with gr.Column(scale=3):
            pergunta = gr.Textbox(label="Sua pergunta", lines=2, placeholder="Ex.: o que eu levo para tirar a identidade nova?")
            perfil = gr.Radio(["geral", "idoso", "baixa_escolaridade"], value="geral", label="Como prefere a resposta")
            imagem = gr.Image(type="filepath", label="Foto de um documento (opcional)")
            enviar = gr.Button("Perguntar", variant="primary")
        with gr.Column(scale=4):
            resposta = gr.Textbox(label="Resposta", lines=8, interactive=False)
            detalhes = gr.Markdown()
    gr.Examples(EXEMPLOS, inputs=[pergunta, perfil])
    enviar.click(responder, [pergunta, perfil, imagem], [resposta, detalhes])
    pergunta.submit(responder, [pergunta, perfil, imagem], [resposta, detalhes])

if __name__ == "__main__":
    app.launch()
