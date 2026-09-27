// API do painel de aprovação (ADR-011, fluxo de rascunho e envio do ADR-012), chamada pela página do
// GitHub Pages (site/aprovacao/). Só aceita o origin do Pages (CORS; outro origin ou nenhum → 403).
//
// OPTIONS /api/*       preflight CORS.
// GET  /api/estado     PÚBLICO: último evento de cada post (sem ip_hash).
// POST /api/decisoes   { decisoes: [{ semana, post, acao: aprovar|ajustar|desfazer, versao, comentario }] }
//   Exige o código de envio no header "Authorization: Bearer <código>" (nunca na URL), com limite de
//   tentativas (limite.js). Cada post é decidido à parte, na ordem, e de forma idempotente:
//   aprovar  → confere a versão do post (hash do conteúdo atual no GitHub) e grava aprovacao.json
//              assinado, igual ao link do e-mail (ADR-009): o publicar.py o publica na data agendada.
//   ajustar  → tira o post do aprovacao.json (se estava), grava ajuste-<n>.json e dispara repository_dispatch.
//   desfazer → tira o post do aprovacao.json assinado (reassina): o portão não o publica mais.
//   Se um post falha (ex.: 409, conteúdo mudou), os outros seguem; a resposta diz o resultado de cada um.
// Todo evento vai para o D1 (append-only) e depois para content/aprovacoes/eventos.jsonl (backup).

import { autorDoCodigo, cabecalhosCors, codigoDoPedido, origemPermitida } from "./acesso.js";
import {
  Recusa, TEXTO_MAX, atualizarAprovacao, isoUtc, itensDe, lerSemana, novoNonce, registrarAjuste, segredoAprovacao,
} from "./acoes.js";
import { exportarEventos } from "./backup.js";
import { Banco } from "./banco.js";
import { ErroGitHub, GitHub } from "./github.js";
import { Limite, MAX_FALHAS } from "./limite.js";
import { hmacHex, montarAprovacao, removerDaAprovacao, utf8, versaoPost } from "./nucleo.js";

const ACOES_PAINEL = ["aprovar", "ajustar", "desfazer"];
const CORPO_MAX = 40000;
export const LOTE_MAX = 10;

function json(status, corpo, cors) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...(cors ?? {}),
    },
  });
}

// Evento como a página o vê (sem ip_hash).
export const publico = (ev) => ev && {
  id: ev.id, post: ev.post, semana: ev.semana, acao: ev.acao, comentario: ev.comentario,
  versao_conteudo: ev.versao_conteudo, autor: ev.autor, criado_em: ev.criado_em, origem: ev.origem,
  commit_sha: ev.commit_sha,
};

function validarItem(corpo) {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return "decisão inválida";
  const { semana, post, acao, versao, comentario } = corpo;
  if (typeof semana !== "string" || !/^\d{4}-W\d{2}$/.test(semana)) return "semana inválida";
  if (!Number.isInteger(post) || post < 1 || post > 9999) return "post inválido";
  if (!ACOES_PAINEL.includes(acao)) return "ação inválida";
  if (acao === "aprovar" && (typeof versao !== "string" || !/^[0-9a-f]{32}$/.test(versao))) return "versão inválida";
  if (comentario !== undefined && typeof comentario !== "string") return "comentário inválido";
  const texto = (comentario ?? "").trim();
  if (texto.length > TEXTO_MAX) return `comentário com mais de ${TEXTO_MAX} caracteres`;
  if (acao === "ajustar" && !texto) return "escreva o que ajustar";
  return null;
}

// Valida o lote inteiro antes de tocar em qualquer coisa: formato ruim → 400 e nada é decidido.
function validarLote(corpo) {
  if (!corpo || typeof corpo !== "object" || !Array.isArray(corpo.decisoes)) return "envie { decisoes: [...] }";
  const lista = corpo.decisoes;
  if (!lista.length) return "nenhuma decisão enviada";
  if (lista.length > LOTE_MAX) return `no máximo ${LOTE_MAX} decisões por envio`;
  for (const item of lista) {
    const problema = validarItem(item);
    if (problema) return `post ${item?.post ?? "?"}: ${problema}`;
  }
  if (new Set(lista.map((d) => d.post)).size !== lista.length) return "post repetido no mesmo envio";
  return null;
}

