"""Gera a base fictícia de cidadãos usada pelo robô de avisos.

Saída: rpa/dados/cidadaos.xlsx, com 200 linhas e as colunas do contrato
"Cidadão sintético" (docs/contratos.md), nesta ordem:
id, nome, email, municipio, regiao, idade, cnh_validade, cadunico_atualizado_em,
recebe_bpc, filho_nascido_em, link_informado, consentiu_avisos

- Todos os dados são inventados (nomes do Faker pt_BR, e-mails em @exemplo.test).
- A semente é fixa: rodar de novo gera a mesma base.
- C001 a C195 são linhas válidas. C196 a C200 têm um erro proposital cada,
  para testar a fila de revisão humana do robô.

Uso (dentro de rpa/):
    python dados/gerar_cidadaos.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from openpyxl import Workbook
from openpyxl.styles import Font

SEMENTE = 2026
DATA_REFERENCIA = date(2026, 11, 12)
LIMITE_CADUNICO = date(2024, 11, 12)  # atualizado antes desta data = desatualizado
ARQUIVO_SAIDA = Path(__file__).resolve().parent / "cidadaos.xlsx"

COLUNAS = [
    "id", "nome", "email", "municipio", "regiao", "idade", "cnh_validade",
    "cadunico_atualizado_em", "recebe_bpc", "filho_nascido_em",
    "link_informado", "consentiu_avisos",
]

TOTAL_VALIDOS = 195  # C001 a C195; as 5 últimas linhas são inválidas de propósito

# Quantas pessoas por município (soma 195). São Paulo é dividido em duas regiões.
MUNICIPIOS = [
    ("Itapeva", "Sudoeste Paulista", 35),
    ("Capão Bonito", "Sudoeste Paulista", 25),
    ("Sorocaba", "Sorocaba", 35),
    ("Itu", "Sorocaba", 20),
    ("São Paulo", "Zona Leste SP", 25),
    ("São Paulo", "Zona Sul SP", 25),
    ("Guarulhos", "Grande SP", 30),
]

# Distribuição das situações (o restante fica sem o dado)
QTD_CNH_VENCENDO = 25       # vence entre hoje e daqui a 30 dias
QTD_CNH_VENCIDA = 10        # validade antes de hoje
QTD_CNH_VALIDA = 85         # vence daqui a mais de 30 dias
QTD_CADUNICO_ANTIGO = 50    # atualizado antes de 12/11/2024
QTD_CADUNICO_RECENTE = 70   # atualizado em 12/11/2024 ou depois
QTD_FILHO_RECENTE = 10      # filho nascido nos últimos 60 dias
QTD_IDOSOS = 40             # 65 anos ou mais
QTD_IDOSOS_COM_BPC = 20     # metade dos idosos já recebe o BPC
QTD_LINK_NAO_OFICIAL = 8
QTD_LINK_OFICIAL = 5
QTD_SEM_CONSENTIMENTO = 20

# Endereços fictícios que imitam golpes comuns (fora de gov.br)
LINKS_NAO_OFICIAIS = [
    "https://renovacnh-rapido.com.br",
    "https://cnh-renovacao-online.net",
    "https://cadunico-atualizar.com",
    "https://bpc-liberado.online",
    "https://identidade-nova-agendamento.com.br",
    "https://consulta-beneficio-idoso.site",
    "https://detran-sp-taxas.com",
    "https://cin-segunda-via.org",
]

# Endereços oficiais (todos terminam em gov.br)
LINKS_OFICIAIS = [
    "https://www.detran.sp.gov.br",
    "https://www.gov.br/mds",
    "https://www.gov.br/pt-br/servicos/obter-a-carteira-de-identidade-nacional",
    "https://www.poupatempo.sp.gov.br",
    "https://www.gov.br/inss",
]


def data_texto(d):
    """Datas sempre no formato AAAA-MM-DD."""
    return d.isoformat()


def data_aleatoria(inicio, fim):
    """Data sorteada entre inicio e fim, inclusive."""
    return inicio + timedelta(days=random.randint(0, (fim - inicio).days))


def sortear(indices, quantidade):
    """Sorteia 'quantidade' posições diferentes de uma lista de índices."""
    return set(random.sample(sorted(indices), quantidade))


def gerar_nome(fake):
    """Nome completo fictício, sem prefixos como 'Dr.' ou 'Sra.'."""
    return f"{fake.first_name()} {fake.last_name()} {fake.last_name()}"


def gerar_validos(fake):
    """Gera as 195 linhas válidas (C001 a C195)."""
    todos = list(range(TOTAL_VALIDOS))

    # Município e região: quantidades fixas, posições embaralhadas
    locais = [(m, r) for m, r, qtd in MUNICIPIOS for _ in range(qtd)]
    random.shuffle(locais)

    # Idade: 40 idosos (65 a 95) e o restante adulto (18 a 64)
    idosos = sortear(todos, QTD_IDOSOS)
    idades = {
        i: random.randint(65, 95) if i in idosos else random.randint(18, 64)
        for i in todos
    }
    com_bpc = sortear(idosos, QTD_IDOSOS_COM_BPC)

    # CNH: cada pessoa cai em no máximo uma situação
    embaralhados = random.sample(todos, len(todos))
    corte1 = QTD_CNH_VENCENDO
    corte2 = corte1 + QTD_CNH_VENCIDA
    corte3 = corte2 + QTD_CNH_VALIDA
    cnh_vencendo = set(embaralhados[:corte1])
    cnh_vencida = set(embaralhados[corte1:corte2])
    cnh_valida = set(embaralhados[corte2:corte3])

    # Cadastro Único: antigo, recente ou sem cadastro
    embaralhados = random.sample(todos, len(todos))
    cad_antigo = set(embaralhados[:QTD_CADUNICO_ANTIGO])
    cad_recente = set(embaralhados[QTD_CADUNICO_ANTIGO:QTD_CADUNICO_ANTIGO + QTD_CADUNICO_RECENTE])

    # Filho recém-nascido só para adultos de até 45 anos
    possiveis_pais = [i for i in todos if idades[i] <= 45]
    filho_recente = sortear(possiveis_pais, QTD_FILHO_RECENTE)

    # Links: não oficiais e oficiais em pessoas diferentes
    embaralhados = random.sample(todos, len(todos))
    link_nao_oficial = embaralhados[:QTD_LINK_NAO_OFICIAL]
    link_oficial = embaralhados[QTD_LINK_NAO_OFICIAL:QTD_LINK_NAO_OFICIAL + QTD_LINK_OFICIAL]
    links = {i: LINKS_NAO_OFICIAIS[k] for k, i in enumerate(link_nao_oficial)}
    links.update({i: LINKS_OFICIAIS[k] for k, i in enumerate(link_oficial)})

    sem_consentimento = sortear(todos, QTD_SEM_CONSENTIMENTO)

    linhas = []
    for i in todos:
        numero = i + 1
        municipio, regiao = locais[i]

        if i in cnh_vencendo:
            cnh = data_texto(DATA_REFERENCIA + timedelta(days=random.randint(0, 30)))
        elif i in cnh_vencida:
            cnh = data_texto(DATA_REFERENCIA - timedelta(days=random.randint(1, 730)))
        elif i in cnh_valida:
            cnh = data_texto(DATA_REFERENCIA + timedelta(days=random.randint(31, 1825)))
        else:
            cnh = None

        if i in cad_antigo:
            cadunico = data_texto(data_aleatoria(date(2019, 1, 1), LIMITE_CADUNICO - timedelta(days=1)))
        elif i in cad_recente:
            cadunico = data_texto(data_aleatoria(LIMITE_CADUNICO, DATA_REFERENCIA))
        else:
            cadunico = None

        if i in filho_recente:
            filho = data_texto(DATA_REFERENCIA - timedelta(days=random.randint(0, 60)))
        else:
            filho = None

        linhas.append({
            "id": f"C{numero:03d}",
            "nome": gerar_nome(fake),
            "email": f"c{numero:03d}@exemplo.test",
            "municipio": municipio,
            "regiao": regiao,
            "idade": idades[i],
            "cnh_validade": cnh,
            "cadunico_atualizado_em": cadunico,
            "recebe_bpc": "sim" if i in com_bpc else "nao",
            "filho_nascido_em": filho,
            "link_informado": links.get(i),
            "consentiu_avisos": "nao" if i in sem_consentimento else "sim",
        })
    return linhas


def gerar_invalidos(fake):
    """Gera C196 a C200, cada uma com um único erro proposital."""
    linhas = []
    for numero in range(196, 201):
        municipio, regiao, _ = random.choice(MUNICIPIOS)
        linhas.append({
            "id": f"C{numero:03d}",
            "nome": gerar_nome(fake),
            "email": f"c{numero:03d}@exemplo.test",
            "municipio": municipio,
            "regiao": regiao,
            "idade": random.randint(25, 60),
            "cnh_validade": data_texto(DATA_REFERENCIA + timedelta(days=random.randint(200, 1500))),
            "cadunico_atualizado_em": data_texto(data_aleatoria(LIMITE_CADUNICO, DATA_REFERENCIA)),
            "recebe_bpc": "nao",
            "filho_nascido_em": None,
            "link_informado": None,
            "consentiu_avisos": "sim",
        })

    linhas[0]["cnh_validade"] = "2026-02-31"     # C196: data impossível
    linhas[1]["email"] = "c197exemplo.test"      # C197: e-mail sem @, com consentimento
    linhas[1]["consentiu_avisos"] = "sim"
    linhas[2]["idade"] = "abc"                   # C198: idade que não é número
    linhas[3]["idade"] = 150                     # C199: idade fora de 0 a 120
    linhas[4]["id"] = "C001"                     # C200: id repetido
    return linhas


def salvar_excel(linhas, caminho):
    planilha = Workbook()
    aba = planilha.active
    aba.title = "cidadaos"
    aba.append(COLUNAS)
    for celula in aba[1]:
        celula.font = Font(bold=True)
    for linha in linhas:
        aba.append([linha[coluna] for coluna in COLUNAS])

    larguras = [7, 32, 22, 15, 19, 7, 14, 23, 11, 17, 44, 17]
    for coluna, largura in zip(aba.columns, larguras):
        aba.column_dimensions[coluna[0].column_letter].width = largura
    aba.freeze_panes = "A2"
    planilha.save(caminho)


def resumo(linhas):
    """Conta as situações da base para conferir a distribuição."""
    validas = linhas[:TOTAL_VALIDOS]
    ref = DATA_REFERENCIA.isoformat()
    limite_cnh = (DATA_REFERENCIA + timedelta(days=30)).isoformat()
    limite_filho = (DATA_REFERENCIA - timedelta(days=60)).isoformat()
    lim_cad = LIMITE_CADUNICO.isoformat()

    def conta(condicao):
        return sum(1 for linha in validas if condicao(linha))

    return {
        "linhas": len(linhas),
        "cnh vencendo (0 a 30 dias)": conta(lambda l: l["cnh_validade"] and ref <= l["cnh_validade"] <= limite_cnh),
        "cnh vencida": conta(lambda l: l["cnh_validade"] and l["cnh_validade"] < ref),
        "cnh válida (mais de 30 dias)": conta(lambda l: l["cnh_validade"] and l["cnh_validade"] > limite_cnh),
        "sem cnh": conta(lambda l: not l["cnh_validade"]),
        "cadastro único antes de 2024-11-12": conta(lambda l: l["cadunico_atualizado_em"] and l["cadunico_atualizado_em"] < lim_cad),
        "cadastro único recente": conta(lambda l: l["cadunico_atualizado_em"] and l["cadunico_atualizado_em"] >= lim_cad),
        "sem cadastro único": conta(lambda l: not l["cadunico_atualizado_em"]),
        "filho nos últimos 60 dias": conta(lambda l: l["filho_nascido_em"] and l["filho_nascido_em"] >= limite_filho),
        "65 anos ou mais": conta(lambda l: l["idade"] >= 65),
        "65+ que recebem bpc": conta(lambda l: l["idade"] >= 65 and l["recebe_bpc"] == "sim"),
        "link não oficial": conta(lambda l: l["link_informado"] and ".gov.br" not in l["link_informado"]),
        "link oficial": conta(lambda l: l["link_informado"] and ".gov.br" in l["link_informado"]),
        "não consentiu avisos": conta(lambda l: l["consentiu_avisos"] == "nao"),
        "inválidas propositais (C196 a C200)": len(linhas) - len(validas),
    }


def main():
    random.seed(SEMENTE)
    Faker.seed(SEMENTE)
    fake = Faker("pt_BR")

    linhas = gerar_validos(fake) + gerar_invalidos(fake)
    salvar_excel(linhas, ARQUIVO_SAIDA)

    print(f"Base salva em {ARQUIVO_SAIDA}")
    for nome, valor in resumo(linhas).items():
        print(f"  {nome}: {valor}")


if __name__ == "__main__":
    main()
