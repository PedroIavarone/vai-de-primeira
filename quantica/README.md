# Roadmap quântico

Estudo de onde a computação quântica ampliaria o Vai de Primeira quando ele sair de uma cidade piloto para o estado inteiro. Documento sem código: o foco é o raciocínio sobre gargalo, capacidade e momento certo.

## Resumo
- **Gargalo:** decidir todos os dias quem atender, em que unidade, em que horário e por qual rota passam as unidades móveis. É otimização combinatória: 100 mil pedidos × 200 locais × 40 faixas de horário já são 800 milhões de variáveis, e a rota das unidades móveis é NP-difícil. No protótipo, essa decisão já existe e é manual: o gestor olha o Excel do robô e o painel de governança para decidir para onde vai a unidade móvel.
- **Capacidade principal: otimização** (annealing quântico e QAOA), de forma híbrida, só em subproblemas e só se vencer o solucionador clássico com os mesmos dados.
- **Capacidade complementar: criptografia pós-quântica** (NIST FIPS 203, 204 e 205), que já pode começar, porque dados de identidade precisam continuar seguros por décadas. O hash SHA-256 que o app usa para CPF e senha continua seguro (Grover só reduz para cerca de 128 bits); o que migra é a troca de chaves e as assinaturas do TLS.

| Horizonte | IA clássica | Quântico | Para o cidadão |
|---|---|---|---|
| Hoje (2026-2027) | Avisos, assistente, conferência, Índice de Prontidão, fila real | Só migração para criptografia pós-quântica | Viagens perdidas evitadas e dados protegidos contra ataques futuros |
| 3 a 5 anos | Programação inteira e meta-heurísticas em escala estadual | Pilotos híbridos em subproblemas regionais, sempre comparados ao clássico | Unidades móveis onde há demanda reprimida |
| Mais de 5 anos | Previsão, conferência, assistente e explicação das decisões | Otimização quântica onde houver vantagem comprovada | Menos espera e deslocamento em todo o estado |

Ética, LGPD e ODS são analisados em cada horizonte: cobertura mínima por município contra viés, só dados agregados em nuvem quântica de terceiros, direito de revisão das decisões automatizadas (LGPD, art. 20), feita por um servidor e ODS 10, 11, 9 e 16.

## Documento
[`Roadmap_Quantico_Vai_de_Primeira.docx`](Roadmap_Quantico_Vai_de_Primeira.docx)

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
