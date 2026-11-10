# Contratos de dados

Formatos de dados trocados entre os módulos. Qualquer mudança de contrato é feita neste arquivo e na API no mesmo commit.

## MQTT (IoT → Node-RED)
Broker de teste: `broker.hivemq.com:1883` (público, não enviar nada sensível).

| Tópico | Publicado por | Exemplo |
|---|---|---|
| `vdp/unidade/{id}/fila` | ESP32 da porta | `{"unidade":"centro","pessoas":23,"ts":"2026-11-14T10:32:00"}` |
| `vdp/unidade/{id}/ambiente` | ESP32 da porta | `{"unidade":"centro","temp_c":29.5,"umidade":61}` |
| `vdp/totem/{id}/presenca` | ESP32 do totem | `{"totem":"t1","presente":true}` |
| `vdp/totem/{id}/ajuda` | ESP32 do totem | `{"totem":"t1","ajuda":true}` |

## API de integração (`api/`)

### `GET /fila`
```json
{"simulado": true, "atualizado_em": "2026-11-14T10:32:00",
 "unidades": [
   {"id": "centro", "nome": "Central Centro", "pessoas": 23, "espera_min": 40, "status": "cheia"},
   {"id": "leste", "nome": "Central Leste", "pessoas": 6, "espera_min": 10, "status": "tranquila"}
 ]}
```
`status`: `tranquila` (espera até 20 min), `moderada` (21 a 45 min), `cheia` (mais de 45 min).

### `POST /checar-documento`
Envio: `multipart/form-data` com o campo `arquivo` (imagem).
```json
{"simulado": true, "latencia_ms": 84,
 "documentos": [
   {"tipo": "cnh", "confianca": 0.93, "qualidade": "ok", "dica": null},
   {"tipo": "certidao", "confianca": 0.81, "qualidade": "reflexo",
    "dica": "Incline o papel para tirar o reflexo."}
 ]}
```
`tipo`: `cin`, `cnh`, `cpf`, `certidao`, `comprovante_residencia`, `desconhecido`.
`qualidade`: `ok`, `borrado`, `reflexo`, `cortado`.

### `POST /perguntar`
Envio:
```json
{"pergunta": "O que preciso para tirar a identidade nova?", "perfil": "idoso"}
```
`perfil`: `geral`, `idoso`, `baixa_escolaridade`.

Resposta:
```json
{"simulado": true, "servico": "cin",
 "resposta": "Para tirar a Carteira de Identidade Nacional...",
 "documentos_necessarios": ["Certidão de nascimento ou de casamento"],
 "gratuito": true, "fontes": ["cin_govbr.html"], "encaminhar_para": null}
```
`encaminhar_para` é preenchido quando o assistente não deve responder (ex.: `"CRAS"`, `"Defensoria Pública"`).

## Cidadão sintético (`rpa/`)
```json
{"id": "C042", "nome": "Pessoa Fictícia 42", "municipio": "Itapeva",
 "cnh_validade": "2026-12-05", "cadunico_atualizado_em": "2023-06-10",
 "idade": 67, "consentiu_avisos": true}
```
