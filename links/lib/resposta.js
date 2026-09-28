// POST /api/resposta (ADR-013): recebe um formulário, aplica o limite por IP, descarta robôs e grava no D1.
// O IP só é usado como HMAC (secret IP_HMAC_SECRET) na tabela envios_ip; a resposta não guarda IP.
import { validar } from "./validar.js";

export const MAX_ENVIOS = 10; // por IP, na janela abaixo
export const JANELA_MS = 60 * 60 * 1000;
export const MAX_CORPO = 16 * 1024; // bytes
const GUARDA_MS = 24 * 60 * 60 * 1000;

const json = (status, corpo) =>
  new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

async function hmacHex(segredo, texto) {
  const chave = await crypto.subtle.importKey("raw", new TextEncoder().encode(segredo),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const assinatura = await crypto.subtle.sign("HMAC", chave, new TextEncoder().encode(texto));
  return [...new Uint8Array(assinatura)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function tratar(request, env, agora, CAMPOS) {
  if (!env.DB || !env.IP_HMAC_SECRET) return json(500, { ok: false, erro: "servidor sem configuração" });

  const bruto = await request.text();
  if (new TextEncoder().encode(bruto).length > MAX_CORPO) return json(413, { ok: false, erro: "grande demais" });
  let corpo;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    return json(400, { ok: false, erros: ["json"] });
  }

  // limite por IP (conta também os envios de robô, para não virar porta aberta)
  const ip = await hmacHex(env.IP_HMAC_SECRET, request.headers.get("CF-Connecting-IP") || "sem-ip");
  const corte = new Date(agora.getTime() - JANELA_MS).toISOString();
  const { n } = await env.DB.prepare("SELECT COUNT(*) AS n FROM envios_ip WHERE ip_hash = ? AND criado_em > ?")
    .bind(ip, corte).first();
  if (n >= MAX_ENVIOS) return json(429, { ok: false, erro: "limite" });
  await env.DB.prepare("DELETE FROM envios_ip WHERE criado_em < ?")
    .bind(new Date(agora.getTime() - GUARDA_MS).toISOString()).run();
  await env.DB.prepare("INSERT INTO envios_ip (ip_hash, criado_em) VALUES (?, ?)").bind(ip, agora.toISOString()).run();

  // campo invisível "site": só robô preenche; finge sucesso e descarta
  if (corpo && typeof corpo === "object" && corpo.site) return json(200, { ok: true });

  const r = validar(corpo, CAMPOS);
  if (!r.ok) return json(400, { ok: false, erros: r.erros });

  await env.DB.prepare("INSERT INTO respostas (id, criado_em, tipo, versao_form, dados) VALUES (?, ?, ?, ?, ?)")
    .bind(crypto.randomUUID(), agora.toISOString(), r.tipo, CAMPOS.versao, JSON.stringify(r.dados)).run();
  return json(200, { ok: true });
}
