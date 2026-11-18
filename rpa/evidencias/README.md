# Evidências do robô

Execuções de 17/11/2026 com data de referência 12/11/2026 e dados fictícios.

| Arquivo | O que mostra |
|---|---|
| `execucao_normal_200_cidadaos.log` e `execucao_normal_resumo.json` | Base de 200 linhas: 195 lidas, 5 inválidas para revisão humana, 102 pessoas com aviso, 91 e-mails enviados à caixa de teste, 11 sem consentimento, 23 itens de revisão humana, 4 sites oficiais no ar |
| `excel_do_gestor.xlsx` | Relatório do gestor: demanda por região (com gráfico), avisos, revisão humana e resumo da execução |
| `execucao_repetida_idempotencia.log` | Segunda execução no mesmo dia: os 91 avisos aparecem como "já avisado antes" e nenhum é reenviado |
| `falha_email.log` | Servidor de e-mail fora do ar: 3 tentativas com espera de 1 s e 2 s por aviso, revisão humana e suspensão dos envios depois de 3 falhas seguidas |
| `falha_llm.log` | LLM com chave inválida: 3 tentativas por tipo de aviso e uso do texto pronto, sem parar a execução |
| `falha_site.log` | Site oficial fora do ar: 3 tentativas e o aviso sai sem aquele link |
| `falha_base.log` | Base inexistente: nada é enviado e a execução termina com segurança |
| `exemplo_email.eml` | E-mail de aviso como chega ao cidadão, com o motivo, o canal oficial e como parar de receber |

As simulações de falha usaram `testes/cidadaos_exemplo.csv` com um banco novo, para que houvesse avisos a enviar. Os logs registram o id do cidadão, nunca o e-mail.
