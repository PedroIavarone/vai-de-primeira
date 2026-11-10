# Aviso proativo

Robô agendado que encontra quem precisa ser avisado, envia a mensagem e gera o relatório de demanda para o gestor.

**Responsável:** Guilherme Nakamura

## Funcionalidades
- Leitura da base de cidadãos (fictícia).
- Regras: CNH vencendo em até 30 dias, Cadastro Único sem atualização há mais de 2 anos, nascimento registrado, possível direito ao BPC (apenas sinalizado).
- Mensagem gerada por LLM, com texto padrão quando o serviço falha.
- Envio por e-mail, verificação de links contra domínios oficiais e relatório em Excel por região.
- Resiliência: log, novas tentativas com espera, sem avisos duplicados e fila de revisão humana.

## Integração
Base no formato de cidadão em [docs/contratos.md](../docs/contratos.md); personas em [docs/personas.md](../docs/personas.md). Chaves no `.env`. Ponto de entrada: `python main.py`.

## Próximos passos
- [ ] Base fictícia `cidadaos.xlsx`
- [ ] Motor de regras e envio
- [ ] Tratamento de falhas e idempotência
- [ ] Validação com casos rotulados
