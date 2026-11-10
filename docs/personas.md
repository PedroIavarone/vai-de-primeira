# Personas e dados fictícios padrão

Personas de referência do produto, usadas em testes, dados de exemplo e demonstrações. **Todas são fictícias.**

Os valores do Índice de Prontidão foram calculados com a regra real de `api/prontidao.py`.

---

## P001 · Dona Francisca (persona principal)
| | |
|---|---|
| Idade | 67 anos |
| Onde mora | Zona rural de Itapeva (SP), a cerca de 1h30 de ônibus da central de atendimento |
| Vida | Trabalhou na roça a vida toda, mora sozinha, renda baixa e irregular |
| Tecnologia | Celular simples, usa WhatsApp quase só por áudio, lê com dificuldade |
| O que precisa | **Carteira de Identidade Nacional (CIN)** e **atualizar o Cadastro Único**, para depois pedir o BPC |
| Documentos que tem | Certidão de casamento antiga (papel gasto, com reflexo quando fotografa), CPF, RG antigo |
| Problema real | Já perdeu duas viagens: na primeira faltou documento, na segunda a certidão estava ilegível |
| Frase | *"Gastei a passagem duas vezes e voltei sem nada."* |

**Jornada (serviço CIN):**
| Momento | Índice | Faixa |
|---|---|---|
| Recebe o aviso do robô, ainda não fez nada | 15 | não pronta |
| Pergunta ao assistente e recebe a lista oficial | 30 | não pronta |
| Fotografa a certidão: **reflexo**. Unidade Centro com fila de 50 min | 44 | não pronta |
| Escolhe a Unidade Leste (10 min de espera) | 64 | quase |
| Tira a foto de novo, sem reflexo | **100** | **pronta** |

A passagem de **64 para 100** é o momento central da experiência: corrigir uma única foto deixa a pessoa pronta para ir.

---

## P002 · Seu Jorge
| | |
|---|---|
| Idade | 41 anos |
| Onde mora | Guaianases, zona leste de São Paulo |
| Vida | Motorista de aplicativo, depende da CNH para trabalhar |
| Tecnologia | Usa bem o celular, mas não tem tempo para descobrir regras |
| O que precisa | **Renovar a CNH**, que vence em **05/12/2026** |
| Documentos que tem | CNH atual, documento de identidade, comprovante de residência antigo |
| Problema real | Não sabe o que levar, se precisa de exame e se o site que achou na internet é oficial (é um site que cobra) |

**Jornada (serviço CNH):**
| Momento | Índice | Faixa |
|---|---|---|
| CNH ok, foto do comprovante **cortada**, fila de 30 min | 72 | quase |
| Refaz a foto do comprovante | 90 | pronta |

Bom exemplo para o alerta de **site falso** e para o **aviso proativo** ("sua CNH vence em 30 dias").

---

## P003 · Ana
| | |
|---|---|
| Idade | 27 anos |
| Onde mora | Cidade Tiradentes, zona leste de São Paulo |
| Vida | Mãe de um bebê de 1 mês, trabalho informal |
| O que precisa | **Incluir o bebê no Cadastro Único** |
| Documentos que tem | CPF dela e a certidão de nascimento do bebê |

**Jornada (serviço Cadastro Único):** CPF conferido ok e fila de 10 min dão **100, pronta**. Mostra que o sistema também diz quando a pessoa **já pode ir**.

---

## Registros para o robô (RPA)
Formato de `docs/contratos.md`. As três personas entram na base sintética junto com as outras pessoas fictícias. Os IDs P001 a P003 ficam reservados para elas.

```json
{"id": "P001", "nome": "Francisca (persona)", "municipio": "Itapeva", "cnh_validade": null,
 "cadunico_atualizado_em": "2023-03-14", "idade": 67, "consentiu_avisos": true}
{"id": "P002", "nome": "Jorge (persona)", "municipio": "São Paulo", "cnh_validade": "2026-12-05",
 "cadunico_atualizado_em": null, "idade": 41, "consentiu_avisos": true}
{"id": "P003", "nome": "Ana (persona)", "municipio": "São Paulo", "cnh_validade": null,
 "cadunico_atualizado_em": "2024-08-02", "idade": 27, "consentiu_avisos": true}
```

Eventos que o robô deve encontrar: **P001** com Cadastro Único desatualizado há mais de 2 anos e idade de 65 ou mais (sinalizar possível direito ao BPC); **P002** com CNH vencendo em até 30 dias, a partir de 05/11/2026; **P003** com o nascimento do bebê (evento de nascimento na base).

---

## Uso de dados
- Nenhum dado real: nada de CPF, RG ou foto de documento de verdade. Imagens de teste usam documentos fictícios ou modelos espécime.
- Depoimentos de pessoas reais, quando usados, são anônimos e autorizados.
