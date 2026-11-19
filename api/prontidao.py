"""Índice de Prontidão: a chance de o cidadão resolver o serviço na primeira ida.

Nota de 0 a 100, feita só com regras explicáveis (sem caixa-preta), para que o
cidadão e o gestor entendam de onde vem cada ponto:

  Documentos   até 60 pts  só conta documento obrigatório com foto boa ("ok").
                           Foto com reflexo, borrada ou cortada vale 0: não deu para conferir.
                           Documento que o serviço não pede também vale 0.
  Fila         até 25 pts  espera até 20 min = 25 · até 45 min = 15 · mais = 5 ·
                           sem dado de fila = 15 (neutro).
  Orientação   até 15 pts  a pessoa já recebeu a lista oficial do que levar.

Regra rigorosa: fila e orientação só somam depois que TODOS os documentos obrigatórios
estão conferidos e ok. Sem os documentos certos, ninguém "vai de primeira", por melhor
que esteja a fila. CPF: na CIN, vale o número impresso na certidão (lido pelo OCR).

Faixas: "pronta" (80 ou mais) · "quase" (50 a 79) · "nao_pronta" (menos de 50).
"""

PONTOS_DOCUMENTOS = 60
PONTOS_FILA = 25
PONTOS_ORIENTACAO = 15
VERSAO_REGRA = "2.0"

# Documentos obrigatórios por serviço (escopo do protótipo).
OBRIGATORIOS = {
    # CIN: certidão + CPF. O CPF dispensa documento próprio se o número aparece na certidão.
    "cin": ["certidao", "cpf"],
    "cnh": ["cnh", "comprovante_residencia"],
    # Cadastro Único: CPF (ou título de eleitor) do responsável; comprovante é recomendado, não obrigatório.
    "cadunico": ["cpf"],
}
NOMES = {
    "certidao": "certidão de nascimento ou de casamento",
    "cnh": "CNH atual",
    "comprovante_residencia": "comprovante de residência",
    "cpf": "CPF",
    "cin": "documento de identidade",
}
PROBLEMAS = {
    "borrado": "está borrada, tire a foto de novo com o celular apoiado",
    "reflexo": "está com reflexo, incline o papel e tire de novo",
    "cortado": "ficou cortada, afaste o celular e tire de novo",
}


def _pontos_fila(espera_min: int | None) -> tuple[int, str | None]:
    if espera_min is None:
        return 15, None
    if espera_min <= 20:
        return 25, None
    if espera_min <= 45:
        return 15, f"A fila está em cerca de {espera_min} min. Se puder, veja outro horário ou outra unidade."
    return 5, f"A fila está longa (cerca de {espera_min} min). Vale escolher outro horário ou outra unidade."


def _faixa(indice: int) -> str:
    if indice >= 80:
        return "pronta"
    if indice >= 50:
        return "quase"
    return "nao_pronta"


def calcular(servico: str, documentos: list[dict], espera_min: int | None, orientado: bool) -> dict:
    """documentos: itens como {"tipo": "certidao", "qualidade": "ok", "cpf_visivel": true} vindos de /checar-documento."""
    obrigatorios = OBRIGATORIOS[servico]
    peso = PONTOS_DOCUMENTOS / len(obrigatorios)

    # Se o mesmo documento foi conferido mais de uma vez, vale a melhor conferência.
    melhor = {}
    for doc in documentos:
        tipo, qualidade = doc.get("tipo"), doc.get("qualidade", "ok")
        if tipo in obrigatorios and melhor.get(tipo) != "ok":
            melhor[tipo] = qualidade
        # CPF impresso numa certidão boa vale como CPF conferido.
        if tipo == "certidao" and qualidade == "ok" and doc.get("cpf_visivel") and "cpf" in obrigatorios:
            melhor["cpf"] = "ok"

    pendencias = []
    pontos_docs = 0.0
    for tipo in obrigatorios:
        qualidade = melhor.get(tipo)
        if qualidade == "ok":
            pontos_docs += peso
        elif qualidade in PROBLEMAS:
            pendencias.append(f"A foto da {NOMES[tipo]} {PROBLEMAS[qualidade]}.")
        elif tipo == "cpf" and servico == "cin":
            pendencias.append("Falta conferir o CPF: mande a foto do CPF, ou a certidão nova, que já traz o número.")
        else:
            pendencias.append(f"Falta conferir: {NOMES[tipo]}.")
    completos = all(melhor.get(t) == "ok" for t in obrigatorios)

    pontos_fila, aviso_fila = _pontos_fila(espera_min)
    if aviso_fila:
        pendencias.append(aviso_fila)
    pontos_orientacao = PONTOS_ORIENTACAO if orientado else 0
    if not orientado:
        pendencias.append("Pergunte ao assistente o que levar, para ter a lista oficial.")
    if not completos:  # regra rigorosa: sem os documentos certos, fila e orientação não contam
        pontos_fila, pontos_orientacao = 0, 0

    indice = round(pontos_docs + pontos_fila + pontos_orientacao)
    return {
        "servico": servico,
        "indice": indice,
        "faixa": _faixa(indice),
        "componentes": {
            "documentos": round(pontos_docs),
            "fila": pontos_fila,
            "orientacao": pontos_orientacao,
        },
        "documentos_completos": completos,
        "obrigatorios": obrigatorios,
        "pendencias": pendencias,
        "versao_regra": VERSAO_REGRA,
    }
