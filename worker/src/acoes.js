// Ações comuns ao link do e-mail (/a, ADR-009) e ao painel (/api, ADR-011): ler a semana no GitHub,
// calcular os itens do ADR-008, gravar aprovacao.json assinado e registrar pedidos de ajuste.
// Uma só implementação para os dois caminhos — o painel não duplica regras.

import { ConflitoGitHub } from "./github.js";
import { assinaturaValida, itensSemana, paraHex } from "./nucleo.js";

export const TEXTO_MAX = 2000;

export class Recusa extends Error {
  constructor(status, titulo, mensagem, codigo = "recusado") {
    super(mensagem);
    this.status = status;
    this.titulo = titulo;
    this.codigo = codigo;
  }
}

export const isoUtc = (d) => d.toISOString().slice(0, 19) + "+00:00";

export const novoNonce = () => paraHex(crypto.getRandomValues(new Uint8Array(16)));

export const segredoAprovacao = (env) => String(env.APROVACAO_HMAC_SECRET ?? "").trim();

const pastaSemana = (semana) => `content/semanas/${semana}`;

// agenda.json e posts.json da semana, como estão no ramo configurado.
export async function lerSemana(gh, semana) {
  const agenda = await gh.lerJson(`${pastaSemana(semana)}/agenda.json`);
  const posts = await gh.lerJson(`${pastaSemana(semana)}/posts.json`);
  if (agenda.semana !== semana) throw new Recusa(500, "Agenda inconsistente", "agenda.json é de outra semana.");
  return { agenda, posts };
}

// Itens do ADR-008 (com os sha256 das artes lidas no GitHub). `numeros` limita a alguns posts:
// o painel decide um post por vez e não precisa ler as artes da semana inteira.
export async function itensDe(gh, semana, { agenda, posts }, numeros = null) {
  const entradas = numeros ? agenda.posts.filter((e) => numeros.includes(e.numero)) : agenda.posts;
  return itensSemana({ ...agenda, posts: entradas }, posts, (arquivo) => gh.lerBytes(`site/midia/${semana}/${arquivo}`));
}

// Lê aprovacao.json (a assinatura existente precisa conferir), aplica `transformar(existente)` →
// { dados, mudou } e commita se mudou. Em conflito de sha, relê e tenta de novo (até 3 vezes).
export async function atualizarAprovacao(gh, env, semana, transformar, mensagem) {
  const segredo = segredoAprovacao(env);
  const caminho = `${pastaSemana(semana)}/aprovacao.json`;
  for (let tentativa = 1; ; tentativa++) {
    const atual = await gh.lerJsonComSha(caminho);
    if (atual && (atual.dados.semana !== semana || !(await assinaturaValida(atual.dados, segredo)))) {
      throw new Recusa(500, "Aprovação existente inválida",
        "O aprovacao.json atual não tem assinatura válida. Nada foi gravado; avise o Diogo.", "aprovacao_invalida");
    }
    const { dados, mudou } = await transformar(atual?.dados ?? null, segredo);
    if (!mudou) return { mudou: false, commit: null, dados };
    try {
      const commit = await gh.gravar(caminho, JSON.stringify(dados, null, 2) + "\n", mensagem, atual?.sha);
      return { mudou: true, commit, dados };
    } catch (erro) {
      if (erro instanceof ConflitoGitHub && tentativa < 3) continue;
      throw erro;
    }
  }
}

// Grava content/semanas/<semana>/ajuste-<n>.json e dispara repository_dispatch. Idempotente pelo nonce.
export async function registrarAjuste(gh, env, semana, numero, texto, nonce, pedidoEm, mensagem) {
  const caminho = `${pastaSemana(semana)}/ajuste-${numero}.json`;
  let commit = null;
  for (let tentativa = 1; ; tentativa++) {
    const atual = await gh.lerJsonComSha(caminho);
    if (atual && atual.dados.nonce === nonce) return { mudou: false, texto: atual.dados.texto, commit: null };
    const dados = { semana, post: numero, texto, pedido_em: pedidoEm, nonce };
    try {
      commit = await gh.gravar(caminho, JSON.stringify(dados, null, 2) + "\n", mensagem, atual?.sha);
      break;
    } catch (erro) {
      if (erro instanceof ConflitoGitHub && tentativa < 3) continue;
      throw erro;
    }
  }
  await gh.disparar(env.EVENTO_AJUSTE || "ajustar_post", { semana, post: numero });
  return { mudou: true, texto, commit };
}
