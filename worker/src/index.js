// Worker de aprovação da Pastoral do Dízimo (ADR-009, arquitetura §1.1 e §5). Sem domínio: *.workers.dev.
//
// GET  /a?s&a&p&e&n&v&h  valida o link (HMAC LINK_HMAC_SECRET + expiração) e só MOSTRA a confirmação
//                         (ou o formulário de ajuste). Nada é gravado em GET: o pré-carregamento de links
//                         do Gmail não aprova nada.
// POST /a                 valida de novo e:
//   aprovar_tudo / aprovar_post → lê agenda.json, posts.json e as artes da semana pela Contents API,
//     calcula os sha256 do ADR-008, confere a versão assinada no link, monta aprovacao.json canônico,
//     assina com APROVACAO_HMAC_SECRET e commita (idempotente: aprovar de novo não grava).
//   ajustar_post → grava content/semanas/<semana>/ajuste-<n>.json e dispara repository_dispatch
//     (evento ajustar_post).
// Segredos (wrangler secret put): LINK_HMAC_SECRET, APROVACAO_HMAC_SECRET, GH_PAT_WORKER.
//
// Painel (ADR-011/012): /api/* (painel.js: estado público; envio com o código CODIGO_APROVADOR e limite
// de tentativas; D1 em env.DB) e cron diário de backup do D1. A antiga rota /p/<código> foi desativada (404).
// Decisões feitas pelo link do e-mail também viram eventos no D1 (origem "email"), se houver banco.

import { Recusa, TEXTO_MAX, atualizarAprovacao, isoUtc, itensDe, lerSemana, registrarAjuste } from "./acoes.js";
import { exportarEventos } from "./backup.js";
import { Banco } from "./banco.js";
import { ErroGitHub, GitHub } from "./github.js";
import { montarAprovacao, motivoLinkInvalido, removerDaAprovacao, versao, versaoPost } from "./nucleo.js";
import { tratarApi } from "./painel.js";

const CAMPOS = ["s", "a", "p", "e", "n", "v", "h"];

// ---------- HTML ----------

const esc = (t) =>
  String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const CSS = `body{margin:0;background:#F3F2EE;color:#1E1B1B;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:560px;margin:0 auto;padding:24px 16px}
.cartao{background:#fff;border:1px solid #ddd;border-top:4px solid #A3121C;border-radius:8px;padding:20px}
h1{font-size:21px;margin:0 0 8px;color:#7E0F17} p{margin:8px 0} .suave{color:#5F5A57;font-size:14px}
button{background:#A3121C;color:#fff;border:0;border-radius:6px;padding:12px 18px;font-size:16px;cursor:pointer;width:100%}
textarea{width:100%;box-sizing:border-box;min-height:140px;font:inherit;padding:8px;border:1px solid #bbb;border-radius:6px}
a{color:#A3121C}`;

