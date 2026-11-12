# Contratos de dados

Formatos de dados trocados entre os módulos. Qualquer mudança de contrato é feita neste arquivo e na API no mesmo commit.

## MQTT (IoT → Node-RED)
Broker: `broker.hivemq.com:1883` (público, não enviar nada sensível). O Node-RED (`iot/node-red/flows.json`) assina os tópicos, valida e grava em `iot/dados/iot.sqlite`.

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
   {"id": "centro", "nome": "Central Centro", "pessoas": 30, "espera_min": 54, "status": "cheia",
    "origem": "sensor", "lido_em": "2026-11-14 10:31:58"},
   {"id": "leste", "nome": "Central Leste", "pessoas": 6, "espera_min": 11, "status": "tranquila", "origem": "simulado"}
 ]}
```
`status`: `tranquila` (espera até 20 min), `moderada` (21 a 45 min), `cheia` (mais de 45 min).
`origem` em cada unidade: `sensor` (leitura do totem nos últimos 15 min, com `lido_em`) ou `simulado` (estimativa). `simulado` no topo é `true` se alguma unidade for estimativa.

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
Campos extras da conferência real: `confianca_qualidade` (0 a 1) e `caixa` `[x0, y0, x1, y1]` em pixels. Quando nenhum documento é encontrado, `documentos` vem vazio e há uma `dica` no nível da resposta.
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
`servico` também pode ser `"bpc"`. A resposta do Assistente da Jornada inclui `urls`, com os links das fontes na mesma ordem de `fontes`.

### `POST /prontidao`
Índice de Prontidão: chance de resolver na primeira ida (0 a 100). Regras explicáveis em `api/prontidao.py`.

Envio (os documentos vêm das respostas de `/checar-documento`):
```json
{"servico": "cin", "unidade_id": "centro", "orientado": true,
 "documentos": [{"tipo": "certidao", "qualidade": "reflexo"}]}
```
Resposta:
```json
{"simulado": true, "servico": "cin", "indice": 64, "faixa": "quase",
 "componentes": {"documentos": 24, "fila": 25, "orientacao": 15},
 "pendencias": ["A foto da certidão de nascimento ou de casamento está com reflexo, incline o papel e tire de novo."],
 "versao_regra": "1.0"}
```
| Componente | Pontos | Regra |
|---|---|---|
| Documentos | até 60 | Obrigatório conferido e ok = peso cheio; com problema = 40% do peso; não conferido = 0 |
| Fila | até 25 | Até 20 min = 25; até 45 min = 15; mais = 5; sem dado = 15 |
| Orientação | até 15 | Já recebeu a lista oficial do assistente |

`faixa`: `pronta` (80 ou mais), `quase` (50 a 79), `nao_pronta` (menos de 50).
Obrigatórios: CIN → certidão · CNH → CNH atual e comprovante · Cadastro Único → CPF (ou título de eleitor) do responsável; o comprovante é recomendado e não conta no índice.

## Cidadão sintético (`rpa/`)
Base do robô em `rpa/dados/cidadaos.xlsx` (ou `.csv`), uma linha por pessoa fictícia. Datas em `AAAA-MM-DD`; sim/não como `sim` ou `nao`.

| Coluna | Exemplo | Obrigatória | Observação |
|---|---|---|---|
| `id` | `C042` | sim | Único |
| `nome` | `Pessoa Fictícia 42` | sim | Nunca enviado ao LLM |
| `email` | `c042@exemplo.test` | se `consentiu_avisos` | Só caixas de teste |
| `municipio` | `Itapeva` | sim | |
| `regiao` | `Sudoeste Paulista` | não | Agrupa a demanda no Excel do gestor |
| `idade` | `67` | sim | 0 a 120 |
| `cnh_validade` | `2026-12-05` | não | Vazio = não tem CNH |
| `cadunico_atualizado_em` | `2023-06-10` | não | Vazio = não está no Cadastro Único |
| `recebe_bpc` | `nao` | não | |
| `filho_nascido_em` | `2026-10-14` | não | |
| `link_informado` | `https://renovacnh-rapido.com.br` | não | Site que a pessoa disse ter usado |
| `consentiu_avisos` | `sim` | sim | Sem consentimento, nenhum aviso é enviado |

Casos de validação (`rpa/validacao/casos.csv`): as mesmas colunas e mais `esperado`, com os avisos certos separados por `;` (`cnh_vencendo`, `cnh_vencida`, `cadunico_desatualizado`, `nascimento`, `bpc_possivel`, `link_suspeito`), `nenhum` ou `revisao` (dado inválido).
