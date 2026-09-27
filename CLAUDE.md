# CLAUDE.md — Pastoral do Dízimo (Instagram)

Sistema que gera, aprova, publica e mede posts do @pastoraldodizimo.arquifln.
Arquitetura: `docs/arquitetura.md` · decisões: `docs/decisoes/ADR-*.md`.

## Regras de conteúdo
- A única fonte de voz, termos, pilares e formato é `cartao-marca.md`. Não releia `docs/marca/`.
- Parâmetros (agenda, limites, CTAs, paleta, fontes, modelo): `config.yaml`.
- Nada é inventado: lacuna vira "a confirmar" e é perguntada ao Diogo.
- Nada é publicado sem aprovação humana explícita (imposta por código).

## Regras de código
- Python 3, `src/pastoral/`, testes em `tests/` (pytest). TDD: teste antes do código.
- Código simples, comentários em português.
- `encoding="utf-8"` explícito em toda leitura/escrita de arquivo (Windows).
- LLM só em `gerar.py` e `analise.py`; o resto é determinístico.
- Credenciais nunca passam pelo Claude: só o nome da variável e onde cadastrar.

## Comandos
- Instalar: `python -m pip install -r requirements.txt`
- Testes: `python -m pytest -q`
- Tokens do cartão: `python -m pastoral.medir_tokens cartao-marca.md` (com `PYTHONPATH=src`)
- Pauta da semana: `python -m pastoral.pauta 2026-W41` (com `PYTHONPATH=src`)
- Lint: `python -m pastoral.lint content/semanas/2026-W40/posts.json` (estreia publicada: acrescentar `--legado`) · Render + QA: `python -m pastoral.render content/estreia/posts.json --destaques` · Prévia: `python -m pastoral.preview` · Amostras creme: `python -m pastoral.amostras`
- Portão de publicação (dry-run padrão; real só com `PUBLICAR=1`): `python -m pastoral.publicar` · Diagnóstico do token: `python -m pastoral.meta --verificar` (ADR-008)
- Aprovação (ADR-009): prévia semanal `python -m pastoral.preview --semana 2026-W41` · e-mail `python -m pastoral.notificar 2026-W41 --dry-run` (HTML fora do repo) · Worker: `cd worker && npm test` (node:test; deploy só pelo Diogo) · `semanal.yml` só com `SEMANAL_ATIVO = 1`
- Mudou hash/assinatura? Regenere os vetores cruzados: `python -m pastoral.aprovacao --vetores tests/fixtures/vetores-python.json` e `node worker/scripts/vetor-worker.mjs`

## Estrutura
- `content/temas.yaml` — fila de temas da estratégia (sem Reels, que são manuais)
- `content/semanas/AAAA-Www/` — briefing, posts, aprovação e ledger da semana
- `src/pastoral/calendario.py` — calendário litúrgico calculado
- `src/pastoral/pauta.py` — escolha dos posts da semana (ciclo 70/20/10)
- `content/estreia/` — pacote de estreia (ADR-005/006/007): posts, bio, render/ · `templates/` — artes · `site/` — prévias

## Git
- Commits em português, terminando com a linha Co-Authored-By.
- Repositório público (R11 resolvido: histórico consolidado). Nunca versionar dado pessoal nem trecho longo de obra protegida.
