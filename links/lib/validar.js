// Validação das respostas no servidor (ADR-013). Espelha a da página, mas é a que vale: listas fechadas,
// tamanhos, obrigatórios e o contato obrigatório nos pedidos de capacitação e de material.
// Devolve { ok: true, tipo, dados } só com os campos conhecidos (aparados) ou { ok: false, erros: [campo…] }.

const texto = (v) => (typeof v === "string" ? v.trim() : v === undefined || v === null ? "" : null);

export function validar(corpo, CAMPOS) {
  if (!corpo || typeof corpo !== "object" || !["agente", "fiel"].includes(corpo.tipo)) {
    return { ok: false, erros: ["tipo"] };
  }
  const tipo = corpo.tipo;
  const { texto_curto: curto, texto_longo: longo } = CAMPOS.limites;
  const erros = [];
  const dados = {};

  // campo de texto: null = tipo errado; obrigatorio e tamanho máximo
  const campoTexto = (nome, max, obrigatorio) => {
    const v = texto(corpo[nome]);
    if (v === null || v.length > max || (obrigatorio && !v)) erros.push(nome);
    dados[nome] = v ?? "";
  };
  const campoLista = (nome, opcoes, obrigatorio) => {
    const v = texto(corpo[nome]);
    if (v === null || (v && !opcoes.includes(v)) || (obrigatorio && !v)) erros.push(nome);
    dados[nome] = v ?? "";
  };

  // paróquia: lista oficial + "Outra" (com o nome); o fiel também pode "Prefiro não dizer" ou deixar em branco
  const opcoesParoquia = [...CAMPOS.paroquias, CAMPOS.outra];
  if (tipo === "fiel") opcoesParoquia.push(CAMPOS.prefiro_nao_dizer);
  campoLista("paroquia", opcoesParoquia, tipo === "agente");
  if (dados.paroquia === CAMPOS.outra) campoTexto("paroquia_outra", curto, true);

  if (tipo === "agente") {
    const a = CAMPOS.agente;
    campoLista("funcao", a.funcoes, true);
    campoLista("pedido", a.pedidos, true);
    const temas = corpo.temas;
    if (!Array.isArray(temas) || temas.length === 0 || !temas.every((t) => a.temas.includes(t))) {
      erros.push("temas");
      dados.temas = [];
    } else {
      dados.temas = [...new Set(temas)];
    }
    campoTexto("descricao", longo, true);
    const precisaContato = a.pedidos_com_contato.includes(dados.pedido);
    campoTexto("nome", curto, precisaContato);
    campoTexto("contato", curto, precisaContato);
  } else {
    campoLista("assunto", CAMPOS.fiel.assuntos, true);
    campoTexto("mensagem", longo, true);
    campoTexto("nome", curto, false);
    campoTexto("contato", curto, false);
  }

  if (corpo.consentimento !== true) erros.push("consentimento");
  return erros.length ? { ok: false, erros } : { ok: true, tipo, dados };
}
