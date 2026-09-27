// Painel de aprovação (ADR-011/012): API /api/*, envio em lote com código e limite de tentativas, link curto
// sem código, D1 (falso sobre node:sqlite com as migrations reais) e GitHub falso. Nada sai para a rede.
// Os códigos daqui são inventados para o teste; o código real existe só como secret do Worker.
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
const CODIGO = "Abcd";                 // curto de propósito: o código real também é curto
const SEMANA = "2026-W41";
const V12 = VETORES.versao_post["12"];
const V13 = VETORES.versao_post["13"];
const APROV = `content/semanas/${SEMANA}/aprovacao.json`;

let gh, db, env, pendentes;

beforeEach(() => {
  gh = new GitHubFalso();
  db = new D1Falso();
  env = { ...ENV_BASE, DB: db, CODIGO_APROVADOR: CODIGO, PAGINA_URL: "https://diogokammers.github.io/pastoral-dizimo-instagram/aprovacao/" };
  pendentes = [];
});

const rodar = (req, e = env, agora = AGORA) =>
  tratar(req, e, { fetch: gh.fetch, agora: () => agora, waitUntil: (p) => pendentes.push(p) });

function api(caminho, { metodo = "GET", corpo, codigo = CODIGO, origem = ORIGEM, ip = "203.0.113.7" } = {}) {
  const headers = {};
  if (ip) headers["CF-Connecting-IP"] = ip;
  if (origem) headers.Origin = origem;
  if (codigo) headers.Authorization = `Bearer ${codigo}`;
  if (corpo !== undefined) headers["Content-Type"] = "application/json";
  return new Request(`${BASE}${caminho}`, {
    method: metodo, headers, body: corpo === undefined ? undefined : typeof corpo === "string" ? corpo : JSON.stringify(corpo),
  });
}

const enviar = (decisoes, { agora, e, ...opcoes } = {}) =>
  rodar(api("/api/decisoes", { metodo: "POST", corpo: Array.isArray(decisoes) ? { decisoes } : decisoes, ...opcoes }), e, agora);

// Envia um lote de UM post e devolve { status, r: resultado do post (ou o corpo inteiro, se não houver) }.
async function decidir(corpo, opcoes) {
  const resp = await enviar([corpo], opcoes);
  const j = await resp.json();
  return { status: resp.status, r: j.resultados ? j.resultados[0] : j, lote: j };
}
const aprovar = (post = 12, versao = post === 12 ? V12 : V13, opcoes) =>
  decidir({ semana: SEMANA, post, acao: "aprovar", versao }, opcoes);
const aprovacao = () => JSON.parse(gh.texto(APROV));
const gravacoesEm = (caminho) => gh.gravacoes.filter((g) => g.caminho === caminho);
const commitsDeDecisao = () => gh.gravacoes.filter((g) => g.caminho !== CAMINHO_BACKUP).length;
const falhas = () => db.db.prepare("SELECT COUNT(*) AS n FROM falhas_acesso").get().n;

// ---------- acesso ----------

test("código: curto, sensível a maiúsculas, comparado com o secret CODIGO_APROVADOR (autor Aprovador)", async () => {
  assert.equal(await autorDoCodigo(env, CODIGO), "Aprovador");
  assert.equal(await autorDoCodigo(env, "abcd"), null, "minúsculas não valem");
  assert.equal(await autorDoCodigo(env, "ABCD"), null);
  assert.equal(await autorDoCodigo(env, "Abc"), null);
  assert.equal(await autorDoCodigo(env, "Abcde"), null);
  assert.equal(await autorDoCodigo(env, " Abcd"), null);
  assert.equal(await autorDoCodigo({ ...env, CODIGO_APROVADOR: CODIGO + "\n" }, CODIGO), "Aprovador", "quebra de linha no secret");
  assert.equal(await autorDoCodigo(env, ""), null);
  assert.equal(await autorDoCodigo(env, null), null);
  assert.equal(await autorDoCodigo({ ...env, CODIGO_APROVADOR: "" }, ""), null);
  assert.equal(await autorDoCodigo({ ...env, CODIGO_APROVADOR: undefined }, CODIGO), null);
});

