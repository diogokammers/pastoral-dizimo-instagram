// Worker de aprovação com o GitHub falso (fetch mockado): nenhuma chamada sai para a rede.
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { tratar } from "../src/index.js";
import { assinarLink, assinaturaValida, deUtf8, sha256Hex, utf8 } from "../src/nucleo.js";
import { ENV, GitHubFalso, VETORES } from "./github-falso.js";

const AGORA = new Date("2026-10-02T13:00:00Z"); // antes da expiração dos links (1791000000)
const BASE = "https://pastoral-dizimo-aprovacao.exemplo.workers.dev";
let gh;

beforeEach(() => {
  gh = new GitHubFalso();
});

const rodar = (req) => tratar(req, ENV, { fetch: gh.fetch, agora: () => AGORA });

async function link(acao, post, nonce = "0123456789abcdef", troca = {}) {
  const p = { s: "2026-W41", a: acao, p: post == null ? "" : String(post), e: "1791000000", n: nonce,
    v: VETORES.semana.versao, ...troca };
  p.h = await assinarLink(ENV.LINK_HMAC_SECRET, p);
  return p;
}

const get = (p) => rodar(new Request(`${BASE}/a?${new URLSearchParams(p)}`));
const post = (p, extra = {}) => rodar(new Request(`${BASE}/a`, { method: "POST", body: new URLSearchParams({ ...p, ...extra }) }));
const aprovacaoGravada = () => JSON.parse(gh.texto("content/semanas/2026-W41/aprovacao.json"));

