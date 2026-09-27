// Painel de aprovação (ADR-011): API /api/*, link curto /p/, D1 (falso sobre node:sqlite com as migrations
// reais) e GitHub falso. Nenhuma chamada sai para a rede.
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { autorDoCodigo } from "../src/acesso.js";
import { CAMINHO_BACKUP } from "../src/backup.js";
import { Banco } from "../src/banco.js";
import { backupAgendado, tratar } from "../src/index.js";
import { assinarLink, assinaturaValida, utf8 } from "../src/nucleo.js";
import { D1Falso } from "./d1-falso.js";
import { ENV as ENV_BASE, GitHubFalso, VETORES } from "./github-falso.js";

const AGORA = new Date("2026-10-02T13:00:00Z");
const BASE = "https://pastoral-dizimo-aprovacao.exemplo.workers.dev";
const ORIGEM = "https://diogokammers.github.io";
const CODIGO_PADRE = "cOdIgO-dO-pAdRe_0123456789abcdefghij";
const CODIGO_DIOGO = "cOdIgO-dO-dIoGo_0123456789abcdefghij";
const SEMANA = "2026-W41";
const V12 = VETORES.versao_post["12"];
const V13 = VETORES.versao_post["13"];
const APROV = `content/semanas/${SEMANA}/aprovacao.json`;

let gh, db, env, pendentes;

beforeEach(() => {
  gh = new GitHubFalso();
  db = new D1Falso();
  env = {
    ...ENV_BASE, DB: db, CODIGO_PADRE, PAGINA_URL: "https://diogokammers.github.io/pastoral-dizimo-instagram/aprovacao/",
  };
  pendentes = [];
});

const rodar = (req, e = env) =>
  tratar(req, e, { fetch: gh.fetch, agora: () => AGORA, waitUntil: (p) => pendentes.push(p) });

function api(caminho, { metodo = "GET", corpo, codigo = CODIGO_PADRE, origem = ORIGEM, ip = "203.0.113.7" } = {}) {
  const headers = { "CF-Connecting-IP": ip };
  if (origem) headers.Origin = origem;
  if (codigo) headers.Authorization = `Bearer ${codigo}`;
  if (corpo !== undefined) headers["Content-Type"] = "application/json";
  return new Request(`${BASE}${caminho}`, {
    method: metodo, headers, body: corpo === undefined ? undefined : typeof corpo === "string" ? corpo : JSON.stringify(corpo),
  });
}

const decidir = (corpo, opcoes = {}) => rodar(api("/api/decisao", { metodo: "POST", corpo, ...opcoes }));
const aprovar = (post = 12, versao = post === 12 ? V12 : V13, opcoes) =>
  decidir({ semana: SEMANA, post, acao: "aprovar", versao }, opcoes);
const aprovacao = () => JSON.parse(gh.texto(APROV));
const gravacoesEm = (caminho) => gh.gravacoes.filter((g) => g.caminho === caminho);
const commitsDeDecisao = () => gh.gravacoes.filter((g) => g.caminho !== CAMINHO_BACKUP).length;

// ---------- acesso ----------

test("código de acesso: formato, comparação e autor; segundo código (Diogo) só quando cadastrado", async () => {
  assert.equal(await autorDoCodigo(env, CODIGO_PADRE), "Padre");
  assert.equal(await autorDoCodigo(env, CODIGO_DIOGO), null, "sem CODIGO_DIOGO cadastrado");
  assert.equal(await autorDoCodigo({ ...env, CODIGO_DIOGO }, CODIGO_DIOGO), "Diogo");
  assert.equal(await autorDoCodigo({ ...env, CODIGO_PADRE: CODIGO_PADRE + "\n" }, CODIGO_PADRE), "Padre", "quebra de linha no secret");
  assert.equal(await autorDoCodigo(env, CODIGO_PADRE.slice(0, -1) + "X"), null);
  assert.equal(await autorDoCodigo(env, "curto"), null);
  assert.equal(await autorDoCodigo(env, CODIGO_PADRE + "!"), null);
  assert.equal(await autorDoCodigo(env, null), null);
  assert.equal(await autorDoCodigo({ ...env, CODIGO_PADRE: "" }, ""), null);
});

