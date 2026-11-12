"""Aviso proativo · robô diário do Vai de Primeira.

Lê a base de cidadãos, encontra quem precisa de aviso, escreve a mensagem (LLM com texto pronto
de reserva), confere os links, envia o e-mail, registra tudo e gera o Excel do gestor.

Uso:
  python main.py                              executa uma vez com a data de hoje
  python main.py --data 2026-11-12            executa como se fosse outro dia (testes)
  python main.py --agendar                    fica rodando e executa todo dia às 07:00
  python main.py --simular-falha email        demonstra uma falha tratada (email, site, llm ou base)
  python main.py --sem-email                  só decide e gera o relatório, sem enviar
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from robo import config
from robo.base import ler_base
from robo.canais import CaixaDeSaida, conferir_links
from robo.mensagens import Redator, faixa_etaria, montar_email
from robo.registro import Registro
from robo.regras import avisos_para, link_oficial
from robo.relatorio import gerar_excel

log = logging.getLogger("robo")
FALHAS_PARA_SUSPENDER = 3  # depois disso o servidor de e-mail é considerado fora do ar nesta execução


def executar(base: Path = config.BASE_PADRAO, hoje: date | None = None, usar_llm: bool = True,
             enviar: bool = True, simular_falha: str | None = None, banco: Path = config.BANCO) -> dict:
    hoje = hoje or date.today()
    inicio = config.agora()
    execucao = datetime.now().strftime("%Y%m%d-%H%M%S")
    arquivo_log = config.configurar_log(f"execucao_{execucao}")
    config.carregar_env()
    log.info("execução %s iniciada (data de referência %s)", execucao, hoje.isoformat())

    smtp = config.smtp()
    links_servico = dict(config.LINKS_SERVICO)
    if simular_falha == "base":
        base = base.with_name("arquivo_que_nao_existe.xlsx")
    if simular_falha == "email":
        smtp = {**smtp, "host": "127.0.0.1", "porta": 1}  # porta fechada: o envio falha
    if simular_falha == "site":
        links_servico["cnh_vencendo"] = "https://servico-fora-do-ar.sp.gov.br"
    if simular_falha == "llm":
        import os
        os.environ["GROQ_API_KEY"] = "chave-invalida-para-teste"

    resumo = {"execucao": execucao, "data_referencia": hoje.isoformat(), "simulacao_de_falha": simular_falha or "nenhuma"}
    registro = Registro(banco)
    try:
        cidadaos, revisao = ler_base(base)
    except (FileNotFoundError, ValueError) as erro:
        log.error("não foi possível ler a base (%s). Nenhum aviso enviado; a execução termina com segurança", erro)
        resumo |= {"situacao": "base indisponível", "erro": str(erro), "log": str(arquivo_log)}
        registro.revisao(execucao, [{"id": None, "etapa": "leitura da base", "motivo": str(erro)}])
        registro.execucao(execucao, inicio, resumo)
        registro.fechar()
        return resumo

    servidor = None
    if enviar and not smtp["usuario"] and simular_falha != "email":
        from servidor_email_teste import iniciar
        try:
            servidor = iniciar(smtp["porta"])
        except OSError:
            log.info("caixa de teste já está rodando na porta %s", smtp["porta"])

    redator = Redator(usar_llm=usar_llm)
    caixa = CaixaDeSaida(smtp)
    usados = {links_servico[a.tipo] for c in cidadaos for a in avisos_para(c, hoje) if a.tipo in links_servico}
    links_ok = conferir_links(usados) if enviar else {u: True for u in usados}

    linhas, situacoes, decisoes, falhas_seguidas = [], Counter(), {}, 0
    for c in cidadaos:
        avisos = avisos_para(c, hoje)
        suspeito = c.link_informado if c.link_informado and not link_oficial(c.link_informado) else ""
        tipos = [a.tipo for a in avisos] + (["link_suspeito"] if suspeito else [])
        decisoes[c.id] = tipos
        if not tipos:
            continue
        linha = {"id": c.id, "municipio": c.municipio, "regiao": c.regiao, "tipos": tipos}
        if not c.consentiu_avisos:
            linha["situacao"] = "sem consentimento: não enviado"
        else:
            novos = [a for a in avisos if not registro.ja_enviado(c.id, a.tipo, a.referencia)]
            if suspeito and registro.ja_enviado(c.id, "link_suspeito", suspeito):
                suspeito = ""  # o alerta sobre esse site já foi enviado
            if not novos and not suspeito:
                linha["situacao"] = "já avisado antes"
            else:
                faixa = faixa_etaria(c.idade)
                partes, origens = [], set()
                for a in novos:
                    texto, origem = redator.texto_do_aviso(a.tipo, faixa)
                    partes.append((a, texto))
                    origens.add(origem)
                assunto, corpo = montar_email(c.primeiro_nome, partes, suspeito, links_ok, links_servico)
                linha["origem_texto"] = "/".join(sorted(origens)) or "template"
                if not enviar:
                    linha["situacao"] = "simulado (sem envio)"
                elif falhas_seguidas >= FALHAS_PARA_SUSPENDER:
                    linha["situacao"] = "envio suspenso: revisão humana"
                    revisao.append({"id": c.id, "etapa": "envio de e-mail",
                                    "motivo": "envio suspenso após falhas seguidas do servidor de e-mail"})
                else:
                    try:
                        caixa.enviar(c.email, assunto, corpo, c.id)
                        for a in novos:
                            registro.marcar_enviado(c.id, a.tipo, a.referencia, linha["origem_texto"])
                        if suspeito:
                            registro.marcar_enviado(c.id, "link_suspeito", suspeito, "template")
                        linha["situacao"] = "enviado"
                        falhas_seguidas = 0
                    except Exception as erro:
                        falhas_seguidas += 1
                        if falhas_seguidas == FALHAS_PARA_SUSPENDER:
                            log.error("%d falhas seguidas de e-mail: envios suspensos nesta execução", falhas_seguidas)
                        linha["situacao"] = "falha no envio: revisão humana"
                        revisao.append({"id": c.id, "etapa": "envio de e-mail", "motivo": f"{type(erro).__name__}: {erro}"})
            if any(a.tipo == "bpc_possivel" for a in avisos):
                revisao.append({"id": c.id, "etapa": "sinalização BPC",
                                "motivo": "possível direito ao BPC: confirmar com o CRAS antes de qualquer orientação individual"})
        situacoes[linha["situacao"]] += 1
        linhas.append(linha)

    if servidor:
        servidor.shutdown()
    resumo |= {
        "situacao": "concluída",
        "cidadaos_lidos": len(cidadaos),
        "com_aviso": len(linhas),
        **{f"situacao: {k}": v for k, v in situacoes.items()},
        "avisos_por_tipo": dict(Counter(t for l in linhas for t in l["tipos"])),
        "textos": redator.estatisticas,
        "links_oficiais_no_ar": sum(links_ok.values()), "links_oficiais_fora_do_ar": len(links_ok) - sum(links_ok.values()),
        "revisao_humana": len(revisao),
        "log": str(arquivo_log.relative_to(config.PASTA)),
    }
    pasta_relatorios = config.SAIDA / "relatorios"
    excel = pasta_relatorios / f"demanda_{execucao}.xlsx"
    gerar_excel(excel, linhas, revisao, resumo)
    resumo["excel"] = str(excel.relative_to(config.PASTA))
    (pasta_relatorios / f"execucao_{execucao}.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    registro.revisao(execucao, revisao)
    registro.execucao(execucao, inicio, resumo)
    registro.fechar()
    log.info("execução %s concluída: %s", execucao, {k: v for k, v in resumo.items() if k.startswith(("situacao", "com_", "revisao"))})
    resumo["decisoes"] = decisoes
    resumo["ids_revisao_leitura"] = [r["id"] for r in revisao if r.get("etapa") == "leitura da base"]
    return resumo


def agendar(**kwargs):
    """Executa todo dia no horário configurado. Uma falha num dia não para o agendamento."""
    hora, minuto = map(int, config.HORARIO_AGENDADO.split(":"))
    while True:
        agora = datetime.now()
        proxima = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if proxima <= agora:
            proxima += timedelta(days=1)
        print(f"próxima execução: {proxima:%d/%m/%Y %H:%M}")
        time.sleep((proxima - agora).total_seconds())
        try:
            executar(**kwargs)
        except Exception:
            logging.getLogger("robo").exception("execução agendada falhou; tentando de novo amanhã")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Aviso proativo do Vai de Primeira")
    p.add_argument("--base", type=Path, default=config.BASE_PADRAO)
    p.add_argument("--data", type=date.fromisoformat, help="data de referência (AAAA-MM-DD)")
    p.add_argument("--sem-llm", action="store_true", help="usa só os textos prontos")
    p.add_argument("--sem-email", action="store_true", help="não envia, só decide e gera o relatório")
    p.add_argument("--agendar", action="store_true", help=f"executa todo dia às {config.HORARIO_AGENDADO}")
    p.add_argument("--simular-falha", choices=["email", "site", "llm", "base"])
    a = p.parse_args()
    opcoes = dict(base=a.base, hoje=a.data, usar_llm=not a.sem_llm, enviar=not a.sem_email, simular_falha=a.simular_falha)
    if a.agendar:
        agendar(**opcoes)
    else:
        r = executar(**opcoes)
        r.pop("decisoes", None)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r.get("situacao") == "concluída" else 1)