test("GET com link válido só mostra a confirmação (pré-carregamento do Gmail não aprova)", async () => {
  const r = await get(await link("aprovar_tudo", null));
  assert.equal(r.status, 200);
  const html = await r.text();
  assert.match(html, /<form method="post" action="\/a">/);
  assert.match(html, /Aprovar os posts da semana 2026-W41/);
  assert.match(html, /semanas\/2026-W41\//, "link para a prévia");
  assert.equal(gh.chamadas.length, 0, "GET não toca no GitHub");
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  assert.match(r.headers.get("Content-Security-Policy"), /default-src 'none'/);
});

test("link com assinatura inválida ou expirado é recusado sem tocar no GitHub", async () => {
  const p = await link("aprovar_post", 12);
  let r = await get({ ...p, p: "13" });
  assert.equal(r.status, 403);
  assert.match(await r.text(), /assinatura inválida/);
  r = await tratar(new Request(`${BASE}/a?${new URLSearchParams(p)}`), ENV,
    { fetch: gh.fetch, agora: () => new Date(1791000000 * 1000) });
  assert.equal(r.status, 403);
  assert.match(await r.text(), /link expirado/);
  r = await post({ ...p, h: "0".repeat(64) });
  assert.equal(r.status, 403);
  assert.equal(gh.chamadas.length, 0);
});

test("POST aprovar_tudo grava aprovacao.json igual ao vetor do Python e válido para o portão", async () => {
  const r = await post(await link("aprovar_tudo", null));
  assert.equal(r.status, 200, await r.clone().text());
  assert.match(await r.text(), /Aprovado/);
  assert.equal(gh.gravacoes.length, 1);
  assert.equal(gh.gravacoes[0].caminho, "content/semanas/2026-W41/aprovacao.json");
  assert.equal(gh.gravacoes[0].ramo, "master");
  const dados = aprovacaoGravada();
  assert.deepEqual(dados, VETORES.aprovacao);
  assert.equal(await assinaturaValida(dados, ENV.APROVACAO_HMAC_SECRET), true);
  for (const c of gh.chamadas) {
    assert.equal(c.headers.Authorization, `Bearer ${ENV.GH_PAT_WORKER}`);
    assert.equal(c.headers["User-Agent"], "pastoral-dizimo-aprovacao");
  }
});

test("hashes das artes vêm do conteúdo lido no GitHub", async () => {
  await post(await link("aprovar_post", 12));
  const item = aprovacaoGravada().posts[0];
  const bytes = gh.arquivos.get("site/midia/2026-W41/post-12-02.jpg").bytes;
  assert.equal(item.artes[1].sha256, await sha256Hex(bytes));
});

test("aprovar duas vezes não duplica nem faz novo commit", async () => {
  const p = await link("aprovar_tudo", null);
  await post(p);
  const r = await post(p);
  assert.equal(r.status, 200);
  assert.match(await r.text(), /já estava aprovado/);
  assert.equal(gh.gravacoes.length, 1);
  const r2 = await post(await link("aprovar_post", 12, "fedcba9876543210"));
  assert.match(await r2.text(), /já estava aprovado/);
  assert.equal(gh.gravacoes.length, 1);
});

test("aprovar posts separados acumula no mesmo aprovacao.json", async () => {
  await post(await link("aprovar_post", 12, "1111111111111111"));
  await post(await link("aprovar_post", 13, "2222222222222222"));
  const dados = aprovacaoGravada();
  assert.deepEqual(dados.posts.map((p) => p.numero), [12, 13]);
  assert.equal(dados.nonce, "2222222222222222");
  assert.equal(await assinaturaValida(dados, ENV.APROVACAO_HMAC_SECRET), true);
  assert.equal(gh.gravacoes.length, 2);
});

test("conteúdo mudou depois do e-mail: recusa sem gravar", async () => {
  gh.arquivos.get("site/midia/2026-W41/post-12-01.jpg").bytes = utf8("arte trocada");
  const r = await post(await link("aprovar_tudo", null));
  assert.equal(r.status, 409);
  assert.match(await r.text(), /mudou depois do e-mail/);
  assert.equal(gh.gravacoes.length, 0);
});

test("aprovacao.json existente com assinatura inválida não é sobrescrito", async () => {
  const falso = { ...VETORES.aprovacao, assinatura: "0".repeat(64) };
  gh.arquivos.set("content/semanas/2026-W41/aprovacao.json", { bytes: utf8(JSON.stringify(falso)), sha: "x1" });
  const r = await post(await link("aprovar_post", 12, "3333333333333333"));
  assert.equal(r.status, 500);
  assert.equal(gh.gravacoes.length, 0);
});

test("conflito de sha no commit: relê e tenta de novo", async () => {
  gh.conflitosPendentes = 1;
  const r = await post(await link("aprovar_tudo", null));
  assert.equal(r.status, 200);
  assert.equal(gh.gravacoes.length, 1);
});

test("post que não é da semana é recusado", async () => {
  const r = await post(await link("aprovar_post", 99));
  assert.equal(r.status, 400);
  assert.equal(gh.gravacoes.length, 0);
});

test("erro do GitHub não vaza o PAT", async () => {
  gh.erroEm = { metodo: "GET", status: 500, corpo: `falhou com ${ENV.GH_PAT_WORKER}` };
  const r = await post(await link("aprovar_tudo", null));
  assert.equal(r.status, 502);
  const html = await r.text();
  assert.ok(!html.includes(ENV.GH_PAT_WORKER));
});

test("sem segredos configurados: 500 e nada gravado", async () => {
  const r = await tratar(new Request(`${BASE}/a?${new URLSearchParams(await link("aprovar_tudo", null))}`),
    { ...ENV, LINK_HMAC_SECRET: "" }, { fetch: gh.fetch, agora: () => AGORA });
  assert.equal(r.status, 500);
  assert.equal(gh.chamadas.length, 0);
});

test("segredo com quebra de linha no fim (colado no PowerShell) ainda vale", async () => {
  const env = { ...ENV, LINK_HMAC_SECRET: ENV.LINK_HMAC_SECRET + "\r\n", APROVACAO_HMAC_SECRET: ENV.APROVACAO_HMAC_SECRET + "\n" };
  const r = await tratar(new Request(`${BASE}/a`, { method: "POST", body: new URLSearchParams(await link("aprovar_tudo", null)) }),
    env, { fetch: gh.fetch, agora: () => AGORA });
  assert.equal(r.status, 200);
  assert.deepEqual(aprovacaoGravada(), VETORES.aprovacao);
});

test("ajustar: GET mostra formulário; POST grava ajuste-<n>.json e dispara repository_dispatch", async () => {
  const p = await link("ajustar_post", 13);
  const form = await (await get(p)).text();
  assert.match(form, /<textarea name="texto"/);
  assert.equal(gh.chamadas.length, 0);

  const r = await post(p, { texto: "  Trocar o título da capa por “Encontro de fé”.  " });
  assert.equal(r.status, 200);
  assert.equal(gh.gravacoes.length, 1);
  assert.equal(gh.gravacoes[0].caminho, "content/semanas/2026-W41/ajuste-13.json");
  const ajuste = JSON.parse(gh.gravacoes[0].texto);
  assert.deepEqual(ajuste, { semana: "2026-W41", post: 13, texto: "Trocar o título da capa por “Encontro de fé”.",
    pedido_em: "2026-10-02T13:00:00+00:00", nonce: "0123456789abcdef" });
  assert.deepEqual(gh.disparos, [{ event_type: "ajustar_post", client_payload: { semana: "2026-W41", post: 13 } }]);

  await post(p, { texto: "de novo" });
  assert.equal(gh.gravacoes.length, 1, "mesmo link não grava de novo");
  assert.equal(gh.disparos.length, 1);
});

test("ajustar sem texto (ou longo demais) volta ao formulário sem gravar", async () => {
  const p = await link("ajustar_post", 13);
  let r = await post(p, { texto: "   " });
  assert.equal(r.status, 400);
  r = await post(p, { texto: "x".repeat(2001) });
  assert.equal(r.status, 400);
  assert.equal(gh.gravacoes.length + gh.disparos.length, 0);
});

test("ajustar post fora da semana é recusado", async () => {
  const r = await post(await link("ajustar_post", 99), { texto: "algo" });
  assert.equal(r.status, 400);
  assert.equal(gh.gravacoes.length, 0);
});

test("texto do ajuste é escapado no HTML", async () => {
  const p = await link("ajustar_post", 13);
  const r = await post(p, { texto: "<script>alert(1)</script>" });
  const html = await r.text();
  assert.ok(!html.includes("<script>alert"));
});

test("outras rotas e métodos", async () => {
  assert.equal((await rodar(new Request(`${BASE}/`))).status, 404);
  assert.equal((await rodar(new Request(`${BASE}/a`, { method: "PUT" }))).status, 405);
  assert.equal((await get({})).status, 403);
});

test("decodificação estrita de UTF-8", () => {
  assert.throws(() => deUtf8(new Uint8Array([0xff])));
});
