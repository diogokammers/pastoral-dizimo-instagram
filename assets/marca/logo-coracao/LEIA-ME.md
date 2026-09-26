# Logotipo "coração partido em 4" — estudo (proposta, não aprovada)

Status: **para avaliação do Diogo.** O ADR-002 mantém o logotipo adiado (`config.yaml`: `marca.simbolo: null`); nada aqui entra nos templates até uma decisão.

## Origem
- Referência trazida pelo Diogo na **rodada 6** (`assets/marca/propostas/rodada6-referencia/UC-ref.svg`, `build_logo18.py`, `prancha27.png`).
- Ícone aprovado do destaque "Dízimo" (ADR-007): `templates/icones/coracao-cheio.svg`. O L1 reproduz exatamente esse contorno, cruz e ângulos (21° / 15° / 8,5° / 21,8°), agora como peças vetoriais reais: 4 cantos + cruz central, sem máscara.

## Arquivos
- `build_logo.py`: gera tudo (`python assets/marca/logo-coracao/build_logo.py`). Parâmetros: `corte`, `cruz`, `arred`, `angulos` e cor por peça. Dependências só deste estudo: shapely, fonttools, uharfbuzz, playwright, Pillow.
- `svg/`: símbolos, lockups (texto em curvas) e avatares.
- `png/`: 2048 px com fundo transparente (4096 no L1), avatares 1080.
- `prancha-logo.png`: variações, teste de redução (512 / 110 / 32 px), fundos e lockups.

## Variações
| | O que muda | Uso sugerido |
|---|---|---|
| L1 principal | Igual ao ícone aprovado: vermelho #A3121C, corte médio (10/240) | Uso corrente |
| L2 corte fino | Corte 6/240: mais massa vermelha | Tamanhos grandes. Em 32 px os cortes quase somem |
| L3 corte largo | Corte 15/240 | O que melhor resiste a 32–56 px (favicon, avatar pequeno) |
| L4 pontas redondas | Pontas das peças com raio 2,5 | Tom mais afetivo; em 110 px quase não se nota |
| L5 cruz marcada | Cruz 22% maior e pátea mais aberta, como na referência | Destaca a cruz, mas encolhe os cantos de baixo |
| L6 dois tons | Cantos de cima em #7E0F17; cruz e cantos de baixo em #A3121C | Peças grandes; em 32 px os dois tons se misturam |
| L7 negativo | Prata #F3F2EE (há também `-com-fundo`, sobre #7E0F17) | Capas escuras |
| L8 grafite | Uma cor #1E1B1B | Documentos, carimbo, impressão em 1 cor |
| L9 filete dourado | L1 com contorno #B08D3B discreto | Só em tamanho grande (o filete some abaixo de ~200 px) |

Lockups (com L1): horizontal e vertical: "Pastoral do Dízimo" em Cormorant Garamond 600 (grafite) e "ARQUIDIOCESE DE FLORIANÓPOLIS" em Source Sans 3 600, caixa alta espaçada (cinza). Avatares circulares 1080 sobre prata e sobre creme #F2E8D5.

## Risco de originalidade
O "coração de quatro partes" também é usado por **outras dioceses** (símbolo de origem Curitiba, 2016, para as 4 dimensões; ver `docs/marca/identidade-visual.md` §1). Este desenho é outro (sem mãos, com cruz pátea central), mas a ideia não é exclusiva. Pode ser confundido com o símbolo de outras pastorais e não identifica a Arquidiocese por si só. Por isso o lockup com o nome deveria ser obrigatório fora do avatar. Isto precisa ser pesado contra o caminho B (roda e cruz, identidade-visual.md §5).
