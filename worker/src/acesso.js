// Acesso ao painel (ADR-012): código de envio, CORS restrito e link curto sem código.
// O código fica SÓ como segredo do Worker (wrangler secret put CODIGO_APROVADOR, via stdin) — nunca no
// HTML, no JS da página nem no repositório. Como pode ser curto, o Worker limita as tentativas (limite.js).

import { utf8 } from "./nucleo.js";

// Segredo → autor gravado nos eventos. Para outro aprovador, basta um novo par aqui + o secret.
export const CODIGOS = [["CODIGO_APROVADOR", "Aprovador"]];
// Qualquer ASCII visível, 1 a 128 caracteres (o código pode ser curto; a proteção é o limite de tentativas).
export const FORMATO_CODIGO = /^[\x21-\x7e]{1,128}$/;
export const ORIGEM_PADRAO = "https://diogokammers.github.io";

async function resumo(texto) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", utf8(texto)));
}

// Compara dois resumos de 32 bytes sem sair antes do fim (tempo constante).
function iguais(a, b) {
  let dif = a.length ^ b.length;
  for (let i = 0; i < a.length; i++) dif |= a[i] ^ b[i];
  return dif === 0;
}

// Autor do código, ou null. Sensível a maiúsculas/minúsculas; confere TODOS os códigos cadastrados
// (sem atalho) comparando os sha256, para o tempo não depender de onde a diferença está.
export async function autorDoCodigo(env, recebido) {
  if (typeof recebido !== "string" || !FORMATO_CODIGO.test(recebido)) return null;
  const h = await resumo(recebido);
  let autor = null;
  for (const [segredo, nome] of CODIGOS) {
    const esperado = String(env[segredo] ?? "").trim();
    if (!esperado) continue;
    if (iguais(h, await resumo(esperado)) && autor === null) autor = nome;
  }
  return autor;
}

export function codigoDoPedido(request) {
  const m = /^Bearer ([\x21-\x7e]{1,128})$/.exec(request.headers.get("Authorization") ?? "");
  return m ? m[1] : null;
}

export const origemPermitida = (env) => (env.ORIGEM_PERMITIDA || ORIGEM_PADRAO).replace(/\/$/, "");

export function cabecalhosCors(env) {
  return {
    "Access-Control-Allow-Origin": origemPermitida(env),
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

// Link curto: a raiz ("/") redireciona para a página do painel. Não leva código nenhum.
export function redirecionarPagina(env, url) {
  const pagina = env.PAGINA_URL || "";
  if (url.pathname !== "/" || !pagina.startsWith("https://")) return null;
  return new Response(null, {
    status: 302,
    headers: { Location: pagina, "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex" },
  });
}
