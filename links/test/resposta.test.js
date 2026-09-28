import { test } from "node:test";
import assert from "node:assert/strict";
import { tratar, MAX_ENVIOS, MAX_CORPO } from "../lib/resposta.js";
import { D1Falso } from "./d1-falso.js";
import { CAMPOS, agenteValido, fielValido } from "./campos-teste.js";

const AGORA = new Date("2026-10-01T12:00:00Z");
const env = (db = new D1Falso()) => ({ DB: db, IP_HMAC_SECRET: "segredo-de-teste" });

function pedido(corpo, ip = "203.0.113.7") {
  return new Request("https://dizimoarquifln.pages.dev/api/resposta", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": ip },
    body: typeof corpo === "string" ? corpo : JSON.stringify(corpo),
  });
}

test("resposta válida é gravada sem o IP", async () => {
  const e = env();
  const r = await tratar(pedido(agenteValido()), e, AGORA, CAMPOS);
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true });
  const [linha] = e.DB.linhas("respostas");
  assert.equal(linha.tipo, "agente");
  assert.equal(linha.versao_form, 1);
  assert.equal(linha.criado_em, AGORA.toISOString());
  assert.match(linha.id, /^[0-9a-f-]{36}$/);
  assert.equal(JSON.parse(linha.dados).descricao, agenteValido().descricao);
  assert.equal(JSON.stringify(linha).includes("203.0.113.7"), false);
  const [envio] = e.DB.linhas("envios_ip");
  assert.match(envio.ip_hash, /^[0-9a-f]{64}$/);
});

test("honeypot preenchido: responde ok e não grava", async () => {
  const e = env();
  const r = await tratar(pedido({ ...fielValido(), site: "http://spam" }), e, AGORA, CAMPOS);
  assert.equal(r.status, 200);
  assert.equal(e.DB.linhas("respostas").length, 0);
});

test("corpo grande demais: 413", async () => {
  const e = env();
  const r = await tratar(pedido({ ...fielValido(), mensagem: "a".repeat(MAX_CORPO) }), e, AGORA, CAMPOS);
  assert.equal(r.status, 413);
  assert.equal(e.DB.linhas("respostas").length, 0);
});

test("JSON inválido: 400", async () => {
  const r = await tratar(pedido("{nao-json"), env(), AGORA, CAMPOS);
  assert.equal(r.status, 400);
});

test("campos inválidos: 400 com a lista", async () => {
  const e = env();
  const r = await tratar(pedido({ ...fielValido(), consentimento: false }), e, AGORA, CAMPOS);
  assert.equal(r.status, 400);
  assert.deepEqual(await r.json(), { ok: false, erros: ["consentimento"] });
  assert.equal(e.DB.linhas("respostas").length, 0);
});

test("limite por IP: o envio além do máximo em 1 hora recebe 429; outro IP segue", async () => {
  const e = env();
  for (let i = 0; i < MAX_ENVIOS; i++) {
    assert.equal((await tratar(pedido(fielValido()), e, AGORA, CAMPOS)).status, 200);
  }
  assert.equal((await tratar(pedido(fielValido()), e, AGORA, CAMPOS)).status, 429);
  assert.equal(e.DB.linhas("respostas").length, MAX_ENVIOS);
  assert.equal((await tratar(pedido(fielValido(), "198.51.100.1"), e, AGORA, CAMPOS)).status, 200);
  const depois = new Date(AGORA.getTime() + 61 * 60 * 1000);
  assert.equal((await tratar(pedido(fielValido()), e, depois, CAMPOS)).status, 200);
});

test("envios com mais de 1 dia são apagados", async () => {
  const e = env();
  await tratar(pedido(fielValido()), e, AGORA, CAMPOS);
  const amanha = new Date(AGORA.getTime() + 25 * 60 * 60 * 1000);
  await tratar(pedido(fielValido(), "198.51.100.1"), e, amanha, CAMPOS);
  assert.equal(e.DB.linhas("envios_ip").length, 1);
});

test("sem o segredo do IP: 500 e nada gravado", async () => {
  const e = { DB: new D1Falso() };
  const r = await tratar(pedido(fielValido()), e, AGORA, CAMPOS);
  assert.equal(r.status, 500);
  assert.equal(e.DB.linhas("respostas").length, 0);
});

test("respostas é append-only", () => {
  const db = new D1Falso();
  db.db.exec(`INSERT INTO respostas VALUES ('x', '2026', 'fiel', 1, '{}')`);
  assert.throws(() => db.db.exec(`UPDATE respostas SET tipo = 'agente'`), /append-only/);
});
