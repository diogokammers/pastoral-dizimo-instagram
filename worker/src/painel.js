// API do painel de aprovação (ADR-011), chamada pela página do GitHub Pages (site/aprovacao/).
//
// OPTIONS /api/*       preflight CORS (só o origin permitido).
// GET  /api/estado     último evento de cada post (exige código de acesso).
// POST /api/decisao    { semana, post, acao: aprovar|ajustar|desfazer, versao, comentario }
//   aprovar  → confere a versão do post (hash do conteúdo atual no GitHub) e grava aprovacao.json
//              assinado, igual ao link do e-mail (ADR-009): o publicar.py o publica na data agendada.
//   ajustar  → tira o post do aprovacao.json (se estava), grava ajuste-<n>.json e dispara repository_dispatch.
//   desfazer → tira o post do aprovacao.json assinado (reassina): o portão não o publica mais.
// Todo evento vai para o D1 (append-only) e depois para content/aprovacoes/eventos.jsonl (backup).
//
// Código de acesso: header "Authorization: Bearer <código>" (nunca na URL). Origin fora da lista → 403.

import { autorDoCodigo, cabecalhosCors, codigoDoPedido, origemPermitida } from "./acesso.js";
import {
  Recusa, TEXTO_MAX, atualizarAprovacao, isoUtc, itensDe, lerSemana, novoNonce, registrarAjuste, segredoAprovacao,
} from "./acoes.js";
import { exportarEventos } from "./backup.js";
import { Banco } from "./banco.js";
import { ErroGitHub, GitHub } from "./github.js";
import { hmacHex, montarAprovacao, removerDaAprovacao, utf8, versaoPost } from "./nucleo.js";

const ACOES_PAINEL = ["aprovar", "ajustar", "desfazer"];
const CORPO_MAX = 10000;

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

function validar(corpo) {
  if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return "corpo inválido";
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

// HMAC do IP (16 hex), só para auditoria no D1; não vai para o backup público.
async function ipHash(env, request) {
  const ip = request.headers.get("CF-Connecting-IP");
  return ip ? (await hmacHex(segredoAprovacao(env), utf8(`ip-v1\n${ip}`))).slice(0, 16) : null;
}

async function decidir(request, env, deps, autor) {
  const bruto = await request.text();
  if (bruto.length > CORPO_MAX) throw new Recusa(413, "Pedido grande demais", "Pedido grande demais.", "corpo_grande");
  let corpo;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    throw new Recusa(400, "Pedido inválido", "JSON inválido.", "pedido_invalido");
  }
  const problema = validar(corpo);
  if (problema) throw new Recusa(400, "Pedido inválido", problema, "pedido_invalido");
  const { semana, post, acao } = corpo;
  const comentario = acao === "ajustar" ? corpo.comentario.trim() : "";

  const banco = new Banco(env.DB);
  const gh = new GitHub(env, deps.fetch);
  const semanaDados = await lerSemana(gh, semana);
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
      `aprovacao(${semana}): ${autor} aprova o post ${post} pelo painel`));
  } else if (acao === "desfazer") {
    ({ mudou: mudouGitHub, commit } = await atualizarAprovacao(gh, env, semana,
      (existente, segredo) => removerDaAprovacao(existente, semana, post, nonce, autor, agora, segredo),
      `aprovacao(${semana}): ${autor} desfaz a aprovação do post ${post} pelo painel`));
  } else {
    const repetido = ultimo && ultimo.acao === "ajustar" && ultimo.comentario === comentario &&
      ultimo.versao_conteudo === versaoAtual;
    if (!repetido) {
      // um post com ajuste pedido não pode continuar aprovado
      const r = await atualizarAprovacao(gh, env, semana,
        (existente, segredo) => removerDaAprovacao(existente, semana, post, nonce, autor, agora, segredo),
        `aprovacao(${semana}): post ${post} sai da aprovação (ajuste pedido por ${autor})`);
      const a = await registrarAjuste(gh, env, semana, post, comentario, nonce, agora,
        `ajuste(${semana}): ${autor} pede ajuste no post ${post} pelo painel`);
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
        criado_em: agora, origem: "painel", commit_sha: commit, ip_hash: await ipHash(env, request) });
    } catch (erro) {
      throw new Recusa(500, "Falha no banco",
        `A decisão ${mudouGitHub ? "foi gravada no GitHub, mas não" : "não"} foi registrada no banco. Toque de novo. (${erro.message})`,
        "falha_banco");
    }
    deps.waitUntil(exportarEventos(banco, gh).catch(() => {}));
  }
  return {
    ok: true, acao, semana, post, idempotente: eventoId === null && !mudouGitHub, evento_id: eventoId,
    commit, versao_conteudo: versaoAtual, estado: publico(await banco.ultimo(post)),
  };
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
  const autor = await autorDoCodigo(env, codigoDoPedido(request));
  if (!autor) return json(401, { erro: "codigo_invalido", mensagem: "Código de acesso inválido." }, cors);

  try {
    if (url.pathname === "/api/estado" && request.method === "GET") {
      const posts = {};
      for (const ev of await new Banco(env.DB).estado()) posts[ev.post] = publico(ev);
      return json(200, { autor, posts }, cors);
    }
    if (url.pathname === "/api/decisao" && request.method === "POST") {
      return json(200, await decidir(request, env, deps, autor), cors);
    }
    return json(404, { erro: "rota_inexistente", mensagem: "Rota inexistente." }, cors);
  } catch (erro) {
    if (erro instanceof Recusa) return json(erro.status, { erro: erro.codigo, mensagem: erro.message }, cors);
    if (erro instanceof ErroGitHub) {
      return json(502, { erro: "falha_github", mensagem: `Nada foi decidido. Falha ao falar com o GitHub: ${erro.message}` }, cors);
    }
    return json(500, { erro: "erro_inesperado", mensagem: `Nada foi decidido. ${erro.message}` }, cors);
  }
}
