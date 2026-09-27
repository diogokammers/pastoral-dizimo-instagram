// Vetor JS → Python do painel (ADR-011): roda a API do Worker de verdade (tratar) com o GitHub falso e o
// D1 falso (node:sqlite + migrations reais) na semana de exemplo — aprova 12 e 13, depois desfaz 12 — e
// grava { apos_aprovar, apos_desfazer } com os aprovacao.json que o Worker commitaria.
// tests/test_simulador_painel.py passa os dois pelo publicar.avaliar_semana. Uso: node scripts/vetor-painel.mjs saida.json
import { writeFileSync } from "node:fs";

import { tratar } from "../src/index.js";
import { D1Falso } from "../test/d1-falso.js";
import { ENV, GitHubFalso, VETORES } from "../test/github-falso.js";

const saida = process.argv[2];
if (!saida) {
  console.error("uso: node scripts/vetor-painel.mjs saida.json");
  process.exit(2);
}
const codigo = "codigo-de-teste-do-vetor-0123456789abcdef";
const env = { ...ENV, DB: new D1Falso(), CODIGO_PADRE: codigo };
const gh = new GitHubFalso();
const caminho = "content/semanas/2026-W41/aprovacao.json";

async function decidir(corpo) {
  const r = await tratar(new Request("https://w.exemplo.workers.dev/api/decisao", {
    method: "POST",
    headers: { Origin: "https://diogokammers.github.io", Authorization: `Bearer ${codigo}`, "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  }), env, { fetch: gh.fetch, agora: () => new Date("2026-10-02T13:00:00Z"), waitUntil: () => {} });
  if (r.status !== 200) {
    console.error(`falhou: HTTP ${r.status} ${await r.text()}`);
    process.exit(1);
  }
}

await decidir({ semana: "2026-W41", post: 12, acao: "aprovar", versao: VETORES.versao_post["12"] });
await decidir({ semana: "2026-W41", post: 13, acao: "aprovar", versao: VETORES.versao_post["13"] });
const aposAprovar = JSON.parse(gh.texto(caminho));
await decidir({ semana: "2026-W41", post: 12, acao: "desfazer" });
const aposDesfazer = JSON.parse(gh.texto(caminho));
writeFileSync(saida, JSON.stringify({ apos_aprovar: aposAprovar, apos_desfazer: aposDesfazer }, null, 2), "utf8");
console.log(saida);
