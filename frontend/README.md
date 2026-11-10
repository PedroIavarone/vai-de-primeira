# App do cidadão e modo totem

Aplicação web em React + Vite usada pelo cidadão no celular e no totem da unidade de atendimento.

**Responsável:** Guilherme Nakamura

## Funcionalidades
- Login local, cadastro do cidadão e consulta dos serviços em andamento (dados no navegador).
- Jornada de cada serviço: o que levar, se é gratuito, onde ir.
- Conferência de documentos pela câmera, com o Índice de Prontidão em destaque.
- Fila das unidades, assistente com voz e modo totem com fonte grande.
- Acessibilidade: VLibras, alto contraste, navegação por teclado e leitura em voz.
- Privacidade: CPF mascarado, consentimento para avisos e opção de apagar os dados.

## Integração
Consome a API em `http://127.0.0.1:8000` (`/perguntar`, `/checar-documento`, `/fila`, `/prontidao`). Identidade visual em [docs/identidade_visual](../docs/identidade_visual/).

## Próximos passos
- [ ] Criar o projeto (`npm create vite@latest . -- --template react`)
- [ ] Rotas: `/login`, `/cadastro`, `/meus-servicos`, `/servico/:id`, `/conferir`, `/fila`, `/assistente`, `/totem`, `/privacidade`
- [ ] Integração com a API
- [ ] Testes de acessibilidade
