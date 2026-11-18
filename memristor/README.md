# Memória de picos

Simulação no Falstad de um memristor que registra quando uma unidade de atendimento fica cheia no mesmo horário com frequência. Picos esporádicos mudam pouco a resistência; picos recorrentes a derrubam, e o estado continua guardado quando o estímulo é retirado.

**Ligação com o projeto:** o totem do módulo [`iot/`](../iot/) já classifica a fila como cheia. Um memristor por faixa de horário receberia um pulso a cada fila cheia e, abaixo de um limite de resistência, a faixa vira "pico recorrente": o app sugere outro horário e o gestor sabe onde reforçar o atendimento.

## Circuito
Dois ramos iguais no mesmo circuito: fonte de pulsos de 5 V e 100 µs, chave, memristor (modelo HP: Ron 100 Ω, Roff 16 kΩ, D 10 nm, µv 5×10⁻¹³ m²/(V·s)) e resistor de 1 kΩ. O ramo A recebe 1 pulso a cada 10 ms; o ramo B, 1 pulso a cada 1 ms. Aos 80 ms as chaves são abertas.

- Arquivo do circuito: [`circuito_memristor.txt`](circuito_memristor.txt)
- Link que abre o circuito no Falstad: [`link_falstad.txt`](link_falstad.txt)

## Resultados
| Momento | A: picos esporádicos | B: picos recorrentes |
|---|---|---|
| Início | 16,000 kΩ | 16,000 kΩ |
| 30 ms | 15,055 kΩ (3 pulsos) | 5,574 kΩ (30 pulsos) |
| 80 ms, fim do estímulo | 14,011 kΩ (8 pulsos) | 100 Ω (saturou com 36 pulsos) |
| 136 ms, sem estímulo | 14,011 kΩ | 100 Ω |

Sem corrente, o estado não muda: a resistência ficou idêntica nos 56 ms sem estímulo. Série completa em [`evidencias/resistencia_no_tempo.csv`](evidencias/resistencia_no_tempo.csv), gráfico e capturas do Falstad em [`evidencias/`](evidencias/).

**Limites:** tempo comprimido (1 pulso representa um evento real), modelo ideal sem perda de estado, sem limiar e sem variação entre peças, e saturação depois de 36 pulsos. Para esquecer picos antigos seria preciso um pulso de polaridade inversa, que não foi simulado.

## Relatório
[`Relatorio_Memoria_de_Picos.docx`](Relatorio_Memoria_de_Picos.docx): vínculo com o desafio, circuito, ensaios, análise e reprodução.

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