// HMAC do IP (16 hex): auditoria no D1 e chave do limite de tentativas. Nunca é exposto.
async function ipHash(env, request) {
  const ip = request.headers.get("CF-Connecting-IP");
  return ip ? (await hmacHex(segredoAprovacao(env), utf8(`ip-v1\n${ip}`))).slice(0, 16) : null;
}

const horaBrasilia = (iso) =>
  new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });

// Confere o código com limite de tentativas. Devolve { autor } ou { resposta } (401/429 já prontos).
async function autenticar(request, env, deps, ip, cors) {
  const limite = new Limite(env.DB);
  const chave = ip ?? "sem-ip";
  const bloqueio = await limite.bloqueadoAte(chave, deps.agora);
  if (bloqueio) {
    return { resposta: json(429, { erro: "bloqueado", bloqueado_ate: bloqueio,
      mensagem: `Muitas tentativas com código errado. Nada foi enviado. Tente de novo depois das ${horaBrasilia(bloqueio)} (horário de Brasília).` }, cors) };
  }
  const autor = await autorDoCodigo(env, codigoDoPedido(request));
  if (autor) {
    await limite.limpar(chave);
    return { autor };
  }
  const falhas = await limite.registrarFalha(chave, deps.agora);
  if (falhas >= MAX_FALHAS) {
    const ate = await limite.bloqueadoAte(chave, deps.agora);
    return { resposta: json(429, { erro: "bloqueado", bloqueado_ate: ate,
      mensagem: `Código errado. Foram ${MAX_FALHAS} tentativas erradas: o envio ficou bloqueado até as ${horaBrasilia(ate)} (horário de Brasília). Nada foi enviado.` }, cors) };
  }
  const restantes = MAX_FALHAS - falhas;
  return { resposta: json(401, { erro: "codigo_invalido", tentativas_restantes: restantes,
    mensagem: `Código errado. Nada foi enviado. Restam ${restantes} tentativa(s) antes de um bloqueio de 15 minutos.` }, cors) };
}

// Decide UM post. Lança Recusa/ErroGitHub; quem chama transforma em resultado do lote.
async function decidirUm(env, deps, ctx, corpo) {
  const { banco, gh, autor, ip, semanas } = ctx;
  const { semana, post, acao } = corpo;
  const comentario = acao === "ajustar" ? corpo.comentario.trim() : "";
  if (!semanas.has(semana)) semanas.set(semana, await lerSemana(gh, semana));
  const semanaDados = semanas.get(semana);
  if (!semanaDados.agenda.posts.some((e) => e.numero === post)) {
    throw new Recusa(400, "Post inexistente", `O post ${post} não faz parte da semana ${semana}.`, "post_inexistente");
  }
  const [item] = await itensDe(gh, semana, semanaDados, [post]);
  const versaoAtual = await versaoPost(semana, item);
  if (acao === "aprovar" && corpo.versao !== versaoAtual) {
    throw new Recusa(409, "Conteúdo mudou",
      "Esta publicação mudou depois que a página foi aberta. Nada foi aprovado; recarregue a página e confira de novo.",
      "conteudo_mudou");
  }

  const agora = isoUtc(deps.agora);
  const nonce = novoNonce();
  const ultimo = await banco.ultimo(post);
  let commit = null;
  let mudouGitHub = false;

  if (acao === "aprovar") {
    ({ mudou: mudouGitHub, commit } = await atualizarAprovacao(gh, env, semana,
      (existente, segredo) => montarAprovacao(existente, semana, [item], [post], nonce, autor, agora, segredo),
      `aprovacao(${semana}): aprova o post ${post} pelo painel`));
  } else if (acao === "desfazer") {
    ({ mudou: mudouGitHub, commit } = await atualizarAprovacao(gh, env, semana,
      (existente, segredo) => removerDaAprovacao(existente, semana, post, nonce, autor, agora, segredo),
      `aprovacao(${semana}): desfaz a aprovação do post ${post} pelo painel`));
  } else {
    const repetido = ultimo && ultimo.acao === "ajustar" && ultimo.comentario === comentario &&
      ultimo.versao_conteudo === versaoAtual;
    if (!repetido) {
      // um post com ajuste pedido não pode continuar aprovado
      const r = await atualizarAprovacao(gh, env, semana,
        (existente, segredo) => removerDaAprovacao(existente, semana, post, nonce, autor, agora, segredo),
        `aprovacao(${semana}): post ${post} sai da aprovação (ajuste pedido pelo painel)`);
      const a = await registrarAjuste(gh, env, semana, post, comentario, nonce, agora,
        `ajuste(${semana}): pedido de ajuste no post ${post} pelo painel`);
      mudouGitHub = r.mudou || a.mudou;
      commit = a.commit ?? r.commit;
    }
  }

  const repetidoNoBanco = acao === "desfazer"
    ? !ultimo || ultimo.acao === "desfazer"
    : Boolean(ultimo && ultimo.acao === acao && ultimo.versao_conteudo === versaoAtual && ultimo.comentario === comentario);
  let eventoId = null;
  if (mudouGitHub || !repetidoNoBanco) {
    try {
      eventoId = await banco.registrar({ post, semana, acao, comentario, versao_conteudo: versaoAtual, autor,
        criado_em: agora, origem: "painel", commit_sha: commit, ip_hash: ip });
    } catch (erro) {
      throw new Recusa(500, "Falha no banco",
        `A decisão ${mudouGitHub ? "foi gravada no GitHub, mas não" : "não"} foi registrada no banco. Envie de novo. (${erro.message})`,
        "falha_banco");
    }
  }
  return {
    ok: true, status: 200, acao, semana, post, idempotente: eventoId === null && !mudouGitHub, evento_id: eventoId,
    commit, versao_conteudo: versaoAtual, estado: publico(await banco.ultimo(post)), novo_evento: eventoId !== null,
  };
}

