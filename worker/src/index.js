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

import { ConflitoGitHub, ErroGitHub, GitHub } from "./github.js";
import { itensSemana, montarAprovacao, motivoLinkInvalido, assinaturaValida, versao } from "./nucleo.js";

const CAMPOS = ["s", "a", "p", "e", "n", "v", "h"];
const TEXTO_MAX = 2000;

class Recusa extends Error {
  constructor(status, titulo, mensagem) {
    super(mensagem);
    this.status = status;
    this.titulo = titulo;
  }
}

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

// ---------- ações ----------

const isoUtc = (d) => d.toISOString().slice(0, 19) + "+00:00";

async function aprovar(env, p, gh, agora) {
  const base = `content/semanas/${p.s}`;
  const agenda = await gh.lerJson(`${base}/agenda.json`);
  const posts = await gh.lerJson(`${base}/posts.json`);
  if (agenda.semana !== p.s) throw new Recusa(500, "Agenda inconsistente", "agenda.json é de outra semana.");
  const itens = await itensSemana(agenda, posts, (arquivo) => gh.lerBytes(`site/midia/${p.s}/${arquivo}`));
  if ((await versao(p.s, itens)) !== p.v) {
    throw new Recusa(409, "Conteúdo mudou",
      "O conteúdo da semana mudou depois do e-mail. Nada foi aprovado; use os links do e-mail mais recente.");
  }
  const alvo = p.a === "aprovar_tudo" ? itens.map((i) => i.numero) : [Number(p.p)];
  if (!alvo.every((n) => itens.some((i) => i.numero === n))) {
    throw new Recusa(400, "Post inexistente", `O post ${p.p} não faz parte da semana ${p.s}.`);
  }
  const segredo = env.APROVACAO_HMAC_SECRET.trim();
  const caminho = `${base}/aprovacao.json`;
  for (let tentativa = 1; ; tentativa++) {
    const atual = await gh.lerJsonComSha(caminho);
    if (atual && (atual.dados.semana !== p.s || !(await assinaturaValida(atual.dados, segredo)))) {
      throw new Recusa(500, "Aprovação existente inválida",
        "O aprovacao.json atual não tem assinatura válida. Nada foi gravado; avise o Diogo.");
    }
    const { dados, mudou } = await montarAprovacao(atual?.dados ?? null, p.s, itens, alvo, p.n,
      env.APROVADO_POR || "Diogo", isoUtc(agora), segredo);
    if (!mudou) return { mudou: false, alvo };
    try {
      await gh.gravar(caminho, JSON.stringify(dados, null, 2) + "\n",
        `aprovacao(${p.s}): aprova post(s) ${alvo.join(", ")} pelo link do e-mail`, atual?.sha);
      return { mudou: true, alvo };
    } catch (erro) {
      if (erro instanceof ConflitoGitHub && tentativa < 3) continue;
      throw erro;
    }
  }
}

async function ajustar(env, p, gh, agora, texto) {
  const base = `content/semanas/${p.s}`;
  const agenda = await gh.lerJson(`${base}/agenda.json`);
  const numero = Number(p.p);
  if (!agenda.posts.some((e) => e.numero === numero)) {
    throw new Recusa(400, "Post inexistente", `O post ${p.p} não faz parte da semana ${p.s}.`);
  }
  const caminho = `${base}/ajuste-${numero}.json`;
  for (let tentativa = 1; ; tentativa++) {
    const atual = await gh.lerJsonComSha(caminho);
    if (atual && atual.dados.nonce === p.n) return { mudou: false, texto: atual.dados.texto };
    const dados = { semana: p.s, post: numero, texto, pedido_em: isoUtc(agora), nonce: p.n };
    try {
      await gh.gravar(caminho, JSON.stringify(dados, null, 2) + "\n",
        `ajuste(${p.s}): pedido de ajuste no post ${numero} pelo link do e-mail`, atual?.sha);
      break;
    } catch (erro) {
      if (erro instanceof ConflitoGitHub && tentativa < 3) continue;
      throw erro;
    }
  }
  await gh.disparar("ajustar_post", { semana: p.s, post: numero });
  return { mudou: true, texto };
}

// ---------- roteamento ----------

export async function tratar(request, env, deps = {}) {
  const fetchFn = deps.fetch ?? ((...a) => fetch(...a));
  const agora = (deps.agora ?? (() => new Date()))();
  const url = new URL(request.url);
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
      const r = await ajustar(env, p, gh, agora, texto);
      return pagina(200, r.mudou ? "Pedido de ajuste registrado" : "Pedido de ajuste já registrado",
        `<p>Post ${esc(p.p)} da semana ${esc(p.s)}:</p><blockquote>${esc(r.texto)}</blockquote>
         <p>O post será refeito e um novo e-mail de aprovação chegará.</p>`);
    }
    const r = await aprovar(env, p, gh, agora);
    const quais = r.alvo.length > 1 ? `Posts ${r.alvo.join(", ")}` : `Post ${r.alvo[0]}`;
    return r.mudou
      ? pagina(200, "Aprovado", `<p>${quais} da semana ${esc(p.s)} aprovado(s). Serão publicados na data agendada.</p>${linkPrevia(env, p.s)}`)
      : pagina(200, "Nada a fazer", `<p>${quais} da semana ${esc(p.s)} já estava aprovado. Nenhum registro novo foi feito.</p>`);
  } catch (erro) {
    if (erro instanceof Recusa) return pagina(erro.status, erro.titulo, `<p>${esc(erro.message)}</p>`);
    if (erro instanceof ErroGitHub) {
      return pagina(502, "Falha ao falar com o GitHub", `<p>Nada foi aprovado. Tente de novo em alguns minutos.</p><p class="suave">${esc(erro.message)}</p>`);
    }
    return pagina(500, "Erro inesperado", `<p>Nada foi aprovado.</p><p class="suave">${esc(erro.message)}</p>`);
  }
}

export default {
  fetch(request, env) {
    return tratar(request, env);
  },
};