test("GET /api/estado exige código válido (401) e devolve o autor", async () => {
  let r = await rodar(api("/api/estado", { codigo: null }));
  assert.equal(r.status, 401);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  r = await rodar(api("/api/estado", { codigo: "x".repeat(40) }));
  assert.equal(r.status, 401);
  r = await rodar(api("/api/estado"));
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(await r.json(), { autor: "Padre", posts: {} });
  assert.equal(gh.chamadas.length, 0);
});

test("CORS: só o origin do Pages; preflight responde; outro origin (ou nenhum) é bloqueado sem gravar", async () => {
  let r = await rodar(api("/api/decisao", { metodo: "OPTIONS", codigo: null }));
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.match(r.headers.get("Access-Control-Allow-Headers"), /Authorization/);
  for (const origem of ["https://evil.example", "https://diogokammers.github.io.evil.example", "null", null]) {
    r = await aprovar(12, V12, { origem });
    assert.equal(r.status, 403, String(origem));
    assert.equal(r.headers.get("Access-Control-Allow-Origin"), null);
  }
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("código errado não grava nada (401)", async () => {
  const r = await aprovar(12, V12, { codigo: "Y".repeat(43) });
  assert.equal(r.status, 401);
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("link curto /p/<código> redireciona para a página com o código só no fragmento", async () => {
  const r = await rodar(new Request(`${BASE}/p/${CODIGO_PADRE}`));
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), `${env.PAGINA_URL}#c=${CODIGO_PADRE}`);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  assert.equal(r.headers.get("Referrer-Policy"), "no-referrer");
  assert.equal((await rodar(new Request(`${BASE}/p/curto`))).status, 404);
  assert.equal((await rodar(new Request(`${BASE}/p/${CODIGO_PADRE}`), { ...env, PAGINA_URL: "" })).status, 404);
  assert.equal(gh.chamadas.length, 0);
});

// ---------- decisões ----------

test("aprovar: aprovacao.json assinado (igual ao link do e-mail), evento no D1 e backup no repositório", async () => {
  const r = await aprovar(12);
  const corpo = await r.json();
  assert.equal(r.status, 200, JSON.stringify(corpo));
  assert.equal(corpo.ok, true);
  assert.equal(corpo.idempotente, false);
  assert.equal(corpo.versao_conteudo, V12);
  assert.equal(corpo.estado.acao, "aprovar");
  assert.equal(corpo.estado.autor, "Padre");

  const dados = aprovacao();
  assert.equal(await assinaturaValida(dados, env.APROVACAO_HMAC_SECRET), true);
  assert.equal(dados.aprovado_por, "Padre");
  assert.deepEqual(dados.posts, [VETORES.semana.itens.find((i) => i.numero === 12)]);
  const [g] = gravacoesEm(APROV);
  assert.equal(g.ramo, "master");
  assert.equal(corpo.commit, g.commit);

  const [linha] = db.linhas();
  assert.deepEqual({ ...linha, ip_hash: typeof linha.ip_hash }, {
    id: 1, post: 12, semana: SEMANA, acao: "aprovar", comentario: "", versao_conteudo: V12, autor: "Padre",
    criado_em: "2026-10-02T13:00:00+00:00", origem: "painel", commit_sha: g.commit, ip_hash: "string",
  });
  assert.match(linha.ip_hash, /^[0-9a-f]{16}$/);
  assert.ok(!linha.ip_hash.includes("203"));

  await Promise.all(pendentes);
  const backup = gh.texto(CAMINHO_BACKUP).trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(backup.length, 1);
  assert.equal(backup[0].id, 1);
  assert.equal(backup[0].versao_conteudo, V12);
  assert.ok(!("ip_hash" in backup[0]), "backup público sem ip_hash");

  const estado = await (await rodar(api("/api/estado"))).json();
  assert.deepEqual(Object.keys(estado.posts), ["12"]);
  assert.equal(estado.posts["12"].acao, "aprovar");
  assert.ok(!("ip_hash" in estado.posts["12"]));
});

test("duas aprovações iguais: idempotente (nenhum commit nem evento novo)", async () => {
  await aprovar(12);
  await Promise.all(pendentes);
  const commits = gh.gravacoes.length;
  const r = await aprovar(12);
  const corpo = await r.json();
  await Promise.all(pendentes);
  assert.equal(r.status, 200);
  assert.equal(corpo.idempotente, true);
  assert.equal(corpo.evento_id, null);
  assert.equal(gh.gravacoes.length, commits, "nem decisão nem backup");
  assert.equal(db.linhas().length, 1);
});

test("aprovar posts separados acumula no mesmo aprovacao.json", async () => {
  await aprovar(12);
  await aprovar(13);
  assert.deepEqual(aprovacao().posts.map((p) => p.numero), [12, 13]);
  assert.equal(await assinaturaValida(aprovacao(), env.APROVACAO_HMAC_SECRET), true);
});

test("versão enviada diferente da atual (página velha ou conteúdo mudou): 409 sem gravar", async () => {
  let r = await aprovar(12, "0".repeat(32));
  assert.equal(r.status, 409);
  assert.equal((await r.json()).erro, "conteudo_mudou");
  gh.arquivos.get(`site/midia/${SEMANA}/post-12-01.jpg`).bytes = utf8("arte trocada");
  r = await aprovar(12, V12);
  assert.equal(r.status, 409);
  assert.equal(gh.gravacoes.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("conteúdo muda depois da aprovação: o estado guarda a versão antiga (a página volta o post a pendente)", async () => {
  await aprovar(12);
  const posts = JSON.parse(gh.texto(`content/semanas/${SEMANA}/posts.json`));
  posts.posts.find((p) => p.numero === 12).legenda += " (texto revisado)";
  gh.arquivos.get(`content/semanas/${SEMANA}/posts.json`).bytes = utf8(JSON.stringify(posts));
  const estado = await (await rodar(api("/api/estado"))).json();
  assert.equal(estado.posts["12"].versao_conteudo, V12);
  const r = await aprovar(12, V12);
  assert.equal(r.status, 409, "aprovar de novo exige a versão nova");
  const nova = (await decidir({ semana: SEMANA, post: 12, acao: "desfazer" }).then((x) => x.json())).versao_conteudo;
  assert.notEqual(nova, V12);
});

test("desfazer tira o post do aprovacao.json assinado; de novo é idempotente", async () => {
  await aprovar(12);
  await aprovar(13);
  let r = await decidir({ semana: SEMANA, post: 12, acao: "desfazer" });
  let corpo = await r.json();
  assert.equal(r.status, 200, JSON.stringify(corpo));
  assert.equal(corpo.estado.acao, "desfazer");
  const dados = aprovacao();
  assert.deepEqual(dados.posts.map((p) => p.numero), [13]);
  assert.equal(await assinaturaValida(dados, env.APROVACAO_HMAC_SECRET), true);
  const commits = commitsDeDecisao();
  r = await decidir({ semana: SEMANA, post: 12, acao: "desfazer" });
  corpo = await r.json();
  assert.equal(corpo.idempotente, true);
  assert.equal(commitsDeDecisao(), commits);
  assert.deepEqual(db.linhas().map((l) => `${l.post}:${l.acao}`), ["12:aprovar", "13:aprovar", "12:desfazer"]);
  r = await decidir({ semana: SEMANA, post: 13, acao: "desfazer" });
  assert.deepEqual(aprovacao().posts, []);
  assert.equal(await assinaturaValida(aprovacao(), env.APROVACAO_HMAC_SECRET), true);
});

test("desfazer post nunca decidido: nada a fazer", async () => {
  const corpo = await (await decidir({ semana: SEMANA, post: 13, acao: "desfazer" })).json();
  assert.equal(corpo.idempotente, true);
  assert.equal(corpo.evento_id, null);
  assert.equal(gh.gravacoes.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("pedir ajuste: ajuste-<n>.json + repository_dispatch + evento; tira da aprovação; repetido é idempotente", async () => {
  await aprovar(13);
  const r = await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "  Trocar a foto da capa.  " });
  const corpo = await r.json();
  assert.equal(r.status, 200, JSON.stringify(corpo));
  assert.equal(corpo.estado.acao, "ajustar");
  assert.equal(corpo.estado.comentario, "Trocar a foto da capa.");
  assert.deepEqual(aprovacao().posts, [], "post com ajuste pedido não fica aprovado");
  const ajuste = JSON.parse(gh.texto(`content/semanas/${SEMANA}/ajuste-13.json`));
  assert.equal(ajuste.texto, "Trocar a foto da capa.");
  assert.match(ajuste.nonce, /^[0-9a-f]{32}$/);
  assert.deepEqual(gh.disparos, [{ event_type: "ajustar_post", client_payload: { semana: SEMANA, post: 13 } }]);
  assert.equal(corpo.commit, gravacoesEm(`content/semanas/${SEMANA}/ajuste-13.json`)[0].commit);

  const commits = commitsDeDecisao();
  const r2 = await (await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "Trocar a foto da capa." })).json();
  assert.equal(r2.idempotente, true);
  assert.equal(commitsDeDecisao(), commits);
  assert.equal(gh.disparos.length, 1);

  await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "Na verdade, trocar o título." });
  assert.equal(gh.disparos.length, 2);
  assert.equal(JSON.parse(gh.texto(`content/semanas/${SEMANA}/ajuste-13.json`)).texto, "Na verdade, trocar o título.");
  assert.deepEqual(db.linhas().map((l) => l.acao), ["aprovar", "ajustar", "ajustar"]);
});

test("evento do dispatch configurável (Worker de teste não aciona nada real)", async () => {
  await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "x" }, {});
  await rodar(api("/api/decisao", { metodo: "POST", corpo: { semana: SEMANA, post: 12, acao: "ajustar", comentario: "y" } }),
    { ...env, EVENTO_AJUSTE: "ajustar_post_teste" });
  assert.deepEqual(gh.disparos.map((d) => d.event_type), ["ajustar_post", "ajustar_post_teste"]);
});

