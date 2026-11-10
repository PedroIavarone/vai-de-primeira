# Identidade visual · Vai de Primeira

Arquivos e cores oficiais da marca, usados no app, no totem, no painel e em todo material do projeto.

## Arquivos
| Arquivo | Uso |
|---|---|
| `logo.png` / `logo.svg` | Logo completo (ícone + nome). Fundo claro. |
| `logo_branco.png` | Logo para fundo escuro. |
| `icone.png` / `icone.svg` | Só o ícone: favicon do app, totem, avatar. |
| `paleta.png` | Referência visual das cores. |

O ícone é um visto dentro de um quadrado azul: a ideia de **resolvido na primeira ida**.

## Cores
Paleta básica: fundo branco ou cinza-claro, texto grafite e **uma cor principal, o azul**. Verde, laranja e vermelho aparecem **só como status**.

| Nome | Hex | Uso |
|---|---|---|
| Azul | `#1F5FAD` | Cor principal: logo, títulos, botões, cabeçalho |
| Grafite | `#1F2933` | Texto |
| Cinza | `#667085` | Texto secundário, legendas |
| Cinza-claro | `#F2F4F7` | Fundo de telas e cartões |
| Borda | `#D0D5DD` | Linhas e bordas |
| Azul-claro | `#E8F0FB` | Destaque suave (ex.: cartão do Índice de Prontidão) |
| Verde | `#1E7F4F` | Status: pronta, documento ok |
| Laranja | `#A84A08` | Status: quase, pendência |
| Vermelho | `#B42318` | Status: não pronta, erro |

Contraste: todas as cores de texto passam no nível AA de acessibilidade sobre branco, e o texto branco passa sobre o azul.

## Fonte
**Atkinson Hyperlegible** (Google Fonts, gratuita). Foi criada para pessoas com baixa visão, o que reforça o compromisso de acessibilidade do produto.
- App (React): `<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">`
- Documentos: Atkinson Hyperlegible em títulos e figuras; Arial no texto corrido.

## Uso da marca
- Nome sempre escrito **Vai de Primeira** (V e P maiúsculos).
- Não usar logos, nomes ou cores de órgãos públicos ou empresas.
- No app, os status do Índice de Prontidão usam: verde (pronta), laranja (quase), vermelho (não pronta).