test("GET /api/estado é público (sem código) e não expõe ip_hash", async () => {
  await aprovar(12);
  const r = await rodar(api("/api/estado", { codigo: null }));
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  const texto = await r.text();
  assert.ok(!texto.includes("ip_hash"));
  const j = JSON.parse(texto);
  assert.deepEqual(Object.keys(j), ["posts"]);
  assert.equal(j.posts["12"].acao, "aprovar");
  assert.equal(j.posts["12"].autor, "Aprovador");
});

test("CORS: só o origin do Pages; preflight responde; outro origin (ou nenhum) é bloqueado sem gravar", async () => {
  let r = await rodar(api("/api/decisoes", { metodo: "OPTIONS", codigo: null }));
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.match(r.headers.get("Access-Control-Allow-Headers"), /Authorization/);
  for (const origem of ["https://evil.example", "https://diogokammers.github.io.evil.example", "null", null]) {
    const x = await aprovar(12, V12, { origem });
    assert.equal(x.status, 403, String(origem));
    r = await rodar(api("/api/estado", { origem, codigo: null }));
    assert.equal(r.status, 403);
  }
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
  assert.equal(falhas(), 0, "origin errado nem conta tentativa");
});

test("código errado ou ausente: 401 com tentativas restantes, nada gravado", async () => {
  let x = await aprovar(12, V12, { codigo: "abcd" });
  assert.equal(x.status, 401);
  assert.equal(x.r.erro, "codigo_invalido");
  assert.equal(x.r.tentativas_restantes, 4);
  assert.match(x.r.mensagem, /Nada foi enviado/);
  x = await aprovar(12, V12, { codigo: null });
  assert.equal(x.status, 401);
  assert.equal(x.r.tentativas_restantes, 3);
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("5 códigos errados bloqueiam o IP por 15 min (até o código certo); outro IP segue livre; depois libera", async () => {
  for (let i = 1; i <= 4; i++) assert.equal((await aprovar(12, V12, { codigo: `Errado${i}` })).status, 401);
  let x = await aprovar(12, V12, { codigo: "Errado5" });
  assert.equal(x.status, 429);
  assert.equal(x.r.erro, "bloqueado");
  assert.equal(x.r.bloqueado_ate, "2026-10-02T13:15:00.000Z");
  assert.match(x.r.mensagem, /bloqueado até as 10:15/);
  x = await aprovar(12, V12);
  assert.equal(x.status, 429, "bloqueado mesmo com o código certo");
  assert.match(x.r.mensagem, /depois das 10:15/);
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);

  x = await aprovar(12, V12, { ip: "198.51.100.9" });
  assert.equal(x.status, 200, "outro IP não é afetado");

  x = await aprovar(13, V13, { agora: new Date("2026-10-02T13:14:59Z") });
  assert.equal(x.status, 429);
  x = await aprovar(13, V13, { agora: new Date("2026-10-02T13:15:01Z") });
  assert.equal(x.status, 200, "passados 15 minutos, libera");
  assert.equal(falhas(), 0, "acertar o código apaga as falhas daquele IP");
});

test("falhas antigas não contam e são apagadas; o IP nunca é gravado em claro", async () => {
  await aprovar(12, V12, { codigo: "x1", agora: new Date("2026-09-30T10:00:00Z") });
  await aprovar(12, V12, { codigo: "x2", agora: new Date("2026-10-02T12:00:00Z") });
  const linhas = db.db.prepare("SELECT * FROM falhas_acesso").all();
  assert.equal(linhas.length, 1, "a de mais de 1 dia foi apagada");
  assert.match(linhas[0].ip_hash, /^[0-9a-f]{16}$/);
  assert.ok(!JSON.stringify(linhas).includes("203.0.113.7"));
  const x = await aprovar(12, V12, { codigo: "x3" });
  assert.equal(x.r.tentativas_restantes, 4, "a de 1 hora atrás está fora da janela de 15 min");
});

test("link curto: /p/<código> desativado; Worker 'aprovar' redireciona a raiz para a página", async () => {
  assert.equal((await rodar(new Request(`${BASE}/p/qualquercoisa0123456789abcdefghij`))).status, 404);
  const { default: curto } = await import("../src/curto.js");
  const e = { PAGINA_URL: env.PAGINA_URL };
  let r = await curto.fetch(new Request("https://aprovar.exemplo.workers.dev/"), e);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), env.PAGINA_URL);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  for (const caminho of ["/p/abcdefghijabcdefghijabcdefghijab", "/a", "/api/estado", "/x"]) {
    r = await curto.fetch(new Request(`https://aprovar.exemplo.workers.dev${caminho}`), e);
    assert.equal(r.status, 404, caminho);
  }
  r = await curto.fetch(new Request("https://aprovar.exemplo.workers.dev/", { method: "POST" }), e);
  assert.equal(r.status, 404);
  r = await curto.fetch(new Request("https://aprovar.exemplo.workers.dev/"), { PAGINA_URL: "" });
  assert.equal(r.status, 404);
});

