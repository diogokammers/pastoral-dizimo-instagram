import { test } from "node:test";
import assert from "node:assert/strict";
import { validar } from "../lib/validar.js";
import { CAMPOS } from "../lib/campos.js";

// os campos gerados (python -m pastoral.links) funcionam com a validação do servidor
test("campos reais: agente com capacitação e fiel anônimo", () => {
  const agente = {
    tipo: "agente", paroquia: CAMPOS.paroquias[0], funcao: CAMPOS.agente.funcoes[0],
    pedido: "Pedido de capacitação", temas: [CAMPOS.agente.temas[0]], descricao: "Formação da equipe nova.",
    nome: "Ana", contato: "ana@exemplo.test", consentimento: true,
  };
  assert.equal(validar(agente, CAMPOS).ok, true);
  assert.deepEqual(validar({ ...agente, contato: "" }, CAMPOS).erros, ["contato"]);
  const fiel = { tipo: "fiel", assunto: CAMPOS.fiel.assuntos[0], mensagem: "Dúvida.", consentimento: true };
  assert.equal(validar(fiel, CAMPOS).ok, true);
  assert.equal(CAMPOS.paroquias.length, 82);
});
