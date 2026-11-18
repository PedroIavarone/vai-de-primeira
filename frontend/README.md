# App do cidadão e modo totem

Aplicação web em **React + Vite** usada pelo cidadão no celular e no totem da entrada da unidade de atendimento.

## Problema
Quem precisa tirar a identidade nova, renovar a CNH, atualizar o Cadastro Único ou entender o BPC muitas vezes **perde a viagem**: falta um documento, a foto da certidão está ilegível ou a fila está tão longa que não dá tempo. Para quem mora longe e tem pouco dinheiro, cada viagem perdida custa caro.

## Para quem
- **Dona Francisca, 67 anos**, zona rural de Itapeva (SP). Lê com dificuldade e já perdeu duas viagens. Precisa da CIN e de atualizar o Cadastro Único.
- **Seu Jorge, 41 anos**, motorista de aplicativo. A CNH vence em dezembro e ele não pode ficar sem dirigir.
- **Ana, 29 anos**, acabou de ter um bebê e precisa incluir a filha no Cadastro Único.

## O que o app faz
| Tela | Rota | O que faz |
|---|---|---|
| Entrar e criar cadastro | `/login`, `/cadastro` | Login local. CPF com máscara e validação, senha mínima de 6 caracteres e aceite de avisos que começa desmarcado |
| Meus serviços | `/meus-servicos` | Serviços que a pessoa quer resolver, com situação e último Índice de Prontidão. Adicionar e remover |
| Jornada do serviço | `/servico/:id` | O que levar, onde ir, se é gratuito e as fontes oficiais. Botão para ouvir o resumo |
| **Conferir documentos** | `/conferir` | Foto de cada documento → conferência de qualidade pela IA (`POST /checar-documento`) → **Índice de Prontidão** (`POST /prontidao`) com o que falta |
| Fila agora | `/fila` | Espera de cada unidade (`GET /fila`), com contagem real do totem quando há sensor |
| Tirar dúvidas | `/assistente` | Assistente com IA (`POST /perguntar`): resposta em linguagem adaptada ao perfil, lista de documentos, se é gratuito e a fonte. Pergunta por voz e resposta em voz |
| Meus dados | `/privacidade` | Dados guardados (CPF mascarado), consentimento de avisos e **apagar meus dados** |
| Por que existimos | `/por-que` | História da Dona Francisca e a relação com os ODS 10, 9, 4 e 11 |
| Modo totem | `/totem` | Sem login, letra e botões grandes, resposta falada, botão "Preciso de ajuda" e fila das unidades. Volta ao início sozinho depois de 90 s |

**Processamento inteligente:** a solicitação do cidadão (uma foto ou uma pergunta) vai para a API, que usa a conferência por visão computacional e o assistente com recuperação em documentos oficiais. A resposta volta como ação: o Índice de Prontidão sobe ou desce, e o app mostra exatamente o que falta para ir com segurança. Quando o texto do documento não dá para ler, a pessoa diz qual documento fotografou e a qualidade conferida pela IA continua valendo.

## Componentes, props e estado
- `componentes/Basicos.jsx`: `Botao` (vira link quando recebe `para`), `CampoTexto` (rótulo, dica e erro ligados por `aria-describedby`), `Selo` e `Aviso` (mensagens com `aria-live`).
- `componentes/CartaoProntidao.jsx`: recebe o `resultado` da API por props e mostra o índice, a barra e as pendências.
- `componentes/Acessibilidade.jsx`: contexto com contraste e tamanho da letra, gravados no navegador.
- `componentes/Layout.jsx`: cabeçalho, rodapé, link "Pular para o conteúdo" e `RotaProtegida`.
- Estado local com `useState` e `useEffect` em cada tela; a fila se atualiza sozinha a cada 30 s (`useFila`).

## Proteção de dados
- Tudo fica no navegador (`localStorage`), centralizado em `servicos/armazenamento.js`.
- **O CPF não é guardado por inteiro:** a conta é identificada pelo hash SHA-256 do CPF, e a tela só mostra `***.456.789-**`.
- **A senha é guardada como hash SHA-256 com sal aleatório**, nunca em texto puro. O erro de login não diz se o CPF ou a senha está errado.
- As fotos dos documentos são conferidas e descartadas: nada é salvo.
- Consentimento de avisos explícito, que pode ser retirado a qualquer momento, e botão para apagar todos os dados.
- O assistente pede para não escrever CPF, e a API mascara CPF, e-mail e telefone antes de chamar o modelo de linguagem.

## Acessibilidade
- **VLibras** (tradução para Libras), fonte **Atkinson Hyperlegible** (feita para baixa visão) e cores da identidade visual com contraste AA.
- Barra no cabeçalho: **alto contraste**, **aumentar e diminuir a letra** (100% a 150%) e **"Ouvir esta página"** (Web Speech API, voz pt-BR).
- Navegação completa por teclado, foco visível, link "Pular para o conteúdo", `label` em todos os campos, mensagens de erro anunciadas e alvos de toque de pelo menos 44 px.

## ODS
- **ODS 10, Redução das desigualdades:** quem mais perde viagens é quem mora longe, lê com dificuldade e tem menos dinheiro.
- **ODS 9, Inovação e infraestrutura:** IA e sensores para o serviço público procurar o cidadão.
- **ODS 4, Educação de qualidade:** cada resposta ensina o caminho e como reconhecer sites falsos.
- **ODS 11, Cidades sustentáveis:** menos viagens perdidas e filas mais bem distribuídas entre as unidades.

## Execução
```bash
# 1. API (em outro terminal, na raiz do repositório)
cd api && pip install -r requirements.txt && uvicorn main:app --port 8000

# 2. App
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # versão de produção em dist/
```
A API fica em `http://127.0.0.1:8000`. Para outro endereço, crie `frontend/.env` com `VITE_API_URL=http://endereco:porta`. Sem a chave do Groq ou sem os modelos de visão, a API responde em modo de demonstração e o app avisa.

## Validação
- Fluxo completo testado no navegador: cadastro, sair, entrar, adicionar serviço, conferir uma foto, ver o Índice de Prontidão subir e apagar os dados.
- Conferido no `localStorage` que o CPF inteiro e a senha não aparecem em lugar nenhum.

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
