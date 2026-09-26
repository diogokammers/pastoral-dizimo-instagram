# Estudo de identidade visual e logotipo — proposta

Data: 2026-09-25 · Status: **decidido em 2026-09-26 — ver [ADR-002](../decisoes/ADR-002-identidade-visual.md)** (paleta e tipografia aprovadas; logotipo adiado).
Prancha visual (paleta, tipografia, 3 logotipos, mockups): publicada como artefato — link na conversa.

## 1. Insumos (o que a identidade precisa respeitar)
| Insumo | O que diz | Fonte |
|---|---|---|
| Estratégia, cap. 4 | Sobriedade institucional; serifada em títulos, sem-serifa em apoio; 2–3 cores; sugestão vinho/dourado/branco **subordinada à identidade oficial da Arquidiocese** | [estrategia-instagram.md](estrategia-instagram.md) |
| Brasão da Arquidiocese | "Esquartelado de **prata e vermelho** … uma **cruz** de esmaltes trocados e **cantonada por uma roda (de Santa Catarina), dividida em quatro partes**"; insígnias em dourado (mitra, cruz patriarcal, báculo). Autor: Ir. Paulo Lachenmayer OSB, 1977 | https://arquifln.org.br/brasao |
| Cores medidas no brasão/marca oficial | vermelho ≈ **#D40A0A**, prata/branco, dourado ≈ #F8E0A8 (claros) — medição por quantização dos PNGs oficiais | pesquisa desta sessão |
| Símbolo usado hoje no perfil | "Coração de quatro mãos" vermelho, comum a várias dioceses (origem Curitiba, 2016, para as **4 dimensões** religiosa, eclesial, caritativa, missionária — a síntese em 4 dimensões **não** aparece literalmente no Doc. CNBB 106; ver [06](../pesquisa/06-cnbb-doc-106.md)) | auditoria do perfil; dizimocnbbsul2.wixsite.com; diocesedesaojoaodelrei.com.br |
| Padroeira | Santa Catarina de Alexandria (a roda) | arquifln.org.br/brasao |
| Versículo-lema | "Deus ama quem dá com alegria" (2Cor 9,7) | estratégia, capa |

Conclusão dos insumos: a paleta **não deve ser vinho/roxo** (sugestão genérica do documento) e sim derivar do brasão: **vermelho + prata + dourado discreto**. O símbolo deve dialogar com as 4 dimensões (já reconhecidas pelo público) e com a cruz cantonada pela roda (identidade arquidiocesana).

## 2. Princípios
1. **Herdar, não inventar:** cada cor e forma tem origem no brasão ou na doutrina.
2. **Sóbrio e legível:** muito espaço, uma ideia por slide, contraste AA medido.
3. **Sem rosto:** identidade tipográfica e simbólica; nenhuma foto de pessoa no piloto (LGPD).
4. **Funciona pequeno:** logotipo legível no avatar de 110 px e em monocromia.
5. **Sem estética publicitária:** sem gradientes, sombras, ícones genéricos de "dinheiro".

## 3. Paleta (tokens) e contrastes medidos
| Token | Hex | Papel | Contraste medido |
|---|---|---|---|
| `--vermelho` | **#A3121C** | Cor primária: títulos, fundos de capa, logotipo em uso corrente | 7,05:1 sobre prata (AA texto normal) |
| `--vermelho-brasao` | #D40A0A | Só quando o logotipo aparece ao lado do brasão oficial | 4,87:1 sobre prata (AA só texto grande) |
| `--vermelho-profundo` | #7E0F17 | Fundos escuros de capa; prata sobre ele | 9,53:1 |
| `--prata` | **#F3F2EE** | Fundo claro padrão (o "prata" do escudo, não creme) | — |
| `--grafite` | #1E1B1B | Texto corrido | 15,3:1 sobre prata |
| `--cinza` | #5F5A57 | Texto de apoio, numeração | 6,07:1 sobre prata |
| `--dourado` | #B08D3B | **Só filetes e ornamentos**, nunca texto sobre prata | 2,79:1 (reprova para texto) |
| `--dourado-claro` | #D9B85C | Detalhes/eyebrow sobre vermelho profundo | 5,57:1 |

Regra codificável: texto sempre em `grafite`, `vermelho` ou `prata`; `dourado` proibido como cor de texto sobre fundo claro (o lint visual checa).

