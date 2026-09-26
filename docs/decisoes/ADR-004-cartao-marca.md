# ADR-004 — Cartão de marca, config.yaml e tamanho medido do contexto fixo

Data: 2026-09-26. Status: aceito (Fase 3, fatias 1 e 2).

## Contexto
O sistema anterior relia arquivos grandes de marca a cada etapa (~84k tokens numa chamada). A arquitetura
(§1.2, §3) pede um `cartao-marca.md` compacto, com tamanho medido, como único contexto de marca da geração
(meta ≤ 3k tokens), e um `config.yaml` com os parâmetros operacionais.

## Alternativas avaliadas
- **Enviar `docs/marca/estrategia-instagram.md` inteiro** (≈ 24 KB) a cada geração — descartado: 4× maior e
  cheio de itens que não são regra (nomes de usuário alternativos, checklist de lançamento).
- **Cartão destilado à mão, só com regras verificáveis** — escolhido. Fontes: estratégia (cap. 1–3, 9, 11,
  15, 16), arquitetura §4, identidade visual §3–4, pesquisa 04 §8/§10 e 06 (Doc. CNBB 106).

## Medição de tokens
Script: `src/pastoral/medir_tokens.py`. Método preferido: duas chamadas `claude -p --output-format json`
(prompt mínimo "Responda apenas: ok" com e sem o cartão); a diferença do total de entrada
(`input + cache_creation + cache_read`) isola o cartão do overhead do Claude Code.

Execução em 2026-09-26 (`--modelo claude-opus-5-5`): o CLI desta máquina respondeu
`"Failed to authenticate: OAuth session expired and could not be refreshed"` (mesmo erro da medição 05).
O script caiu no fallback:

| Arquivo | Caracteres | Tokens | Método |
|---|---|---|---|
| `cartao-marca.md` | 5.388 | **1.347** | estimativa chars/4 **[H]** |

Leitura: mesmo com margem para o português (acentos costumam render menos de 4 caracteres/token; um fator
1,5× daria ≈ 2k), o cartão fica **abaixo da meta de 3k**. **Pendente:** Diogo rodar `claude login` no terminal
e repetir `PYTHONPATH=src python -m pastoral.medir_tokens` para trocar [H] por [M].

## Decisões
1. `cartao-marca.md` na raiz é o **único** contexto de marca da geração; o teste `tests/test_cartao_marca.py`
   impede regressão (seções obrigatórias, termos proibidos, regras de formato, teto de tamanho, e que as
   "quatro dimensões" nunca sejam atribuídas ao Doc. 106).
2. Do Doc. CNBB 106 o cartão só traz o que está como FATO VERIFICADO em `docs/pesquisa/06-cnbb-doc-106.md`
   (n. 6, 9, 10, 12, 22 e Cap. II; aprovação pelo Conselho Permanente).
3. `config.yaml`: terça e sexta 19h America/Sao_Paulo, 2 posts/semana, modelo `claude-opus-5-5` via CLI
   (ADR-001), `marca.simbolo: null` (ADR-002), paleta e fontes do estudo §3–4.
4. **Ordem do ciclo de 10** (decisão de projeto, ajustável no `config.yaml`):
   F F F V F F C V F F — as três primeiras posições casam com os 3 posts fixados (todos Formação).
5. **Mapeamento de pilares da estratégia:** posts marcados "Espiritualidade" e "Transparência" (eixos, não
   pilares, no cap. 9) contam como **Formação** — o cap. 9 lista "espiritualidade" no pilar de 70%;
   "transparência" é inferência **[a confirmar]**.
6. CTAs permitidos = lista da rubrica (arquitetura §4.1 T5) + "seguir o perfil" (CTA do post 1 da estratégia).

## Lacunas registradas (a confirmar com o Diogo)
- **Hashtags fixas:** a estratégia não define nenhuma → `hashtags_fixas: []`.
- **Post 3 ("Para onde vai o dízimo?")** cita as dimensões "religiosa, missionária, caritativa e social";
  a síntese pastoral usual traz "eclesial" em vez de "social", e nenhuma das duas listas é citação do Doc. 106.
- **Semana inicial** da pauta: `2026-W41` é valor provisório.
- Posts de convite (7, 19, 28) e os posts 9 (mapa) e 17 (depoimento) dependem de dado real (agenda, lista de
  paróquias, testemunho com consentimento LGPD); o briefing leva o campo `pendencia`.

## Fatia 2 — calendário e pauta
- `calendario.py`: Páscoa por `dateutil.easter` (method=3) e derivações; testado contra as 5 datas conferidas
  em `docs/pesquisa.md`. Cores por tempo e transferências para domingo (Epifania, Ascensão) seguem a regra
  litúrgica geral, **não conferida em fonte oficial da CNBB** (pesquisa 04 §5) — a confirmar na Agenda
  Litúrgica e Pastoral. CF só com tema verificado (2027); outros anos = "a confirmar".
- `pauta.py`: sem arquivo de estado; a série é recalculada a partir de `semana_inicial`, o que torna a saída
  determinística (bytes idênticos a cada execução, testado).
- Os resumos da estratégia contêm termos proibidos em contexto de negação (ex.: post 2, "não como taxa ou
  cobrança"); o lint da fatia 3 precisa checar o texto **gerado**, não o briefing.

## Consequências
- Contexto fixo da geração ≈ 1,3k tokens [H] + briefing, bem abaixo do orçamento de 8k de entrada (§3).
- Mudança de regra de marca = editar o cartão e rodar os testes; não há outra cópia das regras.
