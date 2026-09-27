# CLAUDE.md — Pastoral do Dízimo (Instagram)

Sistema que gera, aprova, publica e mede posts do @pastoraldodizimo.arquifln.
Arquitetura: `docs/arquitetura.md` · decisões: `docs/decisoes/ADR-*.md` · validações: `docs/validacao/`.

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
- Aprovação (ADR-009): prévia semanal `python -m pastoral.preview --semana 2026-W41` · e-mail `python -m pastoral.notificar 2026-W41 --dry-run` (HTML fora do repo) · Worker: `cd worker && npm test` (node:test + node:sqlite, Node ≥ 22.13) · `semanal.yml` só com `SEMANAL_ATIVO = 1`
- Simulador do Instagram para o aprovador aprovar tudo (perfil + 3 fixados + reserva; grava site/aprovacao/ e copia estreia/destaques para site/midia/): `python -m pastoral.simulador` (com `PYTHONPATH=src`; API = `aprovacao.worker_url`)
- Painel de aprovação (ADR-011/012): respostas como rascunho no aparelho e envio com o código de envio (secret `CODIGO_APROVADOR` do Worker; o valor NUNCA entra no repositório nem na página), com limite de 5 erros/15 min por IP (tabela `falhas_acesso`; para liberar: `… d1 execute pastoral-aprovacoes --remote --command "DELETE FROM falhas_acesso"`). D1 `pastoral-aprovacoes` (eventos append-only; migrations em `worker/migrations/`), estado público em `GET /api/estado`, link curto sem código `https://aprovar.pastoral-dizimo-aprovacao.workers.dev/`, backup em `content/aprovacoes/eventos.jsonl`. Wrangler SEMPRE com o login da Pastoral: `env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID XDG_CONFIG_HOME="C:/Users/odnac/.config-pastoral-dizimo" npx wrangler …` dentro de `worker/` · deploy `… deploy` e `… deploy --env curto` · migrations `… d1 migrations apply pastoral-aprovacoes --remote` · E2E só no ambiente de teste (`--env teste`, ramo `teste-aprovacao`): `python scripts/e2e_painel.py` e `python scripts/e2e_pagina.py` · JS da página no navegador (inclui celular WebKit/Chromium): `tests/test_simulador_navegador.py` (Playwright; `python -m playwright install chromium webkit`)
- Mudou hash/assinatura? Regenere os vetores cruzados: `python -m pastoral.aprovacao --vetores tests/fixtures/vetores-python.json` e `node worker/scripts/vetor-worker.mjs` (o vetor do painel, `vetor-painel.mjs`, roda dentro do pytest)

## Estrutura
- `content/temas.yaml` — fila de temas da estratégia (sem Reels, que são manuais)
- `content/semanas/AAAA-Www/` — briefing, posts, aprovação e ledger da semana
- `src/pastoral/calendario.py` — calendário litúrgico calculado
- `src/pastoral/pauta.py` — escolha dos posts da semana (ciclo 70/20/10)
- `content/estreia/` — pacote de estreia (ADR-005/006/007): posts, bio, render/ · `templates/` — artes · `site/` — prévias

## Git
- Commits em português, terminando com a linha Co-Authored-By.
- Repositório público (R11 resolvido: histórico consolidado). Nunca versionar dado pessoal nem trecho longo de obra protegida.
