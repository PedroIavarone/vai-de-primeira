# API de integração

Ponto único de acesso do app e do totem. Recebe as solicitações do cidadão, encaminha para cada módulo e calcula o Índice de Prontidão.

## Funcionalidades
- `GET /fila`: espera atual de cada unidade.
- `POST /checar-documento`: recebe uma imagem e devolve tipo, qualidade e orientação.
- `POST /perguntar`: pergunta em linguagem natural, resposta com fontes oficiais.
- `POST /prontidao`: Índice de Prontidão (0 a 100) com componentes e pendências. Regras em `prontidao.py`.

## Integração
Contratos completos em [docs/contratos.md](../docs/contratos.md). Endpoints ainda não ligados ao módulo definitivo respondem com dados de demonstração (`"simulado": true`).

## Execução
```bash
pip install -r requirements.txt
uvicorn main:app --reload
python -m pytest -q
```

## Próximos passos
- [ ] Ligar `/fila` ao banco alimentado pelo totem
- [x] Ligar `/checar-documento` ao modelo de visão
- [x] Ligar `/perguntar` ao Assistente da Jornada
- [ ] Endpoint agregado de prontidão por região para o painel
