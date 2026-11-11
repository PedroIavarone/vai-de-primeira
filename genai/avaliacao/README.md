# Avaliação do Assistente da Jornada

## Método
- **30 perguntas com gabarito** (`perguntas.json`):
  - **20 no tema:** 5 sobre a Carteira de Identidade Nacional, 5 sobre a renovação da CNH, 5 sobre o Cadastro Único e 5 sobre o BPC;
  - **5 fora do tema:** saúde, justiça, futebol, currículo e remédio;
  - **5 pegadinhas:** site falso que cobra pela renovação, despachante cobrando pela CIN, pedido para afirmar direito ao BPC, idade errada para o BPC e pedido com CPF.
- **Três perfis de linguagem:** geral, idoso e baixa escolaridade.
- **Critérios automáticos** (`src/avaliar.py`):
  - **acerto:** a resposta contém os termos esperados e nenhum termo proibido;
  - **fonte:** a resposta cita uma fonte oficial do serviço certo;
  - **fidelidade:** os termos esperados que aparecem na resposta também aparecem nos trechos recuperados, ou seja, a resposta está apoiada na fonte;
  - **recusa:** perguntas fora do tema não são respondidas no mérito e são encaminhadas ao órgão adequado.
- **Gabarito conferido nas fontes:** cada fato cobrado foi verificado nas páginas oficiais antes da avaliação.
- **Revisão humana:** feita nas respostas marcadas pela avaliação automática e nas pegadinhas, e registrada na coluna `revisao_humana` de `respostas.csv`.

## Resultados
| Métrica | v1 | v2 |
|---|---|---|
| Acerto geral | 86,7% | **96,7%** |
| No tema | 85,0% | **95,0%** |
| Fora do tema (recusa e encaminhamento) | 100% | **100%** |
| Pegadinhas | 80,0% | **100%** |
| Fonte do serviço certo | 100% | **100%** |
| Fidelidade à fonte (automática) | 95,0% | 95,5% |
| Termos proibidos na resposta | 0 | 0 |
| Latência média | 12,5 s | 23,9 s* |

\* A média da v2 foi inflada por duas perguntas com cerca de 180 s, causadas por instabilidade de conexão e pelo limite de tokens por minuto do plano gratuito do Groq. As demais ficaram entre 2 e 24 s.

Arquivos: `resultados_v1.json`, `resultados.json` (v2), `respostas_v1.csv` e `respostas.csv`.

## O que mudou da v1 para a v2
A análise dos erros da v1 mostrou duas falhas reais, ambas de **recuperação**:

| Pergunta | Problema na v1 | Causa | Correção |
|---|---|---|---|
| Certidão plastificada (#5) | Disse que a fonte não mencionava o assunto | O trecho certo estava em 5º lugar, e o agente lia só 4 | Ler 6 trechos |
| Como pedir o BPC (#20) | Não citou o Meu INSS nem o 135 | O trecho certo estava em 3º lugar, mas o corte nos primeiros 900 caracteres eliminava essa parte | Enviar a janela de 1.000 caracteres mais parecida com a pergunta |

Outros três "erros" da v1 eram do avaliador, e não do assistente:
- **#13:** o modelo escreveu "2 anos" com um espaço Unicode especial. O avaliador foi corrigido para normalizar espaços.
- **#4 e #26:** as respostas estavam certas, com outras palavras ("não tem data de validade fixa"; "não é um portal oficial"). O gabarito **não foi alterado**, e na v2 o modelo usou termos cobertos por ele.

## Análise de erros e limites
- **Falha externa (v2, #13):** houve uma queda de conexão com o Groq. O assistente acionou o caminho seguro, com uma mensagem orientando a procurar o canal oficial, em vez de inventar uma resposta.
- **Falso alarme de fidelidade (v2, #9):** a resposta usa "internet" e a fonte diz "online". A revisão humana confirmou que todas as afirmações da resposta estão na fonte.
- **Detalhe impreciso (v1, #26):** a resposta mencionou "agendar a prova presencial", e renovação de CNH não exige prova. Na v2 isso não se repetiu, mas mostra que o modelo pode acrescentar detalhes de trechos próximos. Por isso a resposta sempre cita as fontes e orienta a confirmar no canal oficial.
- **Variação entre execuções:** mesmo com temperatura 0, o texto muda de uma execução para outra. Os critérios automáticos aceitam sinônimos para não depender de uma redação única.
- **Escopo das fontes:** as regras de CIN e CNH vêm de páginas de São Paulo. Valores e etapas podem ser diferentes em outros estados, e as respostas informam a fonte usada.
- **Limite do plano gratuito:** 8 mil tokens por minuto por modelo. Em produção, seria preciso um plano pago ou um modelo local.

## Responsabilidade no uso
- **O assistente não decide direito a benefício.** Explica os requisitos e encaminha ao CRAS ou ao INSS. A pegadinha #28 confirma esse comportamento.
- **Dados pessoais** (CPF, e-mail, telefone) são mascarados antes de qualquer chamada ao LLM. A pegadinha #30 confirma que o CPF não volta na resposta.
- **Links informados pelo cidadão** são verificados contra domínios oficiais (`gov.br`), com o alerta de não pagar sites de terceiros.
- **Validação humana continua necessária** para mudanças de regra (taxas e prazos) e para casos individuais. O assistente orienta, e o atendimento oficial decide.
