# Totem e fila ao vivo

Totem com ESP32 na entrada da unidade de atendimento. Conta quem entra e sai, mede o ambiente e oferece um botão de ajuda.

## Funcionalidades
- Sensores: PIR (presença no totem), dois sensores de passagem na porta, DHT22 (temperatura e umidade) e botão de ajuda.
- Publicação via MQTT nos tópicos `vdp/unidade/{id}/fila`, `vdp/unidade/{id}/ambiente`, `vdp/totem/{id}/presenca`, `vdp/totem/{id}/ajuda`.
- Node-RED recebe, grava no banco, estima a espera e envia alertas pelo Telegram.

## Integração
Formato das mensagens em [docs/contratos.md](../docs/contratos.md). A espera calculada alimenta `GET /fila` da API.

## Próximos passos
- [ ] Firmware do ESP32 (`esp32/`) e simulação no Wokwi (`wokwi/diagram.json`)
- [ ] Fluxo do Node-RED (`node-red/flow.json`)
- [ ] Persistência em banco
- [ ] Testes nos cenários fila normal, fila cheia, ajuda e calor
