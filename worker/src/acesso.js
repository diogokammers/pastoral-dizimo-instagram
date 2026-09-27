// Acesso ao painel (ADR-011): código secreto (capability) por pessoa, CORS restrito e link curto.
// Os códigos são segredos do Worker (wrangler secret put): CODIGO_PADRE e, se um dia existir, CODIGO_DIOGO.

import { utf8 } from "./nucleo.js";

// Segredo → autor gravado nos eventos. Para um novo aprovador, basta um novo par aqui + o secret.
export const CODIGOS = [
  ["CODIGO_PADRE", "Padre"],
  ["CODIGO_DIOGO", "Diogo"],
];
export const FORMATO_CODIGO = /^[A-Za-z0-9_-]{32,128}$/;
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

// Autor do código, ou null. Confere TODOS os códigos cadastrados (sem atalho) comparando os sha256.
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
  const m = /^Bearer ([A-Za-z0-9_-]{1,200})$/.exec(request.headers.get("Authorization") ?? "");
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

// Link curto /p/<código> → página do Pages com o código no fragmento (#c=…): o fragmento não vai ao
// servidor do Pages, nem a logs, nem ao Referer. O código não é validado aqui (não vira oráculo).
export function redirecionarCurto(env, url) {
  const m = /^\/p\/([A-Za-z0-9_-]{32,128})\/?$/.exec(url.pathname);
  const pagina = env.PAGINA_URL || "";
  if (!m || !pagina.startsWith("https://")) return null;
  return new Response(null, {
    status: 302,
    headers: {
      Location: `${pagina}#c=${m[1]}`,
      "Cache-Control": "no-store",
      "Referrer-Policy": "no-referrer",
      "X-Robots-Tag": "noindex",
    },
  });
}
