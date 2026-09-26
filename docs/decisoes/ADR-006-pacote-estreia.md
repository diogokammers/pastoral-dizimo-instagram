# ADR-006 — Pacote de estreia e fatias 3–4 (parciais)

Data: 2026-09-26. Status: proposto (aguarda aprovação do Diogo e, depois, do Padre).

## Contexto
O ADR-005 pede, antes de qualquer pauta semanal, um pacote de estreia (bio, 6 capas de destaques e os 3 posts
fixados) aprovado em dois níveis. Para produzi-lo foi preciso adiantar partes das fatias 3 (lint) e 4 (render).

## Decisões
1. **Lint determinístico** (`src/pastoral/lint.py`) + **JSON Schema** (`schemas/posts.schema.json`). Termos
   proibidos são barrados **mesmo em negação** ("não é taxa"): mais simples e mais seguro; o texto usa formulação
   positiva. Doc. CNBB 106 só com parágrafo verificado (n. 6, 9, 10, 12, 22 ou Cap. II) e nunca no mesmo bloco que
   "dimensões". Alt-text é **por slide** (a API aceita `alt_text` em cada imagem do carrossel, pesquisa 01).
2. **`gerar.py` é esqueleto**: `claude -p` + schema + lint + 1 regeneração, testado com LLM mockado (CLI sem login).
3. **Os 3 posts foram escritos à mão** (`content/estreia/posts.json`), não gerados. Citações do Doc. 106 são
   paráfrases com "cf."; a única citação bíblica literal é o lema 2Cor 9,7; Rm 15,26-27 e cân. 222 §1 só como
   referência. As quatro dimensões do post 3 aparecem como "síntese pastoral", sem Doc. 106.
4. **Render**: templates HTML/CSS com tokens do `config.yaml`, fontes OFL locais (google/fonts), Playwright/Chromium,
   JPEG q90 4:4:4 com perfil sRGB embutido (via Pillow). QA automático: overflow, contraste ≥ 4,5:1 em todo texto,
   área segura (72 px laterais; texto essencial acima dos 180 px inferiores — o rodapé com a assinatura fica na
   faixa, marcado como não essencial), dimensões e < 8 MB → `qa.json`.
5. **Sem símbolo** (`marca.simbolo: null`): assinatura tipográfica. Capas de destaques só com ícone de linha próprio
   (mãos com chama, livro, calendário, mapa, balão, cruz) dentro de um círculo com filete dourado; sem texto.
6. **Prévia autocontida** (`site/estreia/index.html`, imagens embutidas) com texto de apoio para o Padre.

## Resultado
21 slides (3 × 7) + 6 capas 1080×1920 em `content/estreia/render/`; QA sem reprovações; lint OK.

## Pendências (a confirmar)
- Redação literal de 2Cor 9,7 e referência de Rm 15,26-27 na Bíblia Sagrada — Tradução Oficial da CNBB.
- Paráfrases do Doc. 106 (n. 6, 9, 10, 12) contra o exemplar impresso.
- Escolha da bio (principal ou alternativas) e do nome (proposta acrescenta "de").
- Ícones das capas são rascunho de projeto (em especial "Dízimo").
- Pesquisa 04 §10.9: uso do handle @pastoraldodizimo.arquifln como perfil oficial sem confirmação escrita da Cúria.