test("pedidos inválidos: 400/413 sem gravar", async () => {
  const casos = [
    "não é json",
    [],
    { semana: "2026-41", post: 12, acao: "aprovar", versao: V12 },
    { semana: SEMANA, post: "12", acao: "aprovar", versao: V12 },
    { semana: SEMANA, post: 0, acao: "aprovar", versao: V12 },
    { semana: SEMANA, post: 12, acao: "publicar", versao: V12 },
    { semana: SEMANA, post: 12, acao: "aprovar" },
    { semana: SEMANA, post: 12, acao: "ajustar", comentario: "   " },
    { semana: SEMANA, post: 12, acao: "ajustar", comentario: "x".repeat(2001) },
    { semana: SEMANA, post: 12, acao: "ajustar", comentario: 5 },
  ];
  for (const corpo of casos) {
    const r = await decidir(corpo);
    assert.equal(r.status, 400, JSON.stringify(corpo));
  }
  assert.equal((await decidir("x".repeat(20000))).status, 413);
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("post fora da semana: 400 sem gravar", async () => {
  const r = await aprovar(99, V12);
  assert.equal(r.status, 400);
  assert.equal((await r.json()).erro, "post_inexistente");
  assert.equal(gh.gravacoes.length, 0);
});

test("sem banco ou sem segredo: 500 sem tocar no GitHub", async () => {
  let r = await rodar(api("/api/estado"), { ...env, DB: undefined });
  assert.equal(r.status, 500);
  r = await rodar(api("/api/estado"), { ...env, APROVACAO_HMAC_SECRET: "" });
  assert.equal(r.status, 500);
  assert.equal(gh.chamadas.length, 0);
});

test("D1 fora do ar antes de decidir: nada é gravado", async () => {
  db.falhar = true;
  const r = await aprovar(12);
  assert.equal(r.status, 500);
  assert.match((await r.json()).mensagem, /Nada foi decidido/);
  assert.equal(gh.gravacoes.length, 0);
});

test("D1 falha na gravação depois do commit: 500 avisando; tocar de novo registra sem novo commit", async () => {
  db.falhar = "insert";
  let r = await aprovar(12);
  assert.equal(r.status, 500);
  assert.match((await r.json()).mensagem, /gravada no GitHub, mas não foi registrada no banco/);
  assert.equal(gravacoesEm(APROV).length, 1);
  db.falhar = false;
  r = await aprovar(12);
  const corpo = await r.json();
  assert.equal(r.status, 200);
  assert.equal(corpo.evento_id, 1);
  assert.equal(gravacoesEm(APROV).length, 1, "GitHub já estava certo: nenhum commit novo");
});

test("erro do GitHub vira 502 sem vazar o PAT e sem evento", async () => {
  gh.erroEm = { metodo: "GET", status: 500, corpo: `falhou com ${env.GH_PAT_WORKER}` };
  const r = await aprovar(12);
  assert.equal(r.status, 502);
  assert.ok(!(await r.text()).includes(env.GH_PAT_WORKER));
  assert.equal(db.linhas().length, 0);
});

// ---------- banco ----------

test("D1: eventos são append-only (UPDATE e DELETE recusados) e o estado é o último evento", async () => {
  const banco = new Banco(db);
  const base = { semana: SEMANA, comentario: "", versao_conteudo: V12, autor: "Padre", criado_em: "t" };
  await banco.registrar({ ...base, post: 12, acao: "aprovar" });
  await banco.registrar({ ...base, post: 13, acao: "aprovar", versao_conteudo: V13 });
  await banco.registrar({ ...base, post: 12, acao: "desfazer" });
  assert.throws(() => db.db.exec("UPDATE eventos SET autor = 'x'"), /append-only/);
  assert.throws(() => db.db.exec("DELETE FROM eventos"), /append-only/);
  assert.deepEqual((await banco.estado()).map((e) => `${e.post}:${e.acao}`), ["12:desfazer", "13:aprovar"]);
  assert.equal((await banco.ultimo(12)).acao, "desfazer");
  assert.equal(await banco.ultimo(99), null);
  assert.equal((await banco.todos()).length, 3);
  await assert.rejects(banco.registrar({ ...base, post: 12, acao: "publicar" }), /CHECK/);
  await assert.rejects(banco.registrar({ ...base, post: 12, acao: "aprovar", versao_conteudo: "curta" }), /CHECK/);
});

test("backup agendado (cron) exporta o D1 e não commita se nada mudou", async () => {
  await aprovar(12);
  await Promise.all(pendentes);
  const antes = gravacoesEm(CAMINHO_BACKUP).length;
  const r = await backupAgendado(env, { fetch: gh.fetch });
  assert.equal(r.mudou, false);
  assert.equal(gravacoesEm(CAMINHO_BACKUP).length, antes);
  gh.arquivos.delete(CAMINHO_BACKUP);
  const r2 = await backupAgendado(env, { fetch: gh.fetch });
  assert.equal(r2.mudou, true);
  assert.equal(r2.eventos, 1);
});

// ---------- link do e-mail também registra no D1 ----------

async function link(acao, post, nonce = "0123456789abcdef") {
  const p = { s: SEMANA, a: acao, p: post == null ? "" : String(post), e: "1791000000", n: nonce, v: VETORES.semana.versao };
  p.h = await assinarLink(env.LINK_HMAC_SECRET, p);
  return p;
}

test("aprovação e ajuste pelo link do e-mail viram eventos (origem email) quando há banco", async () => {
  let r = await rodar(new Request(`${BASE}/a`, { method: "POST", body: new URLSearchParams(await link("aprovar_tudo", null)) }));
  assert.equal(r.status, 200);
  assert.deepEqual(db.linhas().map((l) => [l.post, l.acao, l.origem, l.autor, l.versao_conteudo]),
    [[12, "aprovar", "email", "Diogo", V12], [13, "aprovar", "email", "Diogo", V13]]);
  const body = new URLSearchParams({ ...(await link("ajustar_post", 13, "fedcba9876543210")), texto: "Outra foto." });
  r = await rodar(new Request(`${BASE}/a`, { method: "POST", body }));
  assert.equal(r.status, 200);
  assert.deepEqual(aprovacao().posts.map((p) => p.numero), [12], "ajuste pelo e-mail também tira da aprovação");
  const ultimo = db.linhas().at(-1);
  assert.deepEqual([ultimo.post, ultimo.acao, ultimo.comentario, ultimo.origem], [13, "ajustar", "Outra foto.", "email"]);
});

test("Worker curto (aprovar): só redireciona /p/<código>; o resto é 404", async () => {
  const { default: curto } = await import("../src/curto.js");
  const e = { PAGINA_URL: env.PAGINA_URL };
  let r = await curto.fetch(new Request(`https://aprovar.exemplo.workers.dev/p/${CODIGO_PADRE}`), e);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), `${env.PAGINA_URL}#c=${CODIGO_PADRE}`);
  for (const caminho of ["/", "/a", "/api/estado", "/p/", "/p/abc"]) {
    r = await curto.fetch(new Request(`https://aprovar.exemplo.workers.dev${caminho}`), e);
    assert.equal(r.status, 404, caminho);
  }
  r = await curto.fetch(new Request(`https://aprovar.exemplo.workers.dev/p/${CODIGO_PADRE}`, { method: "POST" }), e);
  assert.equal(r.status, 404);
});
