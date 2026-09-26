// Vetor JS → Python (ADR-009): roda o Worker de verdade (tratar) contra o GitHub falso com a semana de
// exemplo e grava o aprovacao.json que ele commitaria. tests/test_aprovacao.py confere que o portão
// (publicar.py) aceita esse arquivo. Uso: node scripts/vetor-worker.mjs [saida.json]
import { writeFileSync } from "node:fs";
import { join } from "node:path";

import { tratar } from "../src/index.js";
import { ENV, FIXTURE, GitHubFalso, VETORES } from "../test/github-falso.js";

const saida = process.argv[2] ?? join(FIXTURE, "aprovacao-worker.json");
const gh = new GitHubFalso();
const link = VETORES.links.validos.find((l) => l.a === "aprovar_tudo");
const resposta = await tratar(
  new Request("https://pastoral-dizimo-aprovacao.exemplo.workers.dev/a", { method: "POST", body: new URLSearchParams(link) }),
  ENV,
  { fetch: gh.fetch, agora: () => new Date("2026-10-02T13:00:00Z") },
);
if (resposta.status !== 200 || gh.gravacoes.length !== 1) {
  console.error(`falhou: HTTP ${resposta.status}`);
  process.exit(1);
}
writeFileSync(saida, gh.gravacoes[0].texto, "utf8");
console.log(saida);
