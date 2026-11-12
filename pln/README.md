# Base de conhecimento

Pipeline que transforma documentos públicos sobre CIN, CNH e Cadastro Único em um corpus limpo, anonimizado e pronto para o Assistente da Jornada.

## Funcionalidades
- Ingestão de PDF, TXT, DOCX, HTML e texto colado, registrando a origem de cada trecho.
- Limpeza (cabeçalhos, rodapés, URLs, hifenização) e normalização em UTF-8, preservando acentos e pontuação.
- Anonimização de CPF, e-mail, telefone e nomes.
- Segmentação em trechos de 256 a 512 tokens respeitando frases.
- Três saídas em JSONL: texto puro, perguntas e respostas, e diálogos (incluindo recusas).

## Integração
Saída em `pln/saida/`: `corpus_texto.jsonl` (base do RAG), `corpus_qa.jsonl`, `corpus_chat.jsonl`. Documentos de entrada em `pln/entrada/`, com a fonte de cada um.

## Próximos passos
- [ ] Selecionar os documentos oficiais
- [ ] Ferramenta com interface em Gradio
- [ ] Estatísticas de qualidade e remoção de duplicatas
