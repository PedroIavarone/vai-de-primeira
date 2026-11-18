# Fábrica de Corpus

Transforma documentos públicos sobre **Carteira de Identidade Nacional (CIN), renovação da CNH, Cadastro Único e BPC** em três corpora limpos e anonimizados, prontos para o ajuste fino de um modelo de linguagem pequeno (SLM). O corpus de texto também é a base de conhecimento do [Assistente da Jornada](../genai/).

**Para quem:** Dona Francisca, 67 anos, zona rural de Itapeva (SP). Lê com dificuldade e já perdeu duas viagens por falta de um documento. Um modelo local e especializado precisa responder a ela em linguagem simples, sem inventar regra.

## Como funciona
```
PDF · DOCX · TXT · HTML · texto colado
  → extração        pdfplumber, python-docx, BeautifulSoup, detecção de codificação
  → limpeza         cabeçalho e rodapé repetidos, número de página, URL solta, caracteres
                    invisíveis, letras espaçadas, hífen no fim da linha, linhas de menu
  → normalização    UTF-8 (NFC), espaços, quebras de linha e aspas. Mantém acentos,
                    pontuação e maiúsculas; sem stopwords removidas e sem stemming
  → anonimização    [CPF] [EMAIL] [TELEFONE] [NOME] (regras + spaCy pt_core_news_md)
  → segmentação     trechos de 256 a 512 tokens, cortando só entre frases ou parágrafos
  → corpora         texto puro · perguntas e respostas · diálogos (com recusas)
  → qualidade       duplicatas removidas, estatísticas e 5 exemplos de cada corpus
```

## Documentos de entrada
Cinco documentos oficiais, um em cada formato, listados com órgão, link e data de acesso em [`entrada/fontes.csv`](entrada/fontes.csv).

| Arquivo | Formato | Órgão | Serviço |
|---|---|---|---|
| `bpc_perguntas_mds.pdf` | PDF (14 páginas) | Ministério do Desenvolvimento e Assistência Social | BPC |
| `cnh_renovacao_detran_sp_duvidas.html` | HTML | Detran-SP | Renovação da CNH |
| `cin_govbr_perguntas.html` | HTML | Ministério da Gestão e da Inovação | CIN |
| `cin_poupatempo_sp.docx` | DOCX | Governo do Estado de São Paulo | CIN |
| `cadunico_inscrever_govbr.txt` | TXT | Ministério do Desenvolvimento e Assistência Social | Cadastro Único |

<!-- RESULTADOS -->
## Resultados
Números de [`saida/relatorio_qualidade.json`](saida/relatorio_qualidade.json), com os 5 documentos de entrada.

| Corpus | Exemplos | Tokens por exemplo (mín · média · máx) | Duplicatas removidas | Descartados |
|---|---|---|---|---|
| [`corpus_texto.jsonl`](saida/corpus_texto.jsonl) | 61 trechos | 337 · 387 · 511 | 0 | — |
| [`corpus_qa.jsonl`](saida/corpus_qa.jsonl) | 169 pares | 21 · 47,8 · 99 | 1 | 13 sem evidência no trecho |
| [`corpus_chat.jsonl`](saida/corpus_chat.jsonl) | 37 diálogos (12 recusas) | 146 · 206,8 · 302 | 0 | 1 fora das regras |

- **Por documento (trechos):** Detran-SP 22 · BPC 18 · Poupatempo 9 · Cadastro Único 8 · CIN gov.br 4.
- **Limpeza:** de 24.384 para 23.639 tokens (−3%). No PDF do BPC, que tem cabeçalho e rodapé em todas as páginas, a redução foi de 8%.
- **Dados pessoais:** nenhum CPF, e-mail, telefone ou nome nos três corpora. Os documentos oficiais não trazem dados pessoais; o exemplo de texto colado mostra a anonimização funcionando (1 CPF, 1 e-mail, 1 telefone e 2 nomes mascarados).
- **Revisão humana:** 42 exemplos (20% dos corpora gerados) sorteados para revisão em [`revisao/revisao.csv`](revisao/revisao.csv). A conferência também achou um erro fora da amostra, já corrigido: a resposta confundia o prazo para **dirigir** com a CNH vencida (30 dias) com um prazo para **renovar**. A evidência existia no trecho, então a checagem automática não pegou; é o tipo de erro que só a leitura humana encontra.
- **Geração:** `openai/gpt-oss-120b` no Groq, temperatura 0,2, com os prompts registrados no relatório.


## Decisões
- **Cabeçalhos e rodapés** são as linhas que se repetem no topo ou no fim de pelo menos metade das páginas do PDF. Isso funciona para qualquer documento, sem lista fixa de frases.
- **URL no meio da frase** vira só o domínio ("acesse gov.br"), porque é o que o cidadão precisa. URL sozinha na linha é removida.
- **Números de atendimento público** (135, 121, 0800) não são mascarados: não são dados pessoais e são informação útil.
- **Nomes de pessoas:** o spaCy marca entidades como pessoa, e regras descartam nomes de órgãos, documentos, programas e siglas (ele marcava "CRAS" e "Formulário Renach" como pessoa).
- **Fidelidade:** cada resposta gerada traz uma evidência copiada do trecho. Se a evidência não estiver no trecho, o exemplo é descartado. Depois, 20% de cada corpus gerado passa por revisão humana em [`revisao/revisao.csv`](revisao/).
- **Valores em reais** ficam fora das perguntas: o PDF do BPC é de 2021 e os valores estão desatualizados.
- **Tokens** contados com o `cl100k_base` do tiktoken.

## Execução
**No Google Colab:** abra [`fabrica_corpus.ipynb`](fabrica_corpus.ipynb) e rode tudo. A primeira célula baixa o repositório e instala as bibliotecas.

**Localmente:**
```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_md
python src/gerar_corpus.py          # gera saida/ a partir de entrada/
python src/app.py                   # interface em http://127.0.0.1:7861
```
A chave do Groq (`GROQ_API_KEY` no `.env` da raiz ou nos segredos do Colab) só é necessária para gerar exemplos novos. As respostas do modelo ficam em `cache/geracao.json`, então tudo roda do início ao fim sem chave.

**Bibliotecas:** pdfplumber, python-docx, BeautifulSoup, charset-normalizer, tiktoken, spaCy, groq, Gradio e matplotlib.

## Estrutura
| Caminho | Conteúdo |
|---|---|
| `fabrica_corpus.ipynb` | Notebook com todas as etapas, do upload ao relatório de qualidade |
| `src/fabrica_corpus.py` | Ingestão, limpeza, normalização, anonimização e segmentação |
| `src/geracao.py` | Geração das perguntas e respostas e dos diálogos, com os prompts |
| `src/gerar_corpus.py` | Pipeline completo e revisão humana |
| `src/app.py` | Interface em Gradio |
| `entrada/` | Documentos de entrada e `fontes.csv` |
| `saida/` | `corpus_texto.jsonl`, `corpus_qa.jsonl`, `corpus_chat.jsonl` e `relatorio_qualidade.json` |
| `revisao/revisao.csv` | Amostra de 20% revisada pela equipe |

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