// ---------- decisões ----------

test("aprovar: aprovacao.json assinado (igual ao link do e-mail), evento no D1 e backup no repositório", async () => {
  const { status, r, lote } = await aprovar(12);
  assert.equal(status, 200, JSON.stringify(lote));
  assert.equal(lote.ok, true);
  assert.equal(lote.autor, "Aprovador");
  assert.equal(r.ok, true);
  assert.equal(r.idempotente, false);
  assert.equal(r.versao_conteudo, V12);
  assert.equal(r.estado.acao, "aprovar");
  assert.equal(r.estado.autor, "Aprovador");

  const dados = aprovacao();
  assert.equal(await assinaturaValida(dados, env.APROVACAO_HMAC_SECRET), true);
  assert.equal(dados.aprovado_por, "Aprovador");
  assert.deepEqual(dados.posts, [VETORES.semana.itens.find((i) => i.numero === 12)]);
  const [g] = gravacoesEm(APROV);
  assert.equal(g.ramo, "master");
  assert.equal(r.commit, g.commit);

  const [linha] = db.linhas();
  assert.deepEqual({ ...linha, ip_hash: typeof linha.ip_hash }, {
    id: 1, post: 12, semana: SEMANA, acao: "aprovar", comentario: "", versao_conteudo: V12, autor: "Aprovador",
    criado_em: "2026-10-02T13:00:00+00:00", origem: "painel", commit_sha: g.commit, ip_hash: "string",
  });
  assert.match(linha.ip_hash, /^[0-9a-f]{16}$/);

  await Promise.all(pendentes);
  const backup = gh.texto(CAMINHO_BACKUP).trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(backup.length, 1);
  assert.equal(backup[0].versao_conteudo, V12);
  assert.ok(!("ip_hash" in backup[0]), "backup público sem ip_hash");
});

test("duas aprovações iguais: idempotente (nenhum commit nem evento)", async () => {
  await aprovar(12);
  await Promise.all(pendentes);
  const commits = gh.gravacoes.length;
  const { status, r } = await aprovar(12);
  await Promise.all(pendentes);
  assert.equal(status, 200);
  assert.equal(r.idempotente, true);
  assert.equal(r.evento_id, null);
  assert.equal(gh.gravacoes.length, commits, "nem decisão nem backup");
  assert.equal(db.linhas().length, 1);
});

test("lote com vários posts: cada um decidido e registrado; um só backup no fim", async () => {
  const resp = await enviar([
    { semana: SEMANA, post: 12, acao: "aprovar", versao: V12 },
    { semana: SEMANA, post: 13, acao: "ajustar", comentario: "Outra foto." },
  ]);
  const j = await resp.json();
  assert.equal(resp.status, 200);
  assert.equal(j.ok, true);
  assert.deepEqual(j.resultados.map((r) => [r.post, r.ok, r.estado.acao]), [[12, true, "aprovar"], [13, true, "ajustar"]]);
  assert.deepEqual(aprovacao().posts.map((p) => p.numero), [12]);
  assert.equal(pendentes.length, 1);
  await Promise.all(pendentes);
  assert.equal(gh.texto(CAMINHO_BACKUP).trim().split("\n").length, 2);
});

test("lote misto com um 409: os outros posts são aplicados e o resultado mostra o que falhou", async () => {
  const resp = await enviar([
    { semana: SEMANA, post: 12, acao: "aprovar", versao: "0".repeat(32) },
    { semana: SEMANA, post: 13, acao: "aprovar", versao: V13 },
  ]);
  const j = await resp.json();
  assert.equal(resp.status, 200);
  assert.equal(j.ok, false);
  assert.deepEqual(j.resultados.map((r) => [r.post, r.ok, r.status, r.erro ?? null]),
    [[12, false, 409, "conteudo_mudou"], [13, true, 200, null]]);
  assert.deepEqual(aprovacao().posts.map((p) => p.numero), [13]);
  assert.deepEqual(db.linhas().map((l) => l.post), [13]);
});

