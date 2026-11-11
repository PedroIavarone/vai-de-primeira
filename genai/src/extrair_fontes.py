"""Extrai o texto principal das páginas oficiais salvas em fontes/brutas/.

Remove menus, cabeçalhos, rodapés e scripts e grava fontes/texto/<arquivo>.txt com a
origem no topo. É a base provisória do Assistente da Jornada até o corpus limpo e
anonimizado do módulo pln/ ficar pronto.

Uso:
  python src/extrair_fontes.py
"""
import csv
import re
import subprocess
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parents[1]
FONTES = RAIZ / "fontes"
REMOVER = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "button", "svg", "iframe"]
CLASSES_RUIDO = re.compile(r"(menu|breadcrumb|rodape|footer|header|social|share|compartilh|cookie|banner|navega)", re.I)


def texto_html(caminho: Path) -> str:
    sopa = BeautifulSoup(caminho.read_bytes(), "html.parser")
    for tag in sopa(REMOVER):
        tag.decompose()
    for tag in sopa.find_all(attrs={"class": CLASSES_RUIDO}):
        # Nunca apaga o body nem quem contém o conteúdo (ex.: body com classe "default-header-template").
        if tag.name in ("html", "body") or tag.select_one("#content, main, article"):
            continue
        tag.decompose()
    candidatos = [sopa.select_one(s) for s in ("#content-core", "#content", "article", "main", "#conteudo")]
    candidatos = [c for c in candidatos if c and len(c.get_text(" ", strip=True)) > 300]
    raiz = candidatos[0] if candidatos else sopa.body or sopa
    linhas = []
    blocos = ["h1", "h2", "h3", "h4", "p", "li", "td", "dt", "dd"]
    for bloco in raiz.find_all(blocos):
        if bloco.find(blocos):  # só blocos internos: evita repetir o texto do filho no pai
            continue
        t = " ".join(bloco.get_text(" ", strip=True).split())
        if len(t) < 3 or (linhas and t == linhas[-1]):
            continue
        if bloco.name in ("h1", "h2", "h3", "h4"):
            t = f"\n## {t}"
        elif bloco.name == "li":
            t = f"- {t}"
        linhas.append(t)
    return "\n".join(linhas)


def texto_pdf(caminho: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(caminho), "-"], capture_output=True, text=True).stdout


def main():
    destino = FONTES / "texto"
    destino.mkdir(parents=True, exist_ok=True)
    with open(FONTES / "fontes.csv", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            bruto = next((FONTES / "brutas").glob(f"{linha['arquivo']}.*"))
            corpo = texto_pdf(bruto) if bruto.suffix == ".pdf" else texto_html(bruto)
            corpo = re.sub(r"\n{3,}", "\n\n", corpo).strip()
            cabecalho = (f"Fonte: {linha['orgao']}\nURL: {linha['url']}\nServiço: {linha['servico']}\n"
                         f"Acesso: {date.fromtimestamp(bruto.stat().st_mtime).isoformat()}\n\n")
            (destino / f"{linha['arquivo']}.txt").write_text(cabecalho + corpo + "\n", encoding="utf-8")
            print(f"{linha['arquivo']:34} {len(corpo.split()):>6} palavras")


if __name__ == "__main__":
    main()
