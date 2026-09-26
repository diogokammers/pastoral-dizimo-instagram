#!/usr/bin/env bash
# Gera LINK_HMAC_SECRET e APROVACAO_HMAC_SECRET (32 bytes aleatórios, hex) e grava cada um DIRETO
# no GitHub (gh secret set) e no Worker (wrangler secret put, via stdin), sem imprimir os valores (ADR-009).
#
# Pré-requisitos: `gh auth login` feito, `npx wrangler login` feito e o Worker já publicado
# (`npx wrangler deploy` dentro de worker/). Uso: bash scripts/gerar-segredos-hmac.sh [dono/repo]
#
# Atenção: rodar de novo TROCA os segredos. Links de e-mail já enviados e aprovações já gravadas
# (aprovacao.json) deixam de valer; será preciso reenviar o e-mail da semana.
set -euo pipefail

REPO="${1:-diogokammers/pastoral-dizimo-instagram}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

for cmd in gh npx; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Comando '$cmd' não encontrado no PATH." >&2; exit 1; }
done

novo_segredo() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    python3 -c 'import secrets; print(secrets.token_hex(32))'
  fi
}

cd "$RAIZ/worker"
for nome in LINK_HMAC_SECRET APROVACAO_HMAC_SECRET; do
  valor="$(novo_segredo)"
  printf '%s' "$valor" | gh secret set "$nome" --repo "$REPO" >/dev/null
  printf '%s' "$valor" | npx wrangler secret put "$nome" >/dev/null
  unset valor
  echo "$nome gravado no GitHub e no Worker (valor não exibido)."
done