## 4. Tipografia (licença SIL OFL confirmada no repositório google/fonts)
- **Títulos:** Cormorant Garamond, peso 600 (SemiBold), maiúsculas/minúsculas, tracking −1%. Serifada de tradição, com itálico bonito para versículos.
- **Apoio e legendas:** Source Sans 3, pesos 400/600. Neutra, legível em 40 px no celular.
- **Alternativa** (se o Diogo preferir mais contraste): EB Garamond + Nunito Sans.
- Arquivos `.ttf` versionados em `assets/fonts/` (render offline, sem depender do Google Fonts no CI).

Escala para 1080×1350: título de capa 88–96 px · título de slide 64 px · texto 40–44 px (entrelinha 1,3) · apoio/numeração 28 px · assinatura 26 px. Margens de segurança 72 px; área de texto ≤ 936 px de largura.

## 5. Logotipo — três caminhos
| | A — Coração quadripartido | B — Roda e Cruz (**recomendado**) | C — Espiga |
|---|---|---|---|
| Ideia | Coração geométrico dividido em 4 por uma cruz em negativo: continuidade com o símbolo que o público já reconhece, redesenhado (sem mãos, sem figuras) | Roda de Santa Catarina em 4 segmentos ao redor de uma cruz grega: literalmente a carga do brasão ("cruz cantonada por roda dividida em quatro partes"); os 4 segmentos = 4 dimensões do dízimo; a roda = comunidade em torno da cruz | Espiga com 10 grãos e cruz no ápice: primícias, colheita, Eucaristia (Ml 3,10; Dt 26); a décima parte sem numerar percentual |
| Prós | Reconhecimento imediato; afetivo | Identidade **arquidiocesana** inequívoca; heráldico, sóbrio; funciona em 1 cor e em 110 px; ninguém mais usa | Bíblico, distinto, bonito em selo |
| Contras | Derivado de marca de outra diocese; coração é usado por muitas pastorais | Pode ler-se como "marca da Arquidiocese" se usado sem o nome | Menos ligado às 4 dimensões; espiga é comum em pastorais rurais |
| Lockup | Símbolo + "Pastoral do Dízimo" (Cormorant) / "Arquidiocese de Florianópolis" (Source Sans, caixa alta, espaçada) | idem | idem |

Recomendação: **B**, com o nome sempre presente no lockup horizontal; no avatar, só o símbolo em vermelho sobre prata. Versões: positiva (vermelho/prata), negativa (prata sobre vermelho profundo), monocromática (grafite), e "junto ao brasão" (usa #D40A0A).

## 6. Sistema de posts (o que os templates implementam)
| Template | Uso | Composição |
|---|---|---|
| `capa` | 1º slide de carrossel | Fundo vermelho profundo; eyebrow dourado-claro com pilar; título Cormorant 92 px em prata; filete dourado; símbolo + "@pastoraldodizimo.arquifln" no rodapé; seta "→" discreta |
| `conteudo` | Slides 2..n−1 | Fundo prata; numeração "2/6" cinza no topo; título vermelho 64 px; texto grafite 42 px, ≤ 25 palavras; filete dourado no rodapé com o símbolo pequeno |
| `citacao` | Imagem única (versículo/Catecismo) | Prata; aspas grandes em vermelho; itálico Cormorant 72 px; referência em Source Sans caixa alta; símbolo |
| `cta` | Último slide | Vermelho profundo; CTA da lista permitida; convite a salvar/compartilhar; lockup completo |
| `destaque` | Capas de destaques (1080×1920, círculo central 1080) | Prata com ícone de linha vermelho (livro, cruz, calendário, mapa, mãos) — conforme cap. 8 |

Área segura Instagram no 4:5: 72 px laterais; 180 px inferiores livres de texto essencial (legenda/ícones sobrepostos no app).

## 7. O que muda no perfil após aprovação
- Avatar: símbolo escolhido (arquivo 1080×1080 exportado do SVG).
- Capas dos 6 destaques (Dízimo, Formação, Agenda, Paróquias, Perguntas, Arquifln).
- 3 posts fixados: apresentação institucional, "O que é o dízimo?", "Para onde vai o dízimo?" (posts 1–3 da estratégia).

## 8. Decisões pedidas ao Diogo
1. Logotipo: A, B ou C (ou combinação/ajuste).
2. Paleta: aprova vermelho + prata + dourado (em vez de vinho)?
3. Tipografia: Cormorant Garamond + Source Sans 3 ou a alternativa?
4. Trocar já a foto de perfil pelo símbolo escolhido, ou só no lançamento dos 3 posts?
