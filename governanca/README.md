# Painel e governança

Painel do gestor público e as regras de governança de IA que valem para todos os módulos do Vai de Primeira.

## Painel do gestor
[`painel/painel.html`](painel/painel.html), gerado por [`painel/gerar_painel.py`](painel/gerar_painel.py). Abra o arquivo no navegador. Os filtros de **região** e **serviço** recalculam os números e os gráficos na hora, sem servidor. O painel não tem filtro de período porque os dados simulados não têm data.

| Pergunta do gestor | Gráfico | Dados |
|---|---|---|
| Quem chega pronto para resolver? | Índice de Prontidão médio na chegada, por região e serviço | Simulados, com a regra real de `api/prontidao.py` |
| Por que as pessoas voltam sem resolver? | Motivos das idas perdidas | Simulados |
| O app ajuda? | Resolução na primeira ida por faixa do índice, com e sem o app | Simulados |
| Para onde levar a unidade móvel? | Desertos de atendimento: avisos do robô por unidade x deslocamento médio | Avisos reais do robô + deslocamento simulado |
| Quanta demanda vem por aí? | Avisos do robô por região e tipo | Execução real do robô (`rpa/`) |
| Quando a unidade lota? | Espera por unidade ao longo do dia | Curva da API e leituras reais do totem (`iot/`) |
| Os modelos estão funcionando? | Tabela de desempenho e revisão humana | Métricas reais de visão, assistente, PLN e robô |

Os dados simulados ficam em [`painel/atendimentos.csv`](painel/atendimentos.csv) (1.200 idas fictícias) e são marcados no painel. A chance de resolver em cada faixa do índice (93%, 62% e 25%) é uma premissa: no piloto, ela seria medida com o registro real dos atendimentos.

```bash
pip install plotly openpyxl
python governanca/painel/gerar_painel.py
```

## Humano no circuito
| Módulo | O que a IA faz | Quem decide |
|---|---|---|
| Conferência por foto | Diz se a foto está boa, borrada, com reflexo ou cortada | O atendente confere o documento original |
| Índice de Prontidão | Calcula a chance de resolver na primeira ida com regras explicáveis | O cidadão decide se vai; o índice não bloqueia ninguém |
| Assistente | Responde com base em páginas oficiais e cita a fonte | Pedido fora do tema ou de direito individual é encaminhado (CRAS, Defensoria) |
| Robô de avisos | Encontra quem precisa agir e escreve o aviso | Dado inválido, falha de envio e **toda sinalização de BPC** vão para revisão humana |
| Corpus de PLN | Gera perguntas e respostas com evidência | 20% dos exemplos são conferidos contra o documento antes do ajuste fino (1 corrigido, 4 removidos) |
| Totem e fila | Mede a fila e alerta | A equipe decide abrir guichê ou orientar a fila |

## Matriz de riscos de IA
Probabilidade e impacto de 1 (baixo) a 3 (alto).

| Risco | Módulo | P | I | Mitigação no projeto | Risco restante |
|---|---|---|---|---|---|
| Foto aprovada como boa quando o documento está ilegível | Visão | 2 | 3 | Limiar de confiança de 0,60 na qualidade (abaixo disso pede nova foto); a conferência final é do atendente | Médio |
| Documento brasileiro não reconhecido pelo detector | Visão | 3 | 2 | Teste de campo com documentos brasileiros fictícios; ajuste com imagens sintéticas; a pessoa informa o tipo quando o OCR falha | Médio |
| Resposta errada ou inventada do assistente | GenAI | 2 | 3 | RAG só com páginas oficiais, fonte citada, resposta validada em JSON, caminho seguro em caso de falha, avaliação com 30 perguntas e pegadinhas | Baixo |
| Resposta com tom de promessa de direito (ex.: "você tem direito ao BPC") | GenAI, RPA | 2 | 3 | Termos proibidos checados no texto; BPC sempre como "pode ter direito, procure o CRAS"; revisão humana | Baixo |
| Exclusão de quem não tem celular ou internet | Todos | 3 | 3 | Modo totem na unidade, sem login; aviso também por SMS ou pelo CRAS no produto; atendimento presencial sempre disponível | Médio |
| Vazamento de dados pessoais | Front, API, RPA | 1 | 3 | CPF guardado só como hash, senha com hash e sal, fotos não guardadas, mascaramento antes do LLM, `.env` fora do repositório | Baixo |
| Golpe com site falso que cobra por serviço gratuito | RPA, GenAI | 3 | 2 | Robô alerta quem informou site fora do gov.br; assistente tem ferramenta de verificação de link | Baixo |
| Viés regional: unidades móveis sempre para onde já há mais demanda | Governança | 2 | 2 | Painel mostra desertos de atendimento (demanda por unidade x deslocamento), não só volume | Médio |
| Dependência de serviço externo de LLM (limite, bloqueio, custo) | GenAI, PLN, RPA | 3 | 2 | Robô usa texto pronto sem o LLM; API responde em modo de demonstração; cache das gerações do PLN | Médio |
| Leitura falsa do sensor no broker MQTT público | IoT | 2 | 1 | Toda leitura é validada e as inválidas vão para a tabela de descartes; em produção, broker com usuário, senha e TLS | Baixo |

## LGPD
| Princípio | Como aparece no projeto |
|---|---|
| Finalidade e necessidade (art. 6º) | Cada módulo guarda só o que usa. O robô envia ao LLM só a situação genérica e a faixa etária, nunca nome, e-mail, data ou município |
| Base legal (art. 7º) | Avisos só com **consentimento** explícito, que começa desmarcado e pode ser retirado. Atendimento público como execução de política pública |
| Dados sensíveis e de crianças | O aviso de nascimento não traz dado do bebê; a base é fictícia |
| Segurança (art. 46) | Hash do CPF e da senha no app, fotos descartadas, chaves só no `.env`, broker sem dado pessoal |
| Direitos do titular (art. 18) | Tela "Meus dados" mostra o que está guardado e tem o botão "Apagar meus dados"; todo aviso traz como parar de receber |
| Decisão automatizada (art. 20) | Nenhuma decisão de direito é automática: BPC, documento e atendimento são decididos por pessoas |
| Anonimização | O corpus de PLN mascara CPF, e-mail, telefone e nomes; o painel do gestor só mostra contagens por região |

## Entrega
- **Vídeo de demonstração:** https://youtu.be/_aiLV_nW3Ow
- **Relatório (PDF):** [Documento_Integracao_Vai_de_Primeira.pdf](Documento_Integracao_Vai_de_Primeira.pdf)

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
