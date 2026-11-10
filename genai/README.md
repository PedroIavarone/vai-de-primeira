# Assistente da Jornada

Agente que monta a jornada de cada cidadão: o que levar, onde ir, se é gratuito, sempre citando a fonte oficial. Responde em linguagem simples, adaptada ao perfil da pessoa.

**Responsável:** Pedro Iavarone Custódio

## Funcionalidades
- Recuperação de trechos da base de conhecimento oficial (RAG) gerada em `pln/`.
- LLM via Groq (`openai/gpt-oss-120b`).
- Ferramentas do agente: `buscar_requisitos`, `checar_documentos`, `consultar_fila`, `verificar_link`.
- Recusa assuntos fora do escopo e encaminha para o órgão adequado (CRAS, Defensoria Pública, UBS).
- Não decide direito a benefício: orienta e encaminha.

## Integração
Saída no formato de `POST /perguntar` em [docs/contratos.md](../docs/contratos.md). Somente dados fictícios são enviados ao LLM.

## Próximos passos
- [ ] Indexar o corpus de `pln/`
- [ ] Agente com as quatro ferramentas
- [ ] Interface de teste em Gradio
- [ ] Conjunto de avaliação: perguntas no escopo, fora do escopo e casos de golpe, com métricas de acerto, fidelidade à fonte e alucinação
