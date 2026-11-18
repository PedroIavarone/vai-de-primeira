# Aviso proativo

Robô diário que encontra quem precisa resolver um documento ou benefício, avisa a pessoa antes que o problema aconteça e entrega ao gestor a demanda por região. Ele inverte a lógica do atendimento: em vez de o cidadão descobrir tarde demais que a CNH venceu ou que o Cadastro Único travou, **o serviço público procura o cidadão**.

**Para quem:** Seu Jorge, motorista de aplicativo, cuja CNH vence em 05/12; Dona Francisca, 67 anos, com o Cadastro Único parado desde 2023 e possível direito ao BPC; Ana, que acabou de ter um bebê.

## Como funciona
```
todo dia às 07:00
  → lê a base de cidadãos (Excel ou CSV, dados fictícios) e valida cada linha
  → regras: CNH vencendo em até 30 dias ou vencida · Cadastro Único sem atualização há mais de 2 anos
            · nascimento nos últimos 60 dias · 65 anos ou mais sem BPC (só sinaliza)
            · site informado pela pessoa que não é oficial (alerta de golpe)
  → pula quem não deu consentimento e quem já recebeu o mesmo aviso (SQLite)
  → escreve o texto com LLM, confere o texto e usa um texto pronto se falhar
  → confere se os sites oficiais do aviso estão no ar
  → envia o e-mail · registra · manda para revisão humana o que o robô não resolve
  → gera o Excel do gestor: demanda por região, avisos, revisão humana e resumo da execução
```

## Quadro de temas
| Tema | Onde é usado no fluxo | O que resolve |
|---|---|---|
| **Automação de planilhas (Excel)** | Leitura da base em `robo/base.py`; relatório do gestor em `robo/relatorio.py` (openpyxl, com gráfico) | A prefeitura já trabalha com planilhas: o robô lê a base sem digitação e entrega a demanda pronta para planejar a unidade móvel |
| **Automação de e-mail** | `robo/canais.py` (SMTP); caixa de teste local em `servidor_email_teste.py` | O aviso chega à pessoa sem ninguém escrever e-mail por e-mail |
| **Automação web e verificação de sites** | `robo/canais.py` consulta os sites oficiais com tempo limite; `robo/regras.py` confere se o site informado pela pessoa é `gov.br` | O aviso nunca manda para um link fora do ar e alerta quem caiu num site que cobra por serviço gratuito |
| **IA generativa com regras** | `robo/mensagens.py`: o LLM (Groq, `gpt-oss-20b`) escreve o texto em linguagem simples por tipo de aviso e faixa etária; regras conferem o texto | Mensagem acolhedora e clara para quem lê com dificuldade, sem prometer direito nem incluir link |
| **Agendamento** | `main.py --agendar` executa todo dia às 07:00 | Ninguém precisa lembrar de rodar o robô |
| **Banco de dados e idempotência** | `robo/registro.py` (SQLite): avisos enviados, revisão humana e execuções | A mesma pessoa não recebe o mesmo aviso duas vezes, e tudo fica auditável |

**Por que esses temas:** o problema é a pessoa descobrir tarde demais que precisa agir. Resolver isso exige achar quem precisa agir numa base que já existe (planilha), avisar pelo canal que a pessoa usa (e-mail), não mandar ninguém para um link quebrado ou falso (verificação de sites), escrever de um jeito que quem lê com dificuldade entenda (IA generativa com regras), rodar sem depender de alguém lembrar (agendamento) e não avisar duas vezes nem perder o histórico (banco de dados). Cada tema cobre uma dessas partes; sem qualquer um deles, o aviso não chega, chega errado ou chega repetido.

## Resiliência e segurança
- **Log** de cada execução em `saida/logs/`, com o id do cidadão (nunca o e-mail).
- **Novas tentativas com espera crescente** (1 s, 2 s, 4 s) no e-mail, nos sites e no LLM, com tempo limite em todas as chamadas.
- **Disjuntor:** depois de 3 falhas seguidas do servidor de e-mail, o robô para de tentar e manda o restante para revisão humana, sem travar a execução.
- **Caminho seguro em cada falha previsível:**

| Falha | O que o robô faz |
|---|---|
| Base ausente ou sem colunas obrigatórias | Não envia nada, registra o erro e termina com segurança |
| Linha com dado inválido (data, idade, e-mail, id repetido) | Pula a linha e manda para revisão humana, com o motivo |
| LLM sem chave, fora do ar, resposta vazia ou fora das regras | Usa o texto pronto do mesmo aviso |
| Site oficial fora do ar | Envia o aviso sem aquele link |
| Servidor de e-mail fora do ar | Tenta 3 vezes, manda para revisão humana e suspende os envios após 3 falhas seguidas |

