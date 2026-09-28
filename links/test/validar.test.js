import { test } from "node:test";
import assert from "node:assert/strict";
import { validar } from "../lib/validar.js";
import { CAMPOS, agenteValido, fielValido } from "./campos-teste.js";

const com = (base, mudancas) => ({ ...base, ...mudancas });
const erros = (corpo) => validar(corpo, CAMPOS).erros;

test("agente válido passa e devolve só os campos conhecidos, aparados", () => {
  const r = validar(com(agenteValido(), { descricao: "  texto  ", extra: "x", nome: " Ana " }), CAMPOS);
  assert.equal(r.ok, true);
  assert.equal(r.tipo, "agente");
  assert.equal(r.dados.descricao, "texto");
  assert.equal(r.dados.nome, "Ana");
  assert.equal("extra" in r.dados, false);
  assert.equal("tipo" in r.dados, false);
  assert.equal("consentimento" in r.dados, false);
});

test("fiel válido sem paróquia e sem contato passa", () => {
  const r = validar(fielValido(), CAMPOS);
  assert.equal(r.ok, true);
  assert.equal(r.dados.paroquia, "");
});

test("tipo desconhecido é recusado", () => {
  assert.deepEqual(erros({ tipo: "outro" }), ["tipo"]);
  assert.deepEqual(erros(null), ["tipo"]);
});

test("agente: paróquia obrigatória e da lista", () => {
  assert.deepEqual(erros(com(agenteValido(), { paroquia: "" })), ["paroquia"]);
  assert.deepEqual(erros(com(agenteValido(), { paroquia: "Inventada" })), ["paroquia"]);
});

test("paróquia 'Outra' exige o nome dela", () => {
  assert.deepEqual(erros(com(agenteValido(), { paroquia: "Outra" })), ["paroquia_outra"]);
  assert.equal(validar(com(agenteValido(), { paroquia: "Outra", paroquia_outra: "Nova" }), CAMPOS).ok, true);
});

test("fiel pode dizer 'Prefiro não dizer'; agente não", () => {
  assert.equal(validar(com(fielValido(), { paroquia: "Prefiro não dizer" }), CAMPOS).ok, true);
  assert.deepEqual(erros(com(agenteValido(), { paroquia: "Prefiro não dizer" })), ["paroquia"]);
});

test("agente: função, pedido e temas das listas fechadas", () => {
  assert.deepEqual(erros(com(agenteValido(), { funcao: "Chefe" })), ["funcao"]);
  assert.deepEqual(erros(com(agenteValido(), { pedido: "Qualquer" })), ["pedido"]);
  assert.deepEqual(erros(com(agenteValido(), { temas: [] })), ["temas"]);
  assert.deepEqual(erros(com(agenteValido(), { temas: ["Inventado"] })), ["temas"]);
  assert.deepEqual(erros(com(agenteValido(), { temas: "Outro" })), ["temas"]);
});

test("temas repetidos viram um só", () => {
  const r = validar(com(agenteValido(), { temas: ["Outro", "Outro"] }), CAMPOS);
  assert.deepEqual(r.dados.temas, ["Outro"]);
});

test("textos: obrigatórios e com limite", () => {
  assert.deepEqual(erros(com(agenteValido(), { descricao: "   " })), ["descricao"]);
  assert.deepEqual(erros(com(agenteValido(), { descricao: "a".repeat(2001) })), ["descricao"]);
  assert.deepEqual(erros(com(fielValido(), { mensagem: "" })), ["mensagem"]);
  assert.deepEqual(erros(com(fielValido(), { nome: "a".repeat(121) })), ["nome"]);
  assert.deepEqual(erros(com(fielValido(), { mensagem: 5 })), ["mensagem"]);
});

test("pedido de capacitação ou material exige nome e contato", () => {
  for (const pedido of ["Pedido de capacitação", "Pedido de material"]) {
    assert.deepEqual(erros(com(agenteValido(), { pedido })), ["nome", "contato"]);
    assert.equal(validar(com(agenteValido(), { pedido, nome: "Ana", contato: "48 99999-0000" }), CAMPOS).ok, true);
  }
});

test("sem consentimento não passa", () => {
  assert.deepEqual(erros(com(fielValido(), { consentimento: false })), ["consentimento"]);
  assert.deepEqual(erros(com(agenteValido(), { consentimento: "sim" })), ["consentimento"]);
});

test("fiel: assunto da lista", () => {
  assert.deepEqual(erros(com(fielValido(), { assunto: "Doação" })), ["assunto"]);
});