test("post fora da semana e erro do GitHub no meio do lote: os outros seguem; o PAT não vaza", async () => {
  let j = await (await enviar([
    { semana: SEMANA, post: 99, acao: "aprovar", versao: V12 },
    { semana: SEMANA, post: 12, acao: "aprovar", versao: V12 },
  ])).json();
  assert.deepEqual(j.resultados.map((r) => [r.post, r.status, r.erro ?? null]), [[99, 400, "post_inexistente"], [12, 200, null]]);

  gh.erroEm = { metodo: "PUT", status: 500, corpo: `falhou com ${env.GH_PAT_WORKER}` };
  const resp = await enviar([{ semana: SEMANA, post: 13, acao: "aprovar", versao: V13 }]);
  const texto = await resp.text();
  assert.ok(!texto.includes(env.GH_PAT_WORKER));
  j = JSON.parse(texto);
  assert.equal(j.resultados[0].status, 502);
  assert.equal(db.linhas().length, 1, "o post 13 não virou evento");
});

test("lote inválido (formato, vazio, grande, post repetido): 400 e nada decidido", async () => {
  const casos = [
    "não é json",
    { outra: [] },
    [],
    Array.from({ length: 11 }, (_, i) => ({ semana: SEMANA, post: i + 1, acao: "desfazer" })),
    [{ semana: SEMANA, post: 12, acao: "aprovar", versao: V12 }, { semana: SEMANA, post: 12, acao: "desfazer" }],
    [{ semana: "2026-41", post: 12, acao: "aprovar", versao: V12 }],
    [{ semana: SEMANA, post: "12", acao: "aprovar", versao: V12 }],
    [{ semana: SEMANA, post: 12, acao: "publicar", versao: V12 }],
    [{ semana: SEMANA, post: 12, acao: "aprovar" }],
    [{ semana: SEMANA, post: 12, acao: "ajustar", comentario: "   " }],
    [{ semana: SEMANA, post: 12, acao: "ajustar", comentario: "x".repeat(2001) }],
    [{ semana: SEMANA, post: 13, acao: "aprovar", versao: V13 }, { semana: SEMANA, post: 12, acao: "ajustar", comentario: 5 }],
  ];
  for (const corpo of casos) {
    const resp = await enviar(corpo);
    assert.equal(resp.status, 400, JSON.stringify(corpo).slice(0, 80));
  }
  assert.equal((await enviar("x".repeat(50000))).status, 413);
  assert.equal(gh.chamadas.length, 0);
  assert.equal(db.linhas().length, 0);
  assert.equal(falhas(), 0, "código certo: nenhuma falha registrada");
});