- **Revisão humana** para dados inválidos, falhas de envio e **toda sinalização de BPC**: o robô nunca decide direito a benefício.
- **Chaves e senhas** só no `.env` da raiz, fora do código e do repositório.

## Execução
```bash
pip install -r requirements.txt
python main.py                                   # executa uma vez (base em dados/cidadaos.xlsx)
python main.py --base testes/cidadaos_exemplo.csv --data 2026-11-12
python main.py --agendar                         # todo dia às 07:00
python main.py --simular-falha email             # demonstra uma falha tratada: email, site, llm ou base
python validar.py                                # compara o robô com os casos rotulados
```
**Configuração (`.env` na raiz do repositório):**
- `GROQ_API_KEY`: opcional. Sem a chave, o robô usa os textos prontos.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: opcionais. **Sem usuário configurado, os e-mails vão para a caixa de teste local** (`saida/caixa_de_teste/`), sem sair do computador.

**Saídas** em `saida/`: `relatorios/demanda_<execução>.xlsx`, `relatorios/execucao_<execução>.json`, `logs/`, `caixa_de_teste/` e `avisos.sqlite`.

## Validação
**50 de 50 casos corretos** em `validacao/casos.csv` (resultado em [`validacao/resultado.md`](validacao/resultado.md)). Os casos incluem as fronteiras das regras: CNH com 30 e 31 dias para vencer e vencendo no dia, Cadastro Único na data exata de corte de 2 anos, 64 e 65 anos, bebê com 60 e 61 dias, site que imita o gov.br e linhas com dado inválido. Como 100% numa amostra pequena pode esconder erro, a análise considera também os casos de fronteira, que são onde uma regra mal escrita falharia primeiro. Evidências das execuções e das falhas simuladas em [`evidencias/`](evidencias/).

`python validar.py` compara as decisões do robô com casos rotulados à mão (`validacao/casos.csv`) e gera `validacao/resultado.md`, com acertos, precisão e recall por tipo de aviso e a lista dos casos com erro. `python main.py --simular-falha <tipo>` demonstra cada falha tratada, com o registro no log.

## Limites
- **Dados sintéticos:** a base de 200 cidadãos e os 50 casos rotulados foram feitos pela equipe. Os 50 acertos medem se as regras fazem o que foi especificado, não se as regras certas foram escolhidas; isso só um piloto com a prefeitura mostraria.
- **Regras fixas:** prazos como 30 dias para a CNH e 2 anos para o Cadastro Único estão no código. Se a regra oficial mudar, alguém precisa atualizar.
- **Texto do LLM:** é conferido por regras (sem promessa de direito, sem link, tamanho máximo), mas a clareza para quem lê com dificuldade não foi medida com pessoas.
- **Canal único:** o aviso sai só por e-mail. Quem não tem e-mail fica de fora até existir SMS ou aviso no app.

## Dados, ética e ODS
O robô trabalha só com **dados fictícios** e segue a LGPD por desenho: só avisa quem deu **consentimento**, todo e-mail traz como parar de receber, o LLM recebe apenas a situação genérica (por exemplo, "a CNH vai vencer") e a faixa etária, **nunca nome, e-mail, data ou município**, e o Excel do gestor não tem nome nem contato. O principal risco ético é tratar uma sinalização como decisão: por isso o possível direito ao BPC é apenas um convite para procurar o CRAS e sempre passa por revisão humana. Também existe o risco de excluir quem não tem e-mail; no produto, o mesmo aviso pode sair por SMS ou pelo totem da unidade. O robô contribui com o **ODS 10** (reduz desigualdades ao levar a informação a quem mais perde viagens e benefícios), o **ODS 9** (acesso à tecnologia no serviço público) e o **ODS 11** (serviços públicos mais acessíveis na cidade e no campo).

## Estrutura
| Caminho | Conteúdo |
|---|---|
| `main.py` | Ponto de entrada: execução única, agendamento e simulação de falhas |
| `validar.py` | Validação com casos rotulados |
| `servidor_email_teste.py` | Caixa de e-mail de teste local |
| `robo/` | Base, regras, mensagens, canais, registro, relatório e resiliência |
| `dados/cidadaos.xlsx` | Base fictícia de 200 cidadãos |
| `validacao/` | Casos rotulados e resultado da validação |
| `testes/cidadaos_exemplo.csv` | Base pequena com as personas e casos de erro |

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
