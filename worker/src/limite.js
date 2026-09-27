// Limite de tentativas do código de envio (ADR-012): 5 códigos errados em 15 minutos, vindos do mesmo IP
// (identificado só pelo HMAC do IP), bloqueiam esse IP por 15 minutos contados da 5ª falha mais recente.
// Acertar o código apaga as falhas daquele IP. Falhas com mais de 1 dia são apagadas a cada nova falha.

export const MAX_FALHAS = 5;
export const JANELA_MS = 15 * 60 * 1000;
const GUARDA_MS = 24 * 60 * 60 * 1000;

export class Limite {
  constructor(db) {
    if (!db) throw new Error("banco D1 (binding DB) não configurado");
    this.db = db;
  }

  // ISO do fim do bloqueio, ou null se o IP pode tentar.
  async bloqueadoAte(ip, agora) {
    const corte = new Date(agora.getTime() - JANELA_MS).toISOString();
    const r = await this.db
      .prepare(`SELECT criado_em FROM falhas_acesso WHERE ip_hash = ? AND criado_em > ?
                ORDER BY criado_em DESC LIMIT 1 OFFSET ${MAX_FALHAS - 1}`)
      .bind(ip, corte)
      .first();
    return r ? new Date(Date.parse(r.criado_em) + JANELA_MS).toISOString() : null;
  }

  // Registra uma falha e devolve quantas o IP tem na janela.
  async registrarFalha(ip, agora) {
    await this.db.prepare("DELETE FROM falhas_acesso WHERE criado_em < ?")
      .bind(new Date(agora.getTime() - GUARDA_MS).toISOString()).run();
    await this.db.prepare("INSERT INTO falhas_acesso (ip_hash, criado_em) VALUES (?, ?)")
      .bind(ip, agora.toISOString()).run();
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM falhas_acesso WHERE ip_hash = ? AND criado_em > ?")
      .bind(ip, new Date(agora.getTime() - JANELA_MS).toISOString()).first();
    return r.n;
  }

  async limpar(ip) {
    await this.db.prepare("DELETE FROM falhas_acesso WHERE ip_hash = ?").bind(ip).run();
  }
}
