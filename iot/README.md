# Totem e fila ao vivo

Totem com ESP32 na entrada da unidade de atendimento. Ele conta quem entra e quem sai, mede o calor do ambiente, percebe quando alguém se aproxima e tem um botão de "preciso de ajuda". Com esses dados, o cidadão vê a espera real antes de sair de casa, e a equipe é avisada quando a fila enche, quando faz calor demais para quem espera em pé ou quando alguém pede ajuda.

**Para quem:** Dona Francisca, que gasta 1h30 de ônibus para chegar à unidade. Saber que a Central Centro está com 50 minutos de espera e a Central Leste com 10 decide se ela resolve tudo de primeira ou perde o dia.

## Como funciona
```
ESP32 (Wokwi)                         broker MQTT público               Node-RED                         API
PIR ──────────── presença ──┐                                      ┌─ valida a leitura                  GET /fila
2 sensores de passagem ─ contagem ─┼──► vdp/unidade/centro/fila ──►├─ calcula espera e status ──► SQLite ──► leitura real
DHT22 ───────── temp e umidade ─┤   vdp/unidade/centro/ambiente   ├─ grava tudo no banco                  da unidade
botão de ajuda ── pedido ───────┘   vdp/totem/t1/presenca|ajuda   └─ alerta: fila cheia, calor, ajuda ──► Telegram
```

| Tópico | Exemplo |
|---|---|
| `vdp/unidade/{id}/fila` | `{"unidade":"centro","pessoas":23}` |
| `vdp/unidade/{id}/ambiente` | `{"unidade":"centro","temp_c":29.5,"umidade":61}` |
| `vdp/totem/{id}/presenca` | `{"totem":"t1","presente":true}` |
| `vdp/totem/{id}/ajuda` | `{"totem":"t1","ajuda":true}` |

**Tratamento dos dados (Node-RED):**
- **Validação:** contagem fora de 0 a 500, temperatura fora de -10 a 60 °C ou evento desconhecido vão para a tabela `descartes`, com o motivo. Nada inválido chega à fila mostrada ao cidadão.
- **Espera estimada:** pessoas × 1,8 min. Status `tranquila` (até 20 min), `moderada` (21 a 45) ou `cheia` (mais de 45).
- **Alertas só na mudança de estado:** fila que fica cheia (e quando volta ao normal) e calor acima de 30 °C (rearma abaixo de 28 °C). Assim a equipe não recebe o mesmo alerta a cada leitura. Todo pedido de ajuda vira alerta.
- **Banco:** `iot/dados/iot.sqlite`, com as tabelas `leituras_fila`, `leituras_ambiente`, `eventos_totem`, `alertas` e `descartes`.
- **Na API**, `GET /fila` usa a leitura mais recente da unidade com sensor (últimos 15 min) e marca `"origem": "sensor"`. As outras unidades continuam com a estimativa, marcadas `"origem": "simulado"`.

## O que é real e o que é simulado
| Parte | Situação |
|---|---|
| ESP32 e sensores | **Simulados no Wokwi** (ESP32, PIR, 2 sensores de passagem, DHT22, botão, LED e buzzer). O firmware é o mesmo de uma placa física |
| MQTT | **Real**, no broker público `broker.hivemq.com` |
| Node-RED, banco e alertas | **Reais**, rodando localmente |
| Simulador em Python | Publica as mesmas mensagens do ESP32 para repetir os cenários de teste sem abrir o Wokwi |
| Outras unidades | Uma só unidade tem totem; as demais usam a estimativa da API |

## Execução
```bash
cd iot/node-red && npm install && npm start            # Node-RED em http://127.0.0.1:1880
python iot/simulador/simulador_totem.py --cenario todos  # ou normal, cheia, ajuda, calor, invalido
```
**ESP32 no Wokwi:** abra o projeto de `wokwi/` ([no Wokwi](https://wokwi.com/projects/480881468470360065)) e clique em Play. O sketch usa [`esp32/mqtt_vdp.h`](esp32/mqtt_vdp.h) para conectar ao Wi-Fi do Wokwi e publicar no broker.

**Alertas no Telegram (opcional):** crie um bot com o @BotFather e coloque `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` no `.env` da raiz. Sem eles, os alertas ficam registrados só no banco.

## Limitações
- **Broker público:** qualquer pessoa pode publicar nos mesmos tópicos. Por isso toda leitura é validada e o conteúdo não tem dado pessoal. Em produção: broker próprio com usuário, senha e TLS.
- **Queda de conexão:** nos testes, o broker derrubou a conexão do Node-RED por 16 s e as mensagens desse intervalo se perderam. O Node-RED agora usa sessão persistente (client id fixo, clean session desligado), e o broker guarda as mensagens QoS 1. O ESP32 publica com QoS 0 (limite da PubSubClient): um evento enviado durante uma reconexão pode se perder.
- **Contagem por sensores de passagem:** duas pessoas lado a lado contam como uma, e quem para na porta pode gerar contagem dupla. Uma câmera com contagem por visão seria mais precisa, mas é mais cara e levanta questões de privacidade.
- **Espera estimada** por tempo médio fixo (1,8 min por pessoa). O ideal é aprender esse tempo com o histórico de cada unidade.
- **Simulação:** o circuito foi testado no Wokwi, não em placa física. No Wokwi foram testados conexão, ambiente, presença e pedido de ajuda, com a mensagem chegando ao banco do Node-RED; a contagem pela porta foi testada com o simulador em Python.

## Evidências
[`evidencias/`](evidencias/): fluxo do Node-RED, monitor serial do Wokwi com presença e ajuda, alertas, eventos e descartes exportados do banco e a resposta de `GET /fila` com a leitura do sensor. Documento da disciplina: [`Documento_Totem_e_Fila_ao_Vivo.docx`](Documento_Totem_e_Fila_ao_Vivo.docx).

## Estrutura
| Caminho | Conteúdo |
|---|---|
| `esp32/` | Firmware do totem (`mqtt_vdp.h` cuida do Wi-Fi e do MQTT) |
| `wokwi/` | Projeto do Wokwi (`diagram.json`, sketch e `libraries.txt`) |
| `node-red/flows.json` | Fluxo do Node-RED |
| `simulador/simulador_totem.py` | Simulador dos cenários de teste |
| `evidencias/` | Prints e vídeos das situações testadas |

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
