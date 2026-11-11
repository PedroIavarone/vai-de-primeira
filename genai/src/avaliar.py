"""Avalia o Assistente da Jornada com as 30 perguntas de avaliacao/perguntas.json.

Critérios automáticos por pergunta:
  acerto       a resposta contém cada grupo de termos esperados e nenhum termo proibido
  fonte        a resposta cita uma fonte do serviço certo
  fidelidade   os termos esperados que aparecem na resposta também aparecem nos trechos
               recuperados (a resposta está apoiada na fonte, não inventada)
  recusa       perguntas fora do tema: não responde o mérito e encaminha ao órgão adequado
Também mede latência e quantas vezes o caminho seguro (falha do LLM) foi usado.

Saídas: avaliacao/resultados.json (resumo + detalhe) e avaliacao/respostas.csv (para a
revisão humana de pelo menos 20% das respostas).

Uso:
  python src/avaliar.py
"""
import csv
import json
import statistics
import time
import unicodedata
from pathlib import Path

from agente import Assistente

RAIZ = Path(__file__).resolve().parents[1]
PAUSA_S = 2.0  # respeita o limite de tokens por minuto do plano gratuito
SINAIS_RECUSA = ["não posso", "não consigo", "só consigo", "só posso", "fora do", "não tenho como",
                 "não é possível", "carteira de identidade", "cadastro único", "cnh", "serviços públicos"]


def norm(texto: str) -> str:
    """Minúsculas, sem acento e com qualquer espaço Unicode (ex.: U+202F) virando espaço comum."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.split())


def contem(texto: str, termo: str) -> bool:
    return norm(termo) in norm(texto)


def avaliar_item(item: dict, r: dict, contexto: list[str]) -> dict:
    resposta = r.get("resposta", "")
    ctx = " ".join(contexto)
    out = {"caminho_seguro": bool(r.get("erro"))}
    if item["categoria"] == "fora_tema":
        alvo = item.get("encaminhar", [])
        texto = f"{resposta} {r.get('encaminhar_para') or ''}"
        encaminhou = any(contem(texto, t) for t in alvo) if alvo else any(contem(resposta, s) for s in SINAIS_RECUSA)
        out["recusa"] = encaminhou and r.get("servico") is None
        out["acerto"] = out["recusa"]
        return out
    grupos_ok, termos_achados = [], []
    for grupo in item.get("deve_conter", []):
        achado = next((t for t in grupo if contem(resposta, t)), None)
        grupos_ok.append(achado is not None)
        if achado:
            termos_achados.append(achado)
    proibido = [t for t in item.get("nao_deve_conter", []) if contem(resposta, t)]
    out["acerto"] = all(grupos_ok) and not proibido
    out["proibido"] = proibido
    servico = item.get("servico")
    out["fonte"] = any(f.startswith(f"{servico}_") for f in r.get("fontes", [])) if servico and contexto else None
    if contexto and termos_achados:
        genericos = {"não", "nao"}
        especificos = [t for t in termos_achados if norm(t) not in genericos]
        out["fidelidade"] = all(contem(ctx, t) for t in especificos) if especificos else None
    else:
        out["fidelidade"] = None
    return out


def taxa(valores):
    v = [x for x in valores if x is not None]
    return round(sum(v) / len(v), 3) if v else None


def main():
    perguntas = json.loads((RAIZ / "avaliacao/perguntas.json").read_text(encoding="utf-8"))
    assistente = Assistente()
    detalhes = []
    for item in perguntas:
        inicio = time.perf_counter()
        r = assistente.perguntar(item["pergunta"], item.get("perfil", "geral"))
        segundos = time.perf_counter() - inicio
        nota = avaliar_item(item, r, getattr(assistente, "ultimo_contexto", []))
        detalhes.append({**item, "resposta": r.get("resposta"), "fontes": r.get("fontes", []),
                         "encaminhar_para": r.get("encaminhar_para"), "ferramentas": r.get("ferramentas", []),
                         "segundos": round(segundos, 1), **nota})
        marca = "✓" if nota["acerto"] else "✗"
        print(f"{marca} {item['id']:>2} [{item['categoria']}] {segundos:4.1f}s  {item['pergunta'][:70]}")
        time.sleep(PAUSA_S)

    resumo = {"total": len(detalhes), "acerto_geral": taxa([d["acerto"] for d in detalhes])}
    for cat in ("no_tema", "fora_tema", "pegadinha"):
        resumo[f"acerto_{cat}"] = taxa([d["acerto"] for d in detalhes if d["categoria"] == cat])
    resumo["fonte_correta"] = taxa([d.get("fonte") for d in detalhes])
    resumo["fidelidade_a_fonte"] = taxa([d.get("fidelidade") for d in detalhes])
    resumo["respostas_nao_fieis_ids"] = [d["id"] for d in detalhes if d.get("fidelidade") is False]
    resumo["termos_proibidos_ids"] = [d["id"] for d in detalhes if d.get("proibido")]
    resumo["caminho_seguro_usado"] = sum(d["caminho_seguro"] for d in detalhes)
    tempos = sorted(d["segundos"] for d in detalhes)
    resumo["latencia_media_s"] = round(statistics.mean(tempos), 1)
    resumo["latencia_p95_s"] = tempos[int(len(tempos) * 0.95) - 1]
    resumo["erros_ids"] = [d["id"] for d in detalhes if not d["acerto"]]

    (RAIZ / "avaliacao/resultados.json").write_text(
        json.dumps({"resumo": resumo, "detalhes": detalhes}, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(RAIZ / "avaliacao/respostas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "categoria", "perfil", "pergunta", "resposta", "fontes", "acerto_automatico",
                    "fidelidade_automatica", "revisao_humana", "comentario"])
        for d in detalhes:
            w.writerow([d["id"], d["categoria"], d.get("perfil"), d["pergunta"], d["resposta"], "; ".join(d["fontes"]),
                        d["acerto"], d.get("fidelidade"), "", ""])
    print("\n" + json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