function resultadoDeErro(corpo, erro) {
  const base = { ok: false, post: corpo.post, semana: corpo.semana, acao: corpo.acao };
  if (erro instanceof Recusa) return { ...base, status: erro.status, erro: erro.codigo, mensagem: erro.message };
  if (erro instanceof ErroGitHub) {
    return { ...base, status: 502, erro: "falha_github", mensagem: `Nada foi decidido neste post. Falha ao falar com o GitHub: ${erro.message}` };
  }
  return { ...base, status: 500, erro: "erro_inesperado", mensagem: `Nada foi decidido neste post. ${erro.message}` };
}

async function decidirLote(request, env, deps, autor, ip) {
  const bruto = await request.text();
  if (bruto.length > CORPO_MAX) throw new Recusa(413, "Pedido grande demais", "Pedido grande demais.", "corpo_grande");
  let corpo;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    throw new Recusa(400, "Pedido inválido", "JSON inválido.", "pedido_invalido");
  }
  const problema = validarLote(corpo);
  if (problema) throw new Recusa(400, "Pedido inválido", problema, "pedido_invalido");

  const banco = new Banco(env.DB);
  const gh = new GitHub(env, deps.fetch);
  const ctx = { banco, gh, autor, ip, semanas: new Map() };
  const resultados = [];
  for (const item of corpo.decisoes) {
    try {
      resultados.push(await decidirUm(env, deps, ctx, item));
    } catch (erro) {
      resultados.push(resultadoDeErro(item, erro));
    }
  }
  if (resultados.some((r) => r.novo_evento)) deps.waitUntil(exportarEventos(banco, gh).catch(() => {}));
  return { ok: resultados.every((r) => r.ok), autor, resultados };
}

export async function tratarApi(request, env, deps) {
  const url = new URL(request.url);
  if (request.headers.get("Origin") !== origemPermitida(env)) {
    return json(403, { erro: "origem_nao_permitida", mensagem: "Origem não permitida." });
  }
  const cors = cabecalhosCors(env);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (!env.DB || !segredoAprovacao(env)) {
    return json(500, { erro: "sem_configuracao", mensagem: "Worker sem banco ou sem segredos (ADR-011)." }, cors);
  }
  try {
    if (url.pathname === "/api/estado" && request.method === "GET") {
      const posts = {};
      for (const ev of await new Banco(env.DB).estado()) posts[ev.post] = publico(ev);
      return json(200, { posts }, cors);
    }
    if (url.pathname === "/api/decisoes" && request.method === "POST") {
      const ip = await ipHash(env, request);
      const acesso = await autenticar(request, env, deps, ip, cors);
      if (acesso.resposta) return acesso.resposta;
      return json(200, await decidirLote(request, env, deps, acesso.autor, ip), cors);
    }
    return json(404, { erro: "rota_inexistente", mensagem: "Rota inexistente." }, cors);
  } catch (erro) {
    if (erro instanceof Recusa) return json(erro.status, { erro: erro.codigo, mensagem: erro.message }, cors);
    return json(500, { erro: "erro_inesperado", mensagem: `Nada foi decidido. ${erro.message}` }, cors);
  }
}
