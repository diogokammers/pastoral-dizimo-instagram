# ADR-001 — Pipeline em lote único, executado no plano Max via `claude -p`

Data: 2026-09-25. Status: aceito.

## Contexto
O sistema anterior (7 subagentes/dia em sessão interativa) chegou a ~84k tokens por chamada e não cabia
na janela do plano Pro. Precisamos de custo por post drasticamente menor, aprovação humana obrigatória e
mínimo trabalho manual. Pesquisa completa em `docs/pesquisa.md`; comparação em `docs/arquitetura.md`.

## Alternativas avaliadas
- **A — Lote único + templates, rota API** (≈ US$ 0,55/mês em Opus 5.5 [H]); exige abrir conta de API.
- **B — Cadeia enxuta de 3 subagentes em sessão Max** (≈ 80–100k tokens/semana [H]; sessão manual semanal).
- **C — Lote único + templates, executado por `claude -p` com o plano Max** (≈ 26k tokens/semana [H]; automático via GitHub Action).

## Evidência
- Preços oficiais e desconto de Batch: `docs/pesquisa/02-claude-code-e-api.md` (tabela).
- `CLAUDE_CODE_OAUTH_TOKEN` documentado em `anthropics/claude-code-action/docs/setup.md` como método de autenticação para Pro/Max.
- `claude -p --output-format json` devolve `usage` e `total_cost_usd` — confirmado localmente (`docs/pesquisa/05-medicoes-locais.md`).
- Overhead por subagente em sessão (prompt de sistema + ferramentas) explica o custo do sistema anterior — hipótese a confirmar no piloto medindo `usage.input_tokens` de uma chamada `claude -p`.

## Decisão
**Alt. C.** Diogo prefere consumir o plano Max já pago em vez de abrir conta de API. O pipeline é o da
Alt. A (LLM em 2 pontos, tudo o mais determinístico); só o cliente de geração muda: `gerar.py` executa
`claude -p` com esquema JSON e modelo configurável, registra tokens e tempo por execução.

## Consequências
- Segredo adicional: `CLAUDE_CODE_OAUTH_TOKEN` (gerado pelo Diogo com `claude setup-token`; validade a confirmar na Fase 3).
- `ANTHROPIC_API_KEY` não existe no projeto. Se o suporte a OAuth em CI mudar, o fallback é a Alt. A
  (troca de um módulo), com custo estimado < US$ 1/mês.
- Risco R5 (Termos de Uso do plano para automação institucional) permanece aberto e documentado.
- A medição do piloto usa o JSON do `claude -p` (input/output/cache) em vez de `usage` da API.
