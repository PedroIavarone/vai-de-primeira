"""Painel do gestor do Vai de Primeira (Business Analytics).

Junta num HTML só os dados que os módulos já produzem e uma amostra simulada de atendimentos:

  dados reais dos módulos
    rpa/saida/relatorios/       avisos do robô por região e tipo, revisão humana
    iot/dados/iot.sqlite        leituras da fila e alertas do totem (quando existir)
    */resultados, */avaliacao   métricas dos modelos (visão, assistente, PLN, robô)
  dados simulados (marcados no painel)
    atendimentos.csv            1.200 idas à unidade, com o Índice de Prontidão calculado pela
                                regra real (api/prontidao.py) e o resultado da ida

Uso:  python gerar_painel.py      →  painel.html e atendimentos.csv nesta pasta
"""
import csv
import json
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "api"))
import prontidao  # noqa: E402

AZUL, VERDE, LARANJA, VERMELHO, CINZA = "#1F5FAD", "#1E7F4F", "#A84A08", "#B42318", "#667085"
SEMENTE = 2026

# ---------------------------------------------------------------- atendimentos simulados
REGIOES = {
    # região: (unidades de atendimento, distância média até a unidade em min, chance de já ter sido orientado)
    "Grande SP": (2, 35, 0.55),
    "Zona Leste SP": (1, 50, 0.45),
    "Zona Sul SP": (1, 45, 0.45),
    "Sorocaba": (1, 60, 0.40),
    "Sudoeste Paulista": (1, 95, 0.25),
}
SERVICOS = {"cin": "Identidade (CIN)", "cnh": "Renovação da CNH", "cadunico": "Cadastro Único"}
FAIXAS = {"pronta": "Pronta", "quase": "Quase", "nao_pronta": "Não pronta"}


def simular_atendimentos(n=1200):
    """Cada linha é uma ida à unidade. O índice usa a regra real; o resultado da ida é sorteado com
    chance que cresce com o índice (premissa do modelo, explicada no painel)."""
    rng = random.Random(SEMENTE)
    linhas = []
    for i in range(n):
        regiao = rng.choices(list(REGIOES), weights=[30, 18, 17, 20, 15])[0]
        unidades, distancia, p_orientado = REGIOES[regiao]
        servico = rng.choice(list(SERVICOS))
        usou_app = rng.random() < 0.5
        orientado = rng.random() < (0.9 if usou_app else p_orientado)
        documentos = []
        for tipo in prontidao.OBRIGATORIOS[servico]:
            # quem usou o app conferiu a foto e corrigiu a maioria dos problemas antes de sair
            levou = rng.random() < (0.95 if usou_app else 0.75 if orientado else 0.6)
            if levou:
                ruim = rng.random() < (0.05 if usou_app else 0.25)
                documentos.append({"tipo": tipo, "qualidade": rng.choice(["reflexo", "borrado", "cortado"]) if ruim else "ok"})
        espera = max(3, int(rng.gauss(55 if unidades == 1 else 30, 18)))
        r = prontidao.calcular(servico, documentos, espera, orientado)
        resolveu = rng.random() < {"pronta": 0.93, "quase": 0.62, "nao_pronta": 0.25}[r["faixa"]]
        motivo = ""
        if not resolveu:
            faltou = [d for d in prontidao.OBRIGATORIOS[servico] if d not in {x["tipo"] for x in documentos}]
            ilegivel = [x for x in documentos if x["qualidade"] != "ok"]
            if faltou:
                motivo = "Documento faltando"
            elif ilegivel:
                motivo = "Documento ilegível ou danificado"
            elif espera > 45:
                motivo = "Desistiu pela espera"
            else:
                motivo = "Outro (sistema, horário, regra)"
        linhas.append({"id": f"A{i:04d}", "regiao": regiao, "servico": servico, "usou_app": usou_app,
                       "indice": r["indice"], "faixa": r["faixa"], "espera_min": espera,
                       "deslocamento_min": max(10, int(rng.gauss(distancia, distancia * 0.25))),
                       "resolveu": resolveu, "motivo": motivo})
    with open(AQUI / "atendimentos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    return linhas


# ---------------------------------------------------------------- dados reais dos módulos
def ler_robo():
    pasta = RAIZ / "rpa" / "saida" / "relatorios"
    execucoes = sorted(pasta.glob("execucao_*.json")) if pasta.exists() else []
    # usa a execução com mais envios (a primeira do dia; as seguintes só pulam quem já foi avisado)
    melhor = max(execucoes, key=lambda p: json.loads(p.read_text()).get("situacao: enviado", 0), default=None)
    if not melhor:
        return None
    resumo = json.loads(melhor.read_text())
    import openpyxl
    planilha = pasta / f"demanda_{resumo['execucao']}.xlsx"
    regioes = {}
    if planilha.exists():
        aba = openpyxl.load_workbook(planilha, read_only=True)["Demanda por região"]
        linhas = list(aba.iter_rows(values_only=True))
        cab = linhas[0]
        for l in linhas[1:]:
            if l[0] and l[0] != "Total":
                regioes[l[0]] = dict(zip(cab[1:], l[1:]))
    return {"resumo": resumo, "regioes": regioes}


def ler_iot():
    banco = RAIZ / "iot" / "dados" / "iot.sqlite"
    if not banco.exists():
        return None
    with sqlite3.connect(banco) as con:
        leituras = con.execute("SELECT count(*), max(pessoas), max(espera_min) FROM leituras_fila").fetchone()
        alertas = Counter(t for (t,) in con.execute("SELECT tipo FROM alertas"))
        descartes = con.execute("SELECT count(*) FROM descartes").fetchone()[0]
    return {"leituras": leituras[0], "max_pessoas": leituras[1], "max_espera": leituras[2],
            "alertas": dict(alertas), "descartes": descartes}


def ler_json(caminho):
    p = RAIZ / caminho
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---------------------------------------------------------------- painel
def kpi(titulo, valor, detalhe, cor=AZUL):
    return (f'<div class="kpi"><div class="kpi-t">{titulo}</div><div class="kpi-v" style="color:{cor}">{valor}</div>'
            f'<div class="kpi-d">{detalhe}</div></div>')


def figura_html(fig, altura=360):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Atkinson Hyperlegible, Arial", size=13, color="#1F2933"),
                      paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-0.15))
    fig.update_xaxes(gridcolor="#EEF0F3")
    fig.update_yaxes(gridcolor="#EEF0F3")
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


