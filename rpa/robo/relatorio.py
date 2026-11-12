"""Excel do gestor: demanda por região, avisos da execução, revisão humana e resumo da execução.

Sem nome nem e-mail: o gestor vê id, município e região, o suficiente para planejar a unidade móvel.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

AZUL = "1F5FAD"
NOMES_TIPOS = {
    "cnh_vencendo": "CNH vencendo", "cnh_vencida": "CNH vencida", "cadunico_desatualizado": "Cadastro Único desatualizado",
    "nascimento": "Nascimento", "bpc_possivel": "Possível BPC (sinalização)", "link_suspeito": "Site não oficial",
}


def _cabecalho(aba, colunas):
    aba.append(colunas)
    for celula in aba[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.alignment = Alignment(vertical="center", wrap_text=True)
    aba.freeze_panes = "A2"


def _larguras(aba):
    for i, coluna in enumerate(aba.columns, start=1):
        maior = max(len(str(c.value or "")) for c in coluna)
        aba.column_dimensions[get_column_letter(i)].width = min(max(12, maior + 2), 60)


def gerar_excel(caminho: Path, linhas_avisos: list[dict], revisao: list[dict], resumo: dict):
    wb = Workbook()

    demanda = wb.active
    demanda.title = "Demanda por região"
    tipos = list(NOMES_TIPOS)
    _cabecalho(demanda, ["Região"] + [NOMES_TIPOS[t] for t in tipos] + ["Total"])
    por_regiao = defaultdict(Counter)
    for l in linhas_avisos:
        for t in l["tipos"]:
            por_regiao[l["regiao"]][t] += 1
    for regiao in sorted(por_regiao):
        contagem = [por_regiao[regiao][t] for t in tipos]
        demanda.append([regiao] + contagem + [sum(contagem)])
    if por_regiao:
        grafico = BarChart()
        grafico.type, grafico.grouping, grafico.overlap = "bar", "stacked", 100
        grafico.title, grafico.y_axis.title = "Avisos por região", "avisos"
        dados = Reference(demanda, min_col=2, max_col=len(tipos) + 1, min_row=1, max_row=len(por_regiao) + 1)
        grafico.add_data(dados, titles_from_data=True)
        grafico.set_categories(Reference(demanda, min_col=1, min_row=2, max_row=len(por_regiao) + 1))
        grafico.height, grafico.width = 9, 18
        demanda.add_chart(grafico, f"A{len(por_regiao) + 4}")
    _larguras(demanda)

    avisos = wb.create_sheet("Avisos")
    _cabecalho(avisos, ["ID", "Município", "Região", "Avisos", "Situação", "Texto"])
    for l in linhas_avisos:
        avisos.append([l["id"], l["municipio"], l["regiao"], ", ".join(NOMES_TIPOS[t] for t in l["tipos"]),
                       l["situacao"], l.get("origem_texto", "")])
    _larguras(avisos)

    rev = wb.create_sheet("Revisão humana")
    _cabecalho(rev, ["ID", "Etapa", "Motivo"])
    for r in revisao:
        rev.append([r.get("id"), r.get("etapa"), r.get("motivo")])
    _larguras(rev)

    execucao = wb.create_sheet("Execução")
    _cabecalho(execucao, ["Indicador", "Valor"])
    for chave, valor in resumo.items():
        execucao.append([chave, str(valor) if isinstance(valor, (dict, list)) else valor])
    _larguras(execucao)

    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