test("versão enviada diferente da atual: 409 sem gravar", async () => {
  gh.arquivos.get(`site/midia/${SEMANA}/post-12-01.jpg`).bytes = utf8("arte trocada");
  const { r } = await aprovar(12, V12);
  assert.equal(r.status, 409);
  assert.equal(gh.gravacoes.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("conteúdo muda depois da aprovação: o estado guarda a versão antiga (a página volta o post a pendente)", async () => {
  await aprovar(12);
  const posts = JSON.parse(gh.texto(`content/semanas/${SEMANA}/posts.json`));
  posts.posts.find((p) => p.numero === 12).legenda += " (texto revisado)";
  gh.arquivos.get(`content/semanas/${SEMANA}/posts.json`).bytes = utf8(JSON.stringify(posts));
  const estado = await (await rodar(api("/api/estado", { codigo: null }))).json();
  assert.equal(estado.posts["12"].versao_conteudo, V12);
  assert.equal((await aprovar(12, V12)).r.status, 409, "aprovar de novo exige a versão nova");
  const nova = (await decidir({ semana: SEMANA, post: 12, acao: "desfazer" })).r.versao_conteudo;
  assert.notEqual(nova, V12);
});

test("desfazer tira o post do aprovacao.json assinado; de novo é idempotente", async () => {
  await aprovar(12);
  await aprovar(13);
  let { r } = await decidir({ semana: SEMANA, post: 12, acao: "desfazer" });
  assert.equal(r.estado.acao, "desfazer");
  const dados = aprovacao();
  assert.deepEqual(dados.posts.map((p) => p.numero), [13]);
  assert.equal(await assinaturaValida(dados, env.APROVACAO_HMAC_SECRET), true);
  const commits = commitsDeDecisao();
  ({ r } = await decidir({ semana: SEMANA, post: 12, acao: "desfazer" }));
  assert.equal(r.idempotente, true);
  assert.equal(commitsDeDecisao(), commits);
  assert.deepEqual(db.linhas().map((l) => `${l.post}:${l.acao}`), ["12:aprovar", "13:aprovar", "12:desfazer"]);
  await decidir({ semana: SEMANA, post: 13, acao: "desfazer" });
  assert.deepEqual(aprovacao().posts, []);
  assert.equal(await assinaturaValida(aprovacao(), env.APROVACAO_HMAC_SECRET), true);
});

test("desfazer post nunca decidido: nada a fazer", async () => {
  const { r } = await decidir({ semana: SEMANA, post: 13, acao: "desfazer" });
  assert.equal(r.idempotente, true);
  assert.equal(r.evento_id, null);
  assert.equal(gh.gravacoes.length, 0);
  assert.equal(db.linhas().length, 0);
});

test("pedir ajuste: ajuste-<n>.json + repository_dispatch + evento; tira da aprovação; repetido é idempotente", async () => {
  await aprovar(13);
  const { r } = await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "  Trocar a foto da capa.  " });
  assert.equal(r.ok, true, JSON.stringify(r));
  assert.equal(r.estado.acao, "ajustar");
  assert.equal(r.estado.comentario, "Trocar a foto da capa.");
  assert.deepEqual(aprovacao().posts, [], "post com ajuste pedido não fica aprovado");
  const ajuste = JSON.parse(gh.texto(`content/semanas/${SEMANA}/ajuste-13.json`));
  assert.equal(ajuste.texto, "Trocar a foto da capa.");
  assert.deepEqual(gh.disparos, [{ event_type: "ajustar_post", client_payload: { semana: SEMANA, post: 13 } }]);

  const commits = commitsDeDecisao();
  const r2 = (await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "Trocar a foto da capa." })).r;
  assert.equal(r2.idempotente, true);
  assert.equal(commitsDeDecisao(), commits);
  assert.equal(gh.disparos.length, 1);

  await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "Na verdade, trocar o título." });
  assert.equal(gh.disparos.length, 2);
  assert.deepEqual(db.linhas().map((l) => l.acao), ["aprovar", "ajustar", "ajustar"]);
});

test("evento do dispatch configurável (Worker de teste não aciona nada real)", async () => {
  await decidir({ semana: SEMANA, post: 13, acao: "ajustar", comentario: "x" });
  await decidir({ semana: SEMANA, post: 12, acao: "ajustar", comentario: "y" }, { e: { ...env, EVENTO_AJUSTE: "ajustar_post_teste" } });
  assert.deepEqual(gh.disparos.map((d) => d.event_type), ["ajustar_post", "ajustar_post_teste"]);
});

test("sem banco ou sem segredo: 500 sem tocar no GitHub", async () => {
  let r = await rodar(api("/api/estado"), { ...env, DB: undefined });
  assert.equal(r.status, 500);
  r = await rodar(api("/api/estado"), { ...env, APROVACAO_HMAC_SECRET: "" });
  assert.equal(r.status, 500);
  assert.equal(gh.chamadas.length, 0);
});

test("D1 fora do ar: 500, nada é gravado", async () => {
  db.falhar = true;
  const resp = await enviar([{ semana: SEMANA, post: 12, acao: "aprovar", versao: V12 }]);
  assert.equal(resp.status, 500);
  assert.equal(gh.gravacoes.length, 0);
});

test("D1 falha na gravação depois do commit: o post falha avisando; enviar de novo registra sem novo commit", async () => {
  db.falhar = "insert";
  let { r } = await aprovar(12);
  assert.equal(r.status, 500);
  assert.match(r.mensagem, /gravada no GitHub, mas não foi registrada no banco/);
  assert.equal(gravacoesEm(APROV).length, 1);
  db.falhar = false;
  ({ r } = await aprovar(12));
  assert.equal(r.ok, true);
  assert.equal(r.evento_id, 1);
  assert.equal(gravacoesEm(APROV).length, 1, "GitHub já estava certo: nenhum commit novo");
});

// ---------- banco ----------

test("D1: eventos são append-only (UPDATE e DELETE recusados) e o estado é o último evento", async () => {
  const banco = new Banco(db);
  const base = { semana: SEMANA, comentario: "", versao_conteudo: V12, autor: "Aprovador", criado_em: "t" };
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
