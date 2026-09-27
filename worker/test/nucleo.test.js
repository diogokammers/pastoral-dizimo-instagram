// Teste cruzado Python → JS: os vetores gerados por `python -m pastoral.aprovacao --vetores` têm de sair
// idênticos aqui (JSON canônico, HMAC, textos da legenda, itens, versão, links e aprovacao.json).
import assert from "node:assert/strict";
import { test } from "node:test";

import * as n from "../src/nucleo.js";
import { VETORES } from "./github-falso.js";

test("JSON canônico idêntico ao do Python", async () => {
  for (const caso of VETORES.canonico) {
    assert.equal(n.canonicoTexto(caso.entrada), caso.saida);
    assert.equal(await n.sha256Hex(n.canonico(caso.entrada)), caso.sha256);
  }
});

test("canônico recusa número não inteiro (evita divergência de formatação de float)", () => {
  assert.throws(() => n.canonicoTexto({ x: 1.5 }));
});

test("assinatura HMAC idêntica à do Python (sem o campo assinatura)", async () => {
  for (const caso of VETORES.assinar) {
    assert.equal(await n.assinar(caso.dados, caso.segredo), caso.assinatura);
    const assinado = { ...caso.dados, assinatura: caso.assinatura };
    assert.equal(await n.assinaturaValida(assinado, caso.segredo), true);
    assert.equal(await n.assinaturaValida(assinado, "outro"), false);
  }
});

test("texto da legenda usa o strip do Python", () => {
  for (const caso of VETORES.legendas) assert.equal(n.textoLegenda(caso.post), caso.texto);
});

test("itens e versão da semana idênticos aos do Python", async () => {
  const { semana, itens, versao, artes_base64 } = VETORES.semana;
  const { readFileSync } = await import("node:fs");
  const { join } = await import("node:path");
  const { FIXTURE } = await import("./github-falso.js");
  const pasta = join(FIXTURE, "content", "semanas", semana);
  const agenda = JSON.parse(readFileSync(join(pasta, "agenda.json"), "utf8"));
  const posts = JSON.parse(readFileSync(join(pasta, "posts.json"), "utf8"));
  const calculados = await n.itensSemana(agenda, posts, async (a) => n.deBase64(artes_base64[a]));
  assert.deepEqual(calculados, itens);
  assert.equal(await n.versao(semana, calculados), versao);
});

test("links assinados pelo Python valem no JS", async () => {
  const { segredo, agora, validos } = VETORES.links;
  for (const params of validos) {
    assert.equal(await n.assinarLink(segredo, params), params.h);
    assert.equal(await n.motivoLinkInvalido(segredo, params, agora), null);
  }
});

test("link adulterado, expirado ou malformado é recusado", async () => {
  const { segredo, agora, validos } = VETORES.links;
  const base = validos[1];
  for (const [campo, valor] of [["s", "2026-W42"], ["p", "13"], ["e", "1791000001"], ["n", "0123456789abcdee"], ["v", "1".repeat(32)]]) {
    assert.equal(await n.motivoLinkInvalido(segredo, { ...base, [campo]: valor }, agora), "assinatura inválida", campo);
  }
  assert.equal(await n.motivoLinkInvalido(segredo, { ...base, h: "0".repeat(64) }, agora), "assinatura inválida");
  assert.equal(await n.motivoLinkInvalido(segredo, base, Number(base.e)), "link expirado");
  assert.equal(await n.motivoLinkInvalido(segredo, { ...base, a: "publicar" }, agora), "link malformado");
  assert.equal(await n.motivoLinkInvalido(segredo, { ...base, h: "xyz" }, agora), "link malformado");
  assert.equal(await n.motivoLinkInvalido(segredo, { ...validos[0], p: "12" }, agora), "link malformado");
  assert.equal(await n.motivoLinkInvalido("", base, agora), "segredo ausente");
  assert.equal(await n.motivoLinkInvalido("outro", base, agora), "assinatura inválida");
});

test("aprovacao.json montado no JS é byte a byte o do Python", async () => {
  const esperado = VETORES.aprovacao;
  const { dados, mudou } = await n.montarAprovacao(null, esperado.semana, VETORES.semana.itens, [12, 13],
    esperado.nonce, esperado.aprovado_por, esperado.aprovado_em, "segredo-aprovacao-de-teste");
  assert.equal(mudou, true);
  assert.deepEqual(dados, esperado);
  assert.deepEqual(Object.keys(dados), ["semana", "aprovado_por", "aprovado_em", "nonce", "posts", "assinatura"]);
});

test("montarAprovacao é idempotente e acumula posts", async () => {
  const itens = VETORES.semana.itens;
  const s = "segredo";
  const a1 = await n.montarAprovacao(null, "2026-W41", itens, [12], "n1", "Diogo", "t1", s);
  const a2 = await n.montarAprovacao(a1.dados, "2026-W41", itens, [12], "n2", "Diogo", "t2", s);
  assert.equal(a2.mudou, false);
  const a3 = await n.montarAprovacao(a1.dados, "2026-W41", itens, [13], "n1", "Diogo", "t3", s);
  assert.equal(a3.mudou, false, "mesmo nonce = link já usado");
  const a4 = await n.montarAprovacao(a1.dados, "2026-W41", itens, [13], "n3", "Diogo", "t4", s);
  assert.equal(a4.mudou, true);
  assert.deepEqual(a4.dados.posts.map((p) => p.numero), [12, 13]);
  await assert.rejects(n.montarAprovacao(null, "2026-W41", itens, [99], "n", "D", "t", s));
});

// ---------- painel (ADR-011) ----------

test("versão de cada post idêntica à do Python", async () => {
  for (const item of VETORES.semana.itens) {
    assert.equal(await n.versaoPost(VETORES.semana.semana, item), VETORES.versao_post[String(item.numero)]);
  }
});

test("remover da aprovação é byte a byte o do Python e idempotente", async () => {
  const r = await n.removerDaAprovacao(VETORES.aprovacao, "2026-W41", 12, "fedcba9876543210", "Aprovador",
    "2026-10-03T10:00:00+00:00", "segredo-aprovacao-de-teste");
  assert.equal(r.mudou, true);
  assert.deepEqual(r.dados, VETORES.remocao);
  assert.deepEqual(Object.keys(r.dados), ["semana", "aprovado_por", "aprovado_em", "nonce", "posts", "assinatura"]);
  const de_novo = await n.removerDaAprovacao(r.dados, "2026-W41", 12, "n", "Aprovador", "t", "segredo-aprovacao-de-teste");
  assert.equal(de_novo.mudou, false);
  assert.equal(de_novo.dados, r.dados);
  assert.deepEqual(await n.removerDaAprovacao(null, "2026-W41", 12, "n", "Aprovador", "t", "s"), { dados: null, mudou: false });
});
