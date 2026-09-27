// Núcleo determinístico do Worker de aprovação (ADR-009). Espelho exato de src/pastoral/aprovacao.py
// e de publicar.py (ADR-008). Só Web APIs (crypto.subtle, TextEncoder, atob/btoa): roda igual no
// Cloudflare Workers e no Node (testes). Qualquer mudança aqui precisa passar nos vetores do Python.

const codificador = new TextEncoder();
const decodificador = new TextDecoder("utf-8", { fatal: true });

export const ACOES = ["aprovar_tudo", "aprovar_post", "ajustar_post"];
const PREFIXO_LINK = "pastoral-link-v1";
const CAMPOS_LINK = ["s", "a", "p", "e", "n", "v"];
const FORMATOS = {
  s: /^\d{4}-W\d{2}$/,
  a: /^(aprovar_tudo|aprovar_post|ajustar_post)$/,
  p: /^\d{1,4}$/,
  e: /^\d{1,12}$/,
  n: /^[0-9a-f]{16,64}$/,
  v: /^[0-9a-f]{32}$/,
  h: /^[0-9a-f]{64}$/,
};

// ---------- bytes ----------

export const utf8 = (texto) => codificador.encode(texto);
export const deUtf8 = (bytes) => decodificador.decode(bytes);

export function paraHex(bytes) {
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}

function deHex(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return bytes;
}

