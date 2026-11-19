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

    # 1 a 3. indicadores e gráficos das idas simuladas: calculados no navegador, para os filtros de região e serviço
    regioes = list(REGIOES)
    idas = [[regioes.index(a["regiao"]), list(SERVICOS).index(a["servico"]), int(a["usou_app"]), a["indice"],
             list(FAIXAS).index(a["faixa"]), int(a["resolveu"]), a["motivo"]] for a in at]

    # 4. para onde levar a unidade móvel: avisos reais do robô por unidade, pesados pelo deslocamento médio
    demanda = {r: (robo["regioes"].get(r, {}).get("Total", 0) if robo else 0) for r in regioes}
    deslocamento = {r: sum(a["deslocamento_min"] for a in at if a["regiao"] == r) / max(1, sum(a["regiao"] == r for a in at)) for r in regioes}
    ranking = sorted(regioes, key=lambda r: demanda[r] / REGIOES[r][0] * deslocamento[r], reverse=True)
    unidade_movel = [{"regiao": r, "deslocamento": round(deslocamento[r]), "avisos": demanda[r], "unidades": REGIOES[r][0]} for r in ranking]

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
        linhas_modelos.append(("Assistente (RAG + agente)", f"{rs['acerto_geral']:.1%}".replace('.', ',') + f" de acerto em {rs['total']} perguntas · fonte certa {rs['fonte_correta']:.0%}",
                               f"fidelidade à fonte {rs['fidelidade_a_fonte']:.1%}".replace('.', ',') + f" · {rs['caminho_seguro_usado']} resposta segura"))
    if pln:
        linhas_modelos.append(("Corpus para ajuste fino (PLN)", f"{pln['corpus_qa']['exemplos']} pares e {pln['corpus_chat']['exemplos']} diálogos",
                               f"{pln['corpus_qa'].get('rejeitados_sem_evidencia', 0)} pares descartados sem evidência · 20% conferidos contra o documento (1 corrigido, 4 removidos)"))
    if rpa_val:
        linhas_modelos.append(("Robô de avisos (RPA)", f"{rpa_val['acertos']} de {rpa_val['casos']} casos rotulados",
                               f"{robo['resumo']['revisao_humana']} casos para revisão humana na última execução" if robo else ""))
    tabela = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in linhas_modelos)

    kpis_fixos = "".join([
        kpi("Avisos enviados pelo robô", f"{robo['resumo'].get('situacao: enviado', 0)}" if robo else "–",
            f"{robo['resumo']['com_aviso']} pessoas com aviso · {robo['resumo']['revisao_humana']} para revisão humana" if robo else ""),
        kpi("Totem da unidade", f"{iot['leituras']} leituras" if iot else "–",
            f"{sum(iot['alertas'].values())} alertas · {iot['descartes']} leituras inválidas descartadas" if iot else "sem dados do totem", LARANJA),
    ])
    opcoes_regiao = "".join(f'<option value="{k}">{r}</option>' for k, r in enumerate(regioes))
    opcoes_servico = "".join(f'<option value="{k}">{n}</option>' for k, n in enumerate(SERVICOS.values()))
    dados = json.dumps({"regioes": regioes, "servicos": list(SERVICOS.values()), "faixas": list(FAIXAS.values()),
                        "idas": idas, "unidade_movel": unidade_movel}, ensure_ascii=False, separators=(",", ":"))

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel do gestor · Vai de Primeira</title>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<style>
 body {{ margin:0; font-family:"Atkinson Hyperlegible",Arial,sans-serif; background:#F2F4F7; color:#1F2933; font-size:16px; }}
 header {{ background:{AZUL}; color:#fff; padding:14px 24px; display:flex; align-items:center; gap:16px; flex-wrap:wrap; }}
 header .nome {{ margin:0 0 2px; font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:#d3e2f6; }}
 header .marca {{ width:44px; height:44px; border-radius:10px; background:#fff; display:grid; place-items:center; flex-shrink:0; }}
 header h1 {{ margin:0; font-size:1.45rem; }} header p {{ margin:2px 0 0; opacity:.9; font-size:.95rem; }}
 .filtros {{ margin-left:auto; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
 .filtros label {{ display:flex; align-items:center; gap:6px; background:#fff; color:#1F2933; border-radius:10px; padding:6px 10px; font-size:.95rem; font-weight:700; }}
 .filtros select {{ font:inherit; font-weight:400; border:0; background:transparent; color:#1F2933; }}
 .selo-sim {{ background:#FDF5EE; color:{LARANJA}; border:2px solid {LARANJA}; border-radius:999px; padding:5px 12px; font-weight:700; font-size:.9rem; }}
 main {{ max-width:1320px; margin:0 auto; padding:20px; }}
 .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:14px; }}
 .kpi, .card {{ background:#fff; border:1px solid #D0D5DD; border-radius:12px; padding:16px 18px; }}
 .kpi-t {{ color:#667085; font-size:.95rem; }} .kpi-v {{ font-size:2.2rem; font-weight:700; line-height:1.15; }} .kpi-d {{ font-size:.9rem; color:#667085; }}
 .kpi-v small {{ font-size:1rem; color:#667085; font-weight:400; }}
 .linha3 {{ display:grid; grid-template-columns:1.25fr 1fr 0.9fr; gap:14px; margin-bottom:14px; }}
 .grade {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(520px,1fr)); gap:14px; margin-bottom:14px; }}
 .card h2 {{ margin:0 0 10px; font-size:1.15rem; }}
 .motivo {{ margin-bottom:12px; }} .motivo-t {{ display:flex; justify-content:space-between; font-size:.95rem; }}
 .barra {{ height:12px; background:#F2F4F7; border-radius:6px; margin-top:4px; overflow:hidden; }} .barra span {{ display:block; height:100%; background:{VERMELHO}; border-radius:6px; }}
 .insight {{ margin-top:10px; background:#E8F0FB; border-radius:10px; padding:10px 12px; font-size:.92rem; }}
 .ranking {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; }}
 .ranking li {{ border:1px solid #D0D5DD; border-radius:10px; padding:10px 12px; display:flex; gap:12px; align-items:center; }}
 .ranking li:first-child {{ border:2px solid {VERMELHO}; background:#FDF1F0; }}
 .ranking b.n {{ font-size:1.3rem; color:{AZUL}; min-width:20px; }} .ranking li:first-child b.n {{ color:{VERMELHO}; }}
 .ranking .d {{ font-size:.88rem; color:#667085; }} .ranking li.foco {{ outline:3px solid {AZUL}; }}
 table {{ width:100%; border-collapse:collapse; }} td, th {{ text-align:left; padding:8px; border-bottom:1px solid #EEF0F3; vertical-align:top; }}
 .nota {{ font-size:.9rem; color:#667085; }}
 .selo {{ display:inline-block; border:2px solid {LARANJA}; color:{LARANJA}; border-radius:999px; padding:0 10px; font-weight:700; font-size:.85rem; }}
 @media (max-width: 1000px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} .linha3 {{ grid-template-columns:1fr; }} .grade {{ grid-template-columns:1fr; }} }}
</style></head><body>
<header>
 <span class="marca"><svg width="28" height="28" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke="{AZUL}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
 <div><p class="nome">Vai de Primeira</p><h1>Painel do gestor</h1><p>Contagens por região. Nenhum dado pessoal.</p></div>
 <div class="filtros">
  <label>Região: <select id="f-regiao"><option value="">Todas</option>{opcoes_regiao}</select></label>
  <label>Serviço: <select id="f-servico"><option value="">Todos</option>{opcoes_servico}</select></label>
  <span class="selo-sim">● Dados simulados</span>
 </div>
</header>
<main>
<div class="kpis">
 <div class="kpi"><div class="kpi-t">Resolveu na primeira ida</div><div class="kpi-v" id="k1"></div><div class="kpi-d" id="k1d"></div></div>
 <div class="kpi"><div class="kpi-t">Com o app × sem o app</div><div class="kpi-v" id="k2" style="color:{VERDE}"></div><div class="kpi-d" id="k2d"></div></div>
 {kpis_fixos}
</div>
<div class="linha3">
 <div class="card"><h2>Índice de Prontidão na chegada</h2><div id="g-indice"></div></div>
 <div class="card"><h2>Por que voltaram sem resolver</h2><div id="motivos"></div><div class="insight" id="insight"></div></div>
 <div class="card"><h2>Para onde levar a unidade móvel</h2><ol class="ranking" id="ranking"></ol>
  <p class="nota">Ordem: avisos do robô por unidade × deslocamento médio até a unidade.</p></div>
</div>
<div class="grade"><div class="card"><h2>Resolveu na primeira ida (%), por faixa do índice</h2><div id="g-faixa"></div></div>
 <div class="card">{figura_html(fig5)}</div></div>
<div class="grade"><div class="card">{figura_html(fig6)}</div>
<div class="card"><h2>Desempenho dos modelos e revisão humana</h2>
<table><tr><th>Módulo</th><th>Resultado</th><th>Controle</th></tr>{tabela}</table>
<p class="nota">A IA faz triagem. Documento é conferido pelo atendente, direito a benefício é decidido pelo órgão responsável e toda sinalização de BPC passa por revisão humana.</p></div></div>
<p class="nota"><span class="selo">simulado</span> Os indicadores de resolução, a prontidão e os motivos usam {total} idas simuladas
(governanca/painel/atendimentos.csv); os filtros recalculam esses números. O Índice de Prontidão de cada ida é calculado pela regra real da API; a chance de resolver
em cada faixa (93%, 62% e 25%) é uma premissa a ser medida no piloto. Os avisos vêm da execução real do robô sobre a base fictícia,
e a leitura do totem, do banco real do Node-RED.</p>
</main>
<script>
const D = {dados};
const CORES = ["{AZUL}", "#5B8FD0", "#A9C4E8"];
const LAYOUT = {{ height: 300, margin: {{l: 40, r: 10, t: 10, b: 60}}, font: {{family: "Atkinson Hyperlegible, Arial", size: 14, color: "#1F2933"}},
  paper_bgcolor: "#fff", plot_bgcolor: "#fff", legend: {{orientation: "h", y: -0.2}}, autosize: true }};
const CFG = {{displayModeBar: false, responsive: true}};
const pct = (a, b) => b ? Math.round(100 * a / b) : 0;
function atualizar() {{
  const fr = document.getElementById("f-regiao").value, fs = document.getElementById("f-servico").value;
  const xs = D.idas.filter(x => (fr === "" || x[0] == fr) && (fs === "" || x[1] == fs));
  const res = xs.filter(x => x[5]).length;
  document.getElementById("k1").innerHTML = pct(res, xs.length) + "%";
  document.getElementById("k1d").textContent = res + " de " + xs.length + " idas";
  const com = xs.filter(x => x[2]), sem = xs.filter(x => !x[2]);
  const tc = pct(com.filter(x => x[5]).length, com.length), ts = pct(sem.filter(x => x[5]).length, sem.length);
  document.getElementById("k2").innerHTML = tc + "% <small>× " + ts + "%</small>";
  document.getElementById("k2d").textContent = "≈ " + Math.max(0, Math.round((tc - ts) / 100 * sem.length)) + " viagens perdidas a menos, se as premissas se confirmarem";
  // índice médio por região (e por serviço, quando nenhum serviço está filtrado)
  const servs = fs === "" ? [0, 1, 2] : [Number(fs)];
  const regs = fr === "" ? D.regioes.map((_, k) => k) : [Number(fr)];
  const tr = servs.map(s => ({{ type: "bar", name: D.servicos[s], marker: {{color: CORES[s]}},
    x: regs.map(r => D.regioes[r].replace(" SP", "").replace("Sudoeste Paulista", "Sudoeste")),
    y: regs.map(r => {{ const v = xs.filter(x => x[0] == r && x[1] == s); return v.length ? Math.round(v.reduce((a, x) => a + x[3], 0) / v.length) : 0; }}) }}));
  Plotly.react("g-indice", tr, {{...LAYOUT, barmode: "group", yaxis: {{range: [0, 100], gridcolor: "#EEF0F3"}}}}, CFG);
  // motivos de quem voltou
  const voltas = xs.filter(x => !x[5]), cont = {{}};
  voltas.forEach(x => cont[x[6]] = (cont[x[6]] || 0) + 1);
  const ordem = Object.entries(cont).sort((a, b) => b[1] - a[1]), max = ordem.length ? ordem[0][1] : 1;
  document.getElementById("motivos").innerHTML = ordem.map(([m, v]) =>
    `<div class="motivo"><div class="motivo-t"><span>${{m.replace("Outro (sistema, horário, regra)", "Outro motivo")}}</span><b>${{v}}</b></div><div class="barra"><span style="width:${{pct(v, max)}}%"></span></div></div>`).join("");
  const docs = voltas.filter(x => x[6].startsWith("Documento")).length;
  document.getElementById("insight").innerHTML = voltas.length ? `→ <b>${{pct(docs, voltas.length)}}%</b> das voltas são por <b>documento</b>: é o que a lista oficial e a conferência pela câmera resolvem.` : "Nenhuma volta neste filtro.";
  // resolução por faixa, com e sem app
  const tf = [[com, "Usou o app antes", "{AZUL}"], [sem, "Não usou", "{CINZA}"]].map(([g, n, c]) => ({{ type: "bar", name: n, marker: {{color: c}}, x: D.faixas,
    y: D.faixas.map((_, f) => {{ const v = g.filter(x => x[4] == f); return pct(v.filter(x => x[5]).length, v.length); }}) }}));
  Plotly.react("g-faixa", tf, {{...LAYOUT, barmode: "group", yaxis: {{range: [0, 100], gridcolor: "#EEF0F3"}}}}, CFG);
  // ranking da unidade móvel (destaca a região filtrada)
  document.getElementById("ranking").innerHTML = D.unidade_movel.map((u, k) =>
    `<li class="${{fr !== "" && D.regioes[fr] === u.regiao ? "foco" : ""}}"><b class="n">${{k + 1}}</b><span><b>${{u.regiao}}</b><br><span class="d">${{u.deslocamento}} min de viagem · ${{u.avisos}} avisos${{u.unidades > 1 ? " · " + u.unidades + " unidades" : ""}}</span></span></li>`).join("");
}}
document.getElementById("f-regiao").addEventListener("change", atualizar);
document.getElementById("f-servico").addEventListener("change", atualizar);
atualizar();
</script>
</body></html>"""
    (AQUI / "painel.html").write_text(html, encoding="utf-8")
    print(f"painel.html · {total} idas · resolveu {resolvidos / total:.0%} · com app {taxa(com_app):.0%} · sem app {taxa(sem_app):.0%}")
    print("motivos:", dict(Counter(a["motivo"] for a in at if not a["resolveu"])))


if __name__ == "__main__":
    main()