function pagina(status, titulo, corpo) {
  const html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>${esc(titulo)} · Pastoral do Dízimo</title><style>${CSS}</style></head>
<body><main><div class="cartao"><h1>${esc(titulo)}</h1>${corpo}</div>
<p class="suave">Pastoral do Dízimo · Arquidiocese de Florianópolis</p></main></body></html>`;
  return new Response(html, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
      "X-Robots-Tag": "noindex",
    },
  });
}

const camposOcultos = (p) =>
  CAMPOS.map((c) => `<input type="hidden" name="${c}" value="${esc(p[c] ?? "")}">`).join("");

function linkPrevia(env, semana) {
  const base = (env.PREVIA_BASE_URL || "").replace(/\/?$/, "/");
  return base.startsWith("https://") ? `<p><a href="${esc(`${base}semanas/${semana}/`)}">Abrir a prévia da semana</a></p>` : "";
}

function descricao(p) {
  return p.a === "aprovar_tudo" ? `os posts da semana ${p.s}` : `o post ${p.p} da semana ${p.s}`;
}

function paginaConfirmacao(env, p) {
  if (p.a === "ajustar_post") return formularioAjuste(env, p, 200);
  return pagina(200, `Aprovar ${descricao(p)}?`,
    `<p>Ao confirmar, a aprovação é registrada no repositório com assinatura. Só o que está na prévia
     (textos e artes exatamente como estão agora) poderá ser publicado, na data agendada.</p>
     ${linkPrevia(env, p.s)}
     <form method="post" action="/a">${camposOcultos(p)}<button type="submit">Confirmar aprovação</button></form>`);
}

function formularioAjuste(env, p, status, aviso = "") {
  return pagina(status, `Pedir ajuste no post ${p.p}`,
    `${aviso ? `<p><b>${esc(aviso)}</b></p>` : ""}
     <p>Descreva o que mudar (imagem e trecho, se possível). O post será refeito e um novo e-mail chegará.</p>
     <p class="suave">O repositório é público: não escreva dados pessoais.</p>
     ${linkPrevia(env, p.s)}
     <form method="post" action="/a">${camposOcultos(p)}
     <textarea name="texto" maxlength="${TEXTO_MAX}" required></textarea>
     <p><button type="submit">Enviar pedido de ajuste</button></p></form>`);
}

// ---------- ações do link (a lógica mora em acoes.js, compartilhada com o painel) ----------

// Registra no D1 as decisões feitas pelo link do e-mail (se o banco existir). Falha aqui não desfaz o
// commit já feito: devolve um aviso para a página mostrar.
async function registrarLink(env, deps, gh, eventos) {
  if (!env.DB || !eventos.length) return "";
  try {
    const banco = new Banco(env.DB);
    for (const ev of eventos) await banco.registrar({ ...ev, origem: "email", autor: env.APROVADO_POR || "Diogo" });
    deps.waitUntil(exportarEventos(banco, gh).catch(() => {}));
    return "";
  } catch (erro) {
    return `Aviso: a decisão foi gravada no repositório, mas não no banco (${erro.message}).`;
  }
}

async function aprovar(env, p, gh, agora, deps) {
  const semanaDados = await lerSemana(gh, p.s);
  const itens = await itensDe(gh, p.s, semanaDados);
  if ((await versao(p.s, itens)) !== p.v) {
    throw new Recusa(409, "Conteúdo mudou",
      "O conteúdo da semana mudou depois do e-mail. Nada foi aprovado; use os links do e-mail mais recente.");
  }
  const alvo = p.a === "aprovar_tudo" ? itens.map((i) => i.numero) : [Number(p.p)];
  if (!alvo.every((n) => itens.some((i) => i.numero === n))) {
    throw new Recusa(400, "Post inexistente", `O post ${p.p} não faz parte da semana ${p.s}.`);
  }
  const quando = isoUtc(agora);
  const r = await atualizarAprovacao(gh, env, p.s,
    (existente, segredo) => montarAprovacao(existente, p.s, itens, alvo, p.n, env.APROVADO_POR || "Diogo", quando, segredo),
    `aprovacao(${p.s}): aprova post(s) ${alvo.join(", ")} pelo link do e-mail`);
  let aviso = "";
  if (r.mudou) {
    const eventos = [];
    for (const n of alvo) {
      const item = itens.find((i) => i.numero === n);
      eventos.push({ post: n, semana: p.s, acao: "aprovar", comentario: "",
        versao_conteudo: await versaoPost(p.s, item), criado_em: quando, commit_sha: r.commit });
    }
    aviso = await registrarLink(env, deps, gh, eventos);
  }
  return { mudou: r.mudou, alvo, aviso };
}

async function ajustar(env, p, gh, agora, texto, deps) {
  const semanaDados = await lerSemana(gh, p.s);
  const numero = Number(p.p);
  if (!semanaDados.agenda.posts.some((e) => e.numero === numero)) {
    throw new Recusa(400, "Post inexistente", `O post ${p.p} não faz parte da semana ${p.s}.`);
  }
  const quando = isoUtc(agora);
  const r = await registrarAjuste(gh, env, p.s, numero, texto, p.n, quando,
    `ajuste(${p.s}): pedido de ajuste no post ${numero} pelo link do e-mail`);
  if (r.mudou) {
    // um post com ajuste pedido não pode continuar aprovado (mesma regra do painel)
    await atualizarAprovacao(gh, env, p.s,
      (existente, segredo) => removerDaAprovacao(existente, p.s, numero, p.n, env.APROVADO_POR || "Diogo", quando, segredo),
      `aprovacao(${p.s}): post ${numero} sai da aprovação (ajuste pedido pelo link do e-mail)`);
  }
  let aviso = "";
  if (r.mudou && env.DB) {
    const [item] = await itensDe(gh, p.s, semanaDados, [numero]);
    aviso = await registrarLink(env, deps, gh, [{ post: numero, semana: p.s, acao: "ajustar", comentario: texto,
      versao_conteudo: await versaoPost(p.s, item), criado_em: quando, commit_sha: r.commit }]);
  }
  return { ...r, aviso };
}

const avisoHtml = (aviso) => (aviso ? `<p class="suave">${esc(aviso)}</p>` : "");

// ---------- roteamento ----------

export async function tratar(request, env, deps = {}) {
  const fetchFn = deps.fetch ?? ((...a) => fetch(...a));
  const agora = (deps.agora ?? (() => new Date()))();
  const waitUntil = deps.waitUntil ?? (() => {});
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return tratarApi(request, env, { fetch: fetchFn, agora, waitUntil });
  if (url.pathname !== "/a") return pagina(404, "Página não encontrada", "<p>Use o link do e-mail.</p>");
  if (request.method !== "GET" && request.method !== "POST") {
    return pagina(405, "Método não permitido", "<p>Use o link do e-mail.</p>");
  }
  const segredoLink = (env.LINK_HMAC_SECRET || "").trim();
  if (!segredoLink || !(env.APROVACAO_HMAC_SECRET || "").trim()) {
    return pagina(500, "Worker sem configuração", "<p>Os segredos ainda não foram cadastrados (ADR-009).</p>");
  }

  let p, form;
  if (request.method === "GET") {
    p = Object.fromEntries(CAMPOS.map((c) => [c, url.searchParams.get(c)]));
  } else {
    form = await request.formData();
    p = Object.fromEntries(CAMPOS.map((c) => [c, form.get(c)]));
  }
  const motivo = await motivoLinkInvalido(segredoLink, p, Math.floor(agora.getTime() / 1000));
  if (motivo) {
    return pagina(403, "Link recusado", `<p>${esc(motivo)}. Nada foi alterado.</p><p class="suave">Use os links do e-mail mais recente.</p>`);
  }
  if (request.method === "GET") return paginaConfirmacao(env, p);

  try {
    const gh = new GitHub(env, fetchFn);
    if (p.a === "ajustar_post") {
      const texto = String(form.get("texto") ?? "").trim();
      if (!texto || texto.length > TEXTO_MAX) {
        return formularioAjuste(env, p, 400, `Escreva o ajuste (até ${TEXTO_MAX} caracteres).`);
      }
      const r = await ajustar(env, p, gh, agora, texto, { waitUntil });
      return pagina(200, r.mudou ? "Pedido de ajuste registrado" : "Pedido de ajuste já registrado",
        `<p>Post ${esc(p.p)} da semana ${esc(p.s)}:</p><blockquote>${esc(r.texto)}</blockquote>
         <p>O post será refeito e um novo e-mail de aprovação chegará.</p>${avisoHtml(r.aviso)}`);
    }
    const r = await aprovar(env, p, gh, agora, { waitUntil });
    const quais = r.alvo.length > 1 ? `Posts ${r.alvo.join(", ")}` : `Post ${r.alvo[0]}`;
    return r.mudou
      ? pagina(200, "Aprovado", `<p>${quais} da semana ${esc(p.s)} aprovado(s). Serão publicados na data agendada.</p>${linkPrevia(env, p.s)}${avisoHtml(r.aviso)}`)
      : pagina(200, "Nada a fazer", `<p>${quais} da semana ${esc(p.s)} já estava aprovado. Nenhum registro novo foi feito.</p>`);
  } catch (erro) {
    if (erro instanceof Recusa) return pagina(erro.status, erro.titulo, `<p>${esc(erro.message)}</p>`);
    if (erro instanceof ErroGitHub) {
      return pagina(502, "Falha ao falar com o GitHub", `<p>Nada foi aprovado. Tente de novo em alguns minutos.</p><p class="suave">${esc(erro.message)}</p>`);
    }
    return pagina(500, "Erro inesperado", `<p>Nada foi aprovado.</p><p class="suave">${esc(erro.message)}</p>`);
  }
}

// Backup diário (cron do wrangler.toml): D1 → content/aprovacoes/eventos.jsonl.
export async function backupAgendado(env, deps = {}) {
  if (!env.DB) return { mudou: false, eventos: 0, commit: null };
  const fetchFn = deps.fetch ?? ((...a) => fetch(...a));
  return exportarEventos(new Banco(env.DB), new GitHub(env, fetchFn));
}

export default {
  fetch(request, env, ctx) {
    return tratar(request, env, { waitUntil: (p) => ctx.waitUntil(p) });
  },
  scheduled(_evento, env, ctx) {
    ctx.waitUntil(backupAgendado(env));
  },
};
