// Campos pequenos e fixos para os testes (os reais são gerados em lib/campos.js por `python -m pastoral.links`).
export const CAMPOS = {
  versao: 1,
  limites: { texto_curto: 120, texto_longo: 2000 },
  paroquias: ["Florianópolis - Santo Antônio (Centro)", "Tijucas - São Sebastião"],
  outra: "Outra",
  prefiro_nao_dizer: "Prefiro não dizer",
  agente: {
    funcoes: ["Coordenador(a)", "Outro serviço"],
    pedidos: ["Dificuldade na pastoral", "Pedido de capacitação", "Pedido de material", "Outro"],
    pedidos_com_contato: ["Pedido de capacitação", "Pedido de material"],
    temas: ["Prestação de contas e transparência", "Outro"],
  },
  fiel: { assuntos: ["Dúvida sobre o dízimo", "Outro"] },
};

export const agenteValido = () => ({
  tipo: "agente",
  paroquia: "Tijucas - São Sebastião",
  funcao: "Coordenador(a)",
  pedido: "Dificuldade na pastoral",
  temas: ["Prestação de contas e transparência"],
  descricao: "Temos dificuldade em apresentar os resultados.",
  consentimento: true,
});

export const fielValido = () => ({
  tipo: "fiel",
  assunto: "Dúvida sobre o dízimo",
  mensagem: "Como é feito o registro?",
  consentimento: true,
});
