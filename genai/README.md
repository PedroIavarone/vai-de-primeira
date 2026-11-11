# Assistente da Jornada

Monta a jornada de cada cidadão para tirar a Carteira de Identidade Nacional, renovar a CNH, se inscrever no Cadastro Único e entender o BPC: o que levar, onde ir e se é gratuito, **sempre citando a fonte oficial** e em linguagem adaptada ao perfil da pessoa.

**Responsável:** Pedro Iavarone Custódio

## Como funciona
```
pergunta do cidadão
  → mascaramento de CPF, e-mail e telefone
  → agente (Groq · gpt-oss-20b) escolhe as ferramentas:
       buscar_requisitos   busca híbrida nos documentos oficiais (RAG)
       consultar_fila      espera atual das unidades (API /fila)
       checar_documento    conferência da foto do documento (API /checar-documento)
       verificar_link      confere se um site é canal oficial do governo
  → resposta final (Groq · gpt-oss-120b) em JSON validado, só com base nos resultados
  → se algo falhar: resposta segura, sem inventar
```

**Por que RAG e agente com ferramentas:** as regras de serviços públicos mudam (taxas, prazos, documentos) e não podem vir da memória do modelo. A recuperação garante que a resposta se apoia em páginas oficiais citáveis. As ferramentas conectam o assistente ao restante do Vai de Primeira (fila, conferência de documentos) e à proteção contra golpes.

**Por que dois modelos:** o plano gratuito do Groq limita 8 mil tokens por minuto por modelo. Um modelo menor decide as ferramentas e o maior escreve a resposta, e assim cada um usa o próprio limite.

## Base de conhecimento
- **Fonte:** o corpus limpo e anonimizado de [`pln/`](../pln/) (`pln/saida/corpus_texto.jsonl`), quando disponível. Até lá, 9 páginas oficiais de órgãos públicos (lista em [`fontes/fontes.csv`](fontes/fontes.csv)), extraídas em `fontes/texto/`.
- **Trechos:** de cerca de 220 palavras, com sobreposição de 40.
- **Busca híbrida:** `multilingual-e5-small` + FAISS (por significado) combinado com BM25 (por palavra exata), por Reciprocal Rank Fusion, com filtro por serviço.
- **Envio ao modelo:** 6 trechos por busca, cada um reduzido à janela de 1.000 caracteres mais relevante para a pergunta.

## Resultados
Avaliação com 30 perguntas (20 no tema, 5 fora do tema, 5 pegadinhas). Detalhes, comparação entre versões e análise de erros em [`avaliacao/README.md`](avaliacao/README.md).

| Acerto geral | No tema | Fora do tema | Pegadinhas | Fonte certa | Fidelidade |
|---|---|---|---|---|---|
| **96,7%** | 95% | 100% | 100% | 100% | 95,5%* |

\* O caso marcado foi um falso alarme, confirmado como fiel na revisão humana.

## Execução
```bash
pip install -r requirements.txt
# no .env da raiz: GROQ_API_KEY=...
python src/extrair_fontes.py          # extrai o texto das páginas oficiais salvas em fontes/brutas/
python src/app.py                     # interface em http://127.0.0.1:7860
python src/avaliar.py                 # avaliação com as 30 perguntas
```
Na API, `POST /perguntar` usa este assistente quando a chave do Groq está configurada.

## Integração
Saída no formato de `POST /perguntar` em [docs/contratos.md](../docs/contratos.md), com o campo extra `urls`, que traz os links das fontes na mesma ordem de `fontes`. Somente perguntas com dados pessoais mascarados são enviadas ao LLM.

## Próximos passos
- [x] Base de conhecimento com fontes oficiais e busca híbrida
- [x] Agente com as quatro ferramentas
- [x] Interface de teste em Gradio
- [x] Avaliação com 30 perguntas
- [ ] Trocar as páginas oficiais pelo corpus do módulo `pln/`, quando estiver pronto
