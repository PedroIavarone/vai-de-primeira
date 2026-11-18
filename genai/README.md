# Assistente da Jornada

Monta a jornada de cada cidadão para tirar a Carteira de Identidade Nacional, renovar a CNH, se inscrever no Cadastro Único e entender o BPC: o que levar, onde ir e se é gratuito, **sempre citando a fonte oficial** e em linguagem adaptada ao perfil da pessoa.

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
- **Fonte:** o corpus limpo e anonimizado de [`pln/`](../pln/) (`pln/saida/corpus_texto.jsonl`, 61 trechos de 5 documentos oficiais), completado pelas 4 páginas oficiais que o corpus não cobre (lista em [`fontes/fontes.csv`](fontes/fontes.csv), texto em `fontes/texto/`). São 84 trechos no total.
- **Trechos:** os do corpus do PLN (256 a 512 tokens, cortados entre frases) e, nas páginas complementares, trechos de cerca de 220 palavras com sobreposição de 40.
- **Busca híbrida:** `multilingual-e5-small` + FAISS (por significado) combinado com BM25 (por palavra exata), por Reciprocal Rank Fusion, com filtro por serviço.
- **Envio ao modelo:** 6 trechos por busca, cada um reduzido à janela de 1.400 caracteres mais relevante para a pergunta.

## Resultados
Avaliação com 30 perguntas (20 no tema, 5 fora do tema, 5 pegadinhas). Detalhes, comparação entre versões e análise de erros em [`avaliacao/README.md`](avaliacao/README.md).

| Acerto geral | No tema | Fora do tema | Pegadinhas | Fonte certa | Fidelidade |
|---|---|---|---|---|---|
| **100%** | 100% | 100% | 100% | 100% | 95,7%* |

\* O caso marcado foi um falso alarme, conferido contra a fonte. Resultado da v3, com o corpus do PLN como base. Uma resposta fiel à fonte ainda citou um valor desatualizado do BPC (veja a análise de erros).

**Exemplos de entradas e saídas:** as 30 perguntas da avaliação, com a resposta, as fontes, as ferramentas usadas e o encaminhamento de cada uma, estão em [`avaliacao/respostas.csv`](avaliacao/respostas.csv); cinco delas estão na documentação técnica.

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
- [x] Base de conhecimento a partir do corpus do módulo `pln/`
- [x] Repetir a avaliação completa com o LLM sobre a nova base
- [ ] Guardar a data de cada fonte e evitar valores em reais que mudam todo ano
- [ ] Modelo pequeno local, ajustado com os corpora de perguntas e de diálogos do módulo `pln/`, para não depender de API externa
- [ ] Fontes de outros estados além de São Paulo
- [ ] Avaliar a clareza das respostas com pessoas do público