export function paraBase64(bytes) {
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

export function deBase64(b64) {
  const bin = atob(b64.replace(/\s/g, ""));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

// ---------- JSON canônico (ADR-008 §4) ----------

// Python ordena chaves por ponto de código; o sort padrão do JS usa unidades UTF-16 (difere em astrais).
function compararPontosDeCodigo(a, b) {
  const A = Array.from(a), B = Array.from(b);
  for (let i = 0; i < Math.min(A.length, B.length); i++) {
    const d = A[i].codePointAt(0) - B[i].codePointAt(0);
    if (d !== 0) return d;
  }
  return A.length - B.length;
}

// Igual a json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False).
export function canonicoTexto(valor) {
  if (valor === null) return "null";
  if (typeof valor === "boolean") return valor ? "true" : "false";
  if (typeof valor === "number") {
    if (!Number.isSafeInteger(valor)) throw new Error("JSON canônico: só números inteiros");
    return String(valor);
  }
  if (typeof valor === "string") return JSON.stringify(valor);
  if (Array.isArray(valor)) return "[" + valor.map(canonicoTexto).join(",") + "]";
  if (typeof valor === "object") {
    const chaves = Object.keys(valor).sort(compararPontosDeCodigo);
    return "{" + chaves.map((k) => JSON.stringify(k) + ":" + canonicoTexto(valor[k])).join(",") + "}";
  }
  throw new Error(`JSON canônico: tipo não suportado (${typeof valor})`);
}

export const canonico = (valor) => utf8(canonicoTexto(valor));

// ---------- hashes e HMAC ----------

export async function sha256Hex(bytes) {
  return paraHex(await crypto.subtle.digest("SHA-256", bytes));
}

async function chaveHmac(segredo) {
  if (!segredo) throw new Error("segredo HMAC vazio");
  return crypto.subtle.importKey("raw", utf8(segredo), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export async function hmacHex(segredo, bytes) {
  return paraHex(await crypto.subtle.sign("HMAC", await chaveHmac(segredo), bytes));
}

// Comparação em tempo constante: crypto.subtle.verify recalcula o HMAC e compara internamente.
export async function hmacConfere(segredo, bytes, assinaturaHex) {
  if (!segredo || typeof assinaturaHex !== "string" || !FORMATOS.h.test(assinaturaHex)) return false;
  return crypto.subtle.verify("HMAC", await chaveHmac(segredo), deHex(assinaturaHex), bytes);
}

function semAssinatura(dados) {
  const copia = { ...dados };
  delete copia.assinatura;
  return copia;
}

export const assinar = (dados, segredo) => hmacHex(segredo, canonico(semAssinatura(dados)));
export const assinaturaValida = (dados, segredo) =>
  hmacConfere(segredo, canonico(semAssinatura(dados)), dados?.assinatura);

// ---------- textos que entram no hash (publicar.texto_legenda / texto_alt) ----------

// Mesmo conjunto de str.isspace() do Python (o trim() do JS inclui U+FEFF e exclui U+001C–U+001F e U+0085).
const ESPACO_PY = "[\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";
const BORDAS = new RegExp(`^${ESPACO_PY}+|${ESPACO_PY}+$`, "gu");
export const stripPython = (texto) => texto.replace(BORDAS, "");

export function textoLegenda(post) {
  const legenda = stripPython(post.legenda ?? "");
  const hashtags = (post.hashtags ?? []).join(" ");
  return hashtags ? `${legenda}\n\n${hashtags}` : legenda;
}

export const textoAlt = (post) => (post.slides ?? []).map((s) => s.alt_text ?? "").join("\n");

// ---------- itens da semana e versão ----------

export async function itensSemana(agenda, postsDados, lerArte) {
  const porNumero = new Map(postsDados.posts.map((p) => [p.numero, p]));
  const entradas = [...agenda.posts].sort((a, b) => a.numero - b.numero);
  const itens = [];
  for (const entrada of entradas) {
    const post = porNumero.get(entrada.numero);
    if (!post) throw new Error(`post ${entrada.numero} da agenda não existe em posts.json`);
    if (entrada.artes.length !== post.slides.length) {
      throw new Error(`post ${entrada.numero}: número de artes não bate com os slides`);
    }
    const artes = [];
    for (const arquivo of entrada.artes) artes.push({ arquivo, sha256: await sha256Hex(await lerArte(arquivo)) });
    itens.push({
      numero: entrada.numero,
      agendado_para: entrada.agendado_para,
      legenda_sha256: await sha256Hex(utf8(textoLegenda(post))),
      alt_text_sha256: await sha256Hex(utf8(textoAlt(post))),
      artes,
    });
  }
  return itens;
}

export async function versao(semana, itens) {
  return (await sha256Hex(canonico({ semana, posts: itens }))).slice(0, 32);
}

// Versão de UM post (painel, ADR-011) — espelho de aprovacao.versao_post.
export async function versaoPost(semana, item) {
  return (await sha256Hex(canonico({ semana, post: item }))).slice(0, 32);
}

// ---------- links assinados ----------

const mensagemLink = (params) => utf8([PREFIXO_LINK, ...CAMPOS_LINK.map((c) => String(params[c] ?? ""))].join("\n"));

export async function assinarLink(segredo, params) {
  return hmacHex(segredo, mensagemLink(params));
}

// null se o link vale; senão o motivo (mesmas frases do Python).
export async function motivoLinkInvalido(segredo, params, agoraEpoch) {
  if (!segredo) return "segredo ausente";
  for (const [campo, formato] of Object.entries(FORMATOS)) {
    const valor = params[campo];
    if (campo === "p" && params.a === "aprovar_tudo") {
      if (valor !== "") return "link malformado";
      continue;
    }
    if (typeof valor !== "string" || !formato.test(valor)) return "link malformado";
  }
  if (!(await hmacConfere(segredo, mensagemLink(params), params.h))) return "assinatura inválida";
  if (Number(params.e) <= agoraEpoch) return "link expirado";
  return null;
}

// ---------- aprovacao.json ----------

// Junta os posts `alvo` à aprovação existente. Idempotente: link já usado (mesmo nonce) ou posts já
// aprovados com o mesmo conteúdo → { dados: existente, mudou: false }.
export async function montarAprovacao(existente, semana, itens, alvo, nonce, aprovadoPor, aprovadoEm, segredo) {
  const disponiveis = new Map(itens.map((i) => [i.numero, i]));
  const faltando = alvo.filter((n) => !disponiveis.has(n));
  if (faltando.length || !alvo.length) throw new Error(`post(s) fora da semana: ${faltando.join(", ") || "nenhum"}`);
  const aprovados = new Map((existente?.posts ?? []).map((i) => [i.numero, i]));
  if (existente && existente.nonce === nonce) return { dados: existente, mudou: false };
  const igual = (a, b) => a !== undefined && canonicoTexto(a) === canonicoTexto(b);
  if (alvo.every((n) => igual(aprovados.get(n), disponiveis.get(n)))) return { dados: existente, mudou: false };
  for (const n of alvo) aprovados.set(n, disponiveis.get(n));
  const dados = {
    semana,
    aprovado_por: aprovadoPor,
    aprovado_em: aprovadoEm,
    nonce,
    posts: [...aprovados.keys()].sort((a, b) => a - b).map((n) => aprovados.get(n)),
  };
  dados.assinatura = await assinar(dados, segredo);
  return { dados, mudou: true };
}

// Tira o post `numero` da aprovação e reassina (desfazer no painel, ADR-011) — espelho de
// aprovacao.remover_da_aprovacao. Sem o post no arquivo, o portão (publicar.py) não o publica.
export async function removerDaAprovacao(existente, semana, numero, nonce, aprovadoPor, aprovadoEm, segredo) {
  if (!existente || !(existente.posts ?? []).some((i) => i.numero === numero)) return { dados: existente, mudou: false };
  const dados = {
    semana,
    aprovado_por: aprovadoPor,
    aprovado_em: aprovadoEm,
    nonce,
    posts: existente.posts.filter((i) => i.numero !== numero),
  };
  dados.assinatura = await assinar(dados, segredo);
  return { dados, mudou: true };
}