def main():
    at = simular_atendimentos()
    robo = ler_robo()
    iot = ler_iot()
    genai = ler_json("genai/avaliacao/resultados.json")
    visao = ler_json("visao/resultados/ponta_a_ponta.json")
    visao_campo = ler_json("visao/resultados/teste_campo.json")
    pln = ler_json("pln/saida/relatorio_qualidade.json")
    rpa_val = ler_json("rpa/validacao/resultado.json")

    total = len(at)
    resolvidos = sum(a["resolveu"] for a in at)
    com_app = [a for a in at if a["usou_app"]]
    sem_app = [a for a in at if not a["usou_app"]]
    taxa = lambda xs: sum(a["resolveu"] for a in xs) / len(xs)
    viagens_perdidas_evitaveis = round((taxa(com_app) - taxa(sem_app)) * len(sem_app))

    # 1. prontidão média por região e serviço
    regioes = list(REGIOES)
    media = defaultdict(list)
    for a in at:
        media[(a["regiao"], a["servico"])].append(a["indice"])
    fig1 = go.Figure()
    for s, nome in SERVICOS.items():
        fig1.add_bar(name=nome, x=regioes, y=[round(sum(media[(r, s)]) / len(media[(r, s)])) for r in regioes])
    fig1.update_layout(title="Índice de Prontidão médio na chegada, por região e serviço", barmode="group",
                       colorway=[AZUL, "#5B8FD0", "#A9C4E8"], yaxis=dict(range=[0, 100], title="índice (0 a 100)"))

    # 2. motivos de recusa
    motivos = Counter(a["motivo"] for a in at if not a["resolveu"])
    ordem = motivos.most_common()
    fig2 = go.Figure(go.Bar(x=[v for _, v in ordem][::-1], y=[m for m, _ in ordem][::-1], orientation="h", marker_color=VERMELHO))
    fig2.update_layout(title="Motivos de quem voltou sem resolver", xaxis_title="idas perdidas")

    # 3. resolução por faixa e uso do app
    fig3 = go.Figure()
    for grupo, nome, cor in ((com_app, "Usou o app antes", AZUL), (sem_app, "Não usou", CINZA)):
        fig3.add_bar(name=nome, x=list(FAIXAS.values()),
                     y=[round(100 * taxa([a for a in grupo if a["faixa"] == f]) if any(a["faixa"] == f for a in grupo) else 0) for f in FAIXAS],
                     marker_color=cor)
    fig3.update_layout(title="Resolveu na primeira ida (%), por faixa do índice", barmode="group", yaxis=dict(range=[0, 100]))

    # 4. desertos de atendimento: demanda do robô x unidades x deslocamento
    demanda = {r: (robo["regioes"].get(r, {}).get("Total", 0) if robo else 0) for r in regioes}
    deslocamento = {r: sum(a["deslocamento_min"] for a in at if a["regiao"] == r) / max(1, sum(a["regiao"] == r for a in at)) for r in regioes}
    fig4 = go.Figure(go.Scatter(
        x=[deslocamento[r] for r in regioes], y=[demanda[r] / REGIOES[r][0] for r in regioes], text=regioes,
        mode="markers+text", textposition="top center",
        marker=dict(size=[18 + demanda[r] for r in regioes], color=[VERMELHO if deslocamento[r] > 70 else AZUL for r in regioes], opacity=0.75)))
    fig4.update_layout(title="Desertos de atendimento: demanda por unidade x deslocamento",
                       xaxis_title="deslocamento médio até a unidade (min)", yaxis_title="avisos do robô por unidade")

    # 5. avisos do robô por região e tipo
    fig5 = go.Figure()
    if robo:
        tipos = [t for t in next(iter(robo["regioes"].values())) if t != "Total"]
        for t, cor in zip(tipos, [AZUL, "#5B8FD0", VERDE, "#7FB89A", LARANJA, VERMELHO]):
            fig5.add_bar(name=t, x=regioes, y=[robo["regioes"].get(r, {}).get(t, 0) for r in regioes], marker_color=cor)
    fig5.update_layout(title="Avisos do robô por região (execução diária)", barmode="stack")

    # 6. fila por hora (curva usada pela API) com leituras reais do totem
    sys.path.insert(0, str(RAIZ / "api"))
    import simulacao
    from datetime import datetime
    horas = list(range(8, 18))
    fig6 = go.Figure()
    for u in simulacao.UNIDADES:
        esperas = []
        for h in horas:
            f = simulacao.fila_agora(datetime(2026, 11, 18, h, 30))
            esperas.append(next(x["espera_min"] for x in f["unidades"] if x["id"] == u["id"]))
        fig6.add_scatter(x=[f"{h}h" for h in horas], y=esperas, name=u["nome"], mode="lines+markers")
    fig6.add_hline(y=45, line_dash="dash", line_color=VERMELHO, annotation_text="fila cheia")
    fig6.update_layout(title="Espera estimada por unidade ao longo do dia", yaxis_title="min", colorway=[AZUL, VERDE, LARANJA])

    # tabela de desempenho dos modelos
    linhas_modelos = []
    if visao:
        linhas_modelos.append(("Conferência por foto (visão)", f"{visao['acerto_geral']:.0%} de ponta a ponta em {visao['fotos_teste']} fotos de teste (MIDV-2020)",
                               f"{visao_campo['resumo']['detectados_no_limiar']} de {visao_campo['resumo']['imagens']} no teste com documentos brasileiros" if visao_campo else "teste com documentos brasileiros pendente"))
    if genai:
        rs = genai["resumo"]
        linhas_modelos.append(("Assistente (RAG + agente)", f"{rs['acerto_geral']:.1%} de acerto em {rs['total']} perguntas · fonte certa {rs['fonte_correta']:.0%}",
                               f"fidelidade à fonte {rs['fidelidade_a_fonte']:.1%} · {rs['caminho_seguro_usado']} resposta segura"))
    if pln:
        linhas_modelos.append(("Corpus para ajuste fino (PLN)", f"{pln['corpus_qa']['exemplos']} pares e {pln['corpus_chat']['exemplos']} diálogos",
                               f"{pln['corpus_qa'].get('rejeitados_sem_evidencia', 0)} pares descartados sem evidência · revisão humana de 20%"))
    if rpa_val:
        linhas_modelos.append(("Robô de avisos (RPA)", f"{rpa_val['acertos']} de {rpa_val['casos']} casos rotulados",
                               f"{robo['resumo']['revisao_humana']} casos para revisão humana na última execução" if robo else ""))
    tabela = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in linhas_modelos)

    kpis = "".join([
        kpi("Resolveu na primeira ida", f"{resolvidos / total:.0%}", f"{resolvidos} de {total} idas (simulado)"),
        kpi("Com o app x sem o app", f"{taxa(com_app):.0%} x {taxa(sem_app):.0%}", f"simulado: ≈ {viagens_perdidas_evitaveis} viagens perdidas a menos, se as premissas se confirmarem", VERDE),
        kpi("Avisos enviados pelo robô", f"{robo['resumo'].get('situacao: enviado', 0)}" if robo else "–",
            f"{robo['resumo']['com_aviso']} pessoas com aviso · {robo['resumo']['revisao_humana']} para revisão humana" if robo else ""),
        kpi("Totem da unidade", f"{iot['leituras']} leituras" if iot else "–",
            f"{sum(iot['alertas'].values())} alertas · {iot['descartes']} leituras inválidas descartadas" if iot else "sem dados do totem", LARANJA),
    ])

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel do gestor · Vai de Primeira</title>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<style>
 body {{ margin:0; font-family:"Atkinson Hyperlegible",Arial,sans-serif; background:#F2F4F7; color:#1F2933; }}
 header {{ background:{AZUL}; color:#fff; padding:16px 24px; }}
 header h1 {{ margin:0; font-size:1.5rem; }} header p {{ margin:4px 0 0; opacity:.9; }}
 main {{ max-width:1280px; margin:0 auto; padding:20px; }}
 .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:14px; margin-bottom:16px; }}
 .kpi, .card {{ background:#fff; border:1px solid #D0D5DD; border-radius:12px; padding:14px 16px; }}
 .kpi-t {{ color:#667085; font-size:.95rem; }} .kpi-v {{ font-size:2rem; font-weight:700; }} .kpi-d {{ font-size:.9rem; color:#667085; }}
 .grade {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(560px,1fr)); gap:14px; margin-bottom:14px; }}
 table {{ width:100%; border-collapse:collapse; }} td, th {{ text-align:left; padding:8px; border-bottom:1px solid #EEF0F3; vertical-align:top; }}
 .nota {{ font-size:.9rem; color:#667085; }}
 .selo {{ display:inline-block; border:2px solid {LARANJA}; color:{LARANJA}; border-radius:999px; padding:0 10px; font-weight:700; font-size:.85rem; }}
</style></head><body>
<header><h1>Painel do gestor · Vai de Primeira</h1>
<p>Onde as pessoas perdem viagem, por quê, e para onde levar a unidade móvel. Nenhum dado pessoal: só contagens por região.</p></header>
<main>
<div class="kpis">{kpis}</div>
<div class="grade"><div class="card">{figura_html(fig1)}</div><div class="card">{figura_html(fig2)}</div></div>
<div class="grade"><div class="card">{figura_html(fig3)}</div><div class="card">{figura_html(fig4)}</div></div>
<div class="grade"><div class="card">{figura_html(fig5)}</div><div class="card">{figura_html(fig6)}</div></div>
<div class="card"><h2 style="margin-top:0">Desempenho dos modelos e revisão humana</h2>
<table><tr><th>Módulo</th><th>Resultado</th><th>Controle</th></tr>{tabela}</table>
<p class="nota">A IA faz triagem. Documento é conferido pelo atendente, direito a benefício é decidido pelo órgão responsável e toda sinalização de BPC passa por revisão humana.</p></div>
<p class="nota"><span class="selo">simulado</span> Os gráficos de prontidão, motivos e resolução usam {total} idas simuladas
(governanca/painel/atendimentos.csv). O Índice de Prontidão de cada ida é calculado pela regra real da API; a chance de resolver
em cada faixa (93%, 62% e 25%) é uma premissa a ser medida no piloto. Os avisos vêm da execução real do robô sobre a base fictícia,
e a leitura do totem, do banco real do Node-RED.</p>
</main></body></html>"""
    (AQUI / "painel.html").write_text(html, encoding="utf-8")
    print(f"painel.html · {total} idas · resolveu {resolvidos / total:.0%} · com app {taxa(com_app):.0%} · sem app {taxa(sem_app):.0%}")
    print("motivos:", dict(motivos))


if __name__ == "__main__":
    main()
