# ADR-007 — Fundos por tipo de post (creme × vermelho) e 5 destaques

Data: 2026-09-26. Status: aceito (decisões do Diogo); amostras aguardam o olhar dele.

## Contexto
No pacote de estreia (ADR-006) todo post tinha capa e CTA em vermelho profundo e conteúdo em prata. O Diogo
quer reservar o vermelho para o que merece destaque e dar aos posts comuns da semana um fundo mais leve.
Também decidiu enxugar os destaques do perfil.

## Decisões
1. **Destaque "Paróquias" removido.** Ficam 5: Dízimo, Formação, Agenda, Perguntas, Arquifln
   (`render.DESTAQUES`); `destaque-paroquias.jpg` apagado; prévia e `qa.json` refeitos. O ícone `mapa.svg`
   continua em `templates/icones/` sem uso.
2. **Tema de fundo codificado** (`render.tema_do_post`, `render.classe_fundo`):
   - post com `fixado: true` **ou** `importante: true` → tema **vermelho**: capa e CTA em vermelho profundo,
     conteúdo e citação em prata (como no ADR-006);
   - qualquer outro post → tema **creme**: capa, conteúdo, citação e CTA em fundo creme; títulos, eyebrow,
     assinatura (nome) e seta em vermelho; texto em grafite; usuário, instituição, numeração e fonte em cinza;
     filetes em dourado (só ornamento).
   - `fixado` e `importante` são booleanos opcionais no `schemas/posts.schema.json`. Os 3 posts da estreia
     ganharam `"fixado": true` (só a marca; nenhum texto mudou).
   - Nos templates, cada fundo (`.escuro`, `.claro`, `.creme` em `base.css`) define as cores do texto
     (`--c-titulo`, `--c-texto`, `--c-eyebrow`, `--c-nome`, `--c-apoio`, `--c-seta`); os templates só as usam.
3. **Token `creme: #F2E8D5`** no `config.yaml` (creme quente, entre o prata do escudo e o dourado). `prata`
   continua para os slides de conteúdo dos fixados/importantes.

## Contrastes medidos sobre o creme #F2E8D5 (WCAG 2.x, `render.contraste`)
| Cor | Uso no tema creme | Razão | Resultado |
|---|---|---|---|
| vermelho #A3121C | títulos, eyebrow, assinatura, seta, referência | **6,49:1** | AA |
| grafite #1E1B1B | texto corrido | **14,07:1** | AA/AAA |
| cinza #5F5A57 | usuário, instituição, numeração, fonte | **5,60:1** | AA |
| vermelho profundo #7E0F17 | (não usado como texto no creme) | 8,78:1 | AA |
| dourado #B08D3B | só filetes — nunca texto | 2,57:1 | reprova para texto (por isso só ornamento) |

Creme × prata: 1,08:1 — são fundos próximos; a diferença é de temperatura, não de contraste.
O QA automático do render (contraste ≥ 4,5:1 em todo texto) passou nos 7 slides em creme.

## Amostras para o Diogo (`content/estreia/amostras/`, `python -m pastoral.amostras`)
- `post-comum-creme-01..07.jpg` — o post 2 renderizado como post comum (cópia sem `fixado`); o post 2 real
  continua fixado e vermelho em `content/estreia/render/`.
- `comparativo.jpg` — capa fixada (vermelha) × capa comum (creme); conteúdo prata × conteúdo creme.
- `destaques.jpg` — as 5 capas em círculos de 200 px sobre branco, com o nome abaixo, como no perfil.

## Consequências
- A pauta semanal passa a gerar posts creme por padrão; `importante: true` é a exceção explícita a marcar.
- O ADR-006 (6 capas, fundos únicos) fica superado nesses dois pontos.

## Adendo (2026-09-27) — ícone do destaque "Dízimo"
Diogo aprovou todas as artes, exceto o ícone de "Dízimo" (mãos em concha). Substituído pelo **coração partido em 4**
da referência dele (rodada 6, `assets/marca/propostas/rodada6-referencia/UC-ref.svg`): coração preenchido em vermelho
com quatro cortes em torno de uma cruz, em `templates/icones/coracao-cheio.svg`. A versão em traço
(`coracao.svg`) foi testada e descartada por ficar confusa no tamanho do destaque. Ícones sem uso (`maos`, `mapa`) removidos.
