// D1 falso para os testes: a mesma API usada por banco.js (prepare → bind → first/all/run) sobre o SQLite
// embutido no Node (node:sqlite), com as MESMAS migrations de worker/migrations/ aplicadas em ordem.
// Assim os testes exercitam o SQL de verdade (CHECKs, gatilhos append-only e a visão estado_atual).
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

export const MIGRATIONS = fileURLToPath(new URL("../migrations/", import.meta.url));

const semProto = (linha) => (linha ? { ...linha } : null);

class Comando {
  constructor(banco, sql, args = []) {
    this.banco = banco;
    this.sql = sql;
    this.args = args;
  }

  bind(...args) {
    return new Comando(this.banco, this.sql, args);
  }

  async first() {
    this.banco.falharSeCombinado(this.sql);
    return semProto(this.banco.db.prepare(this.sql).get(...this.args));
  }

  async all() {
    this.banco.falharSeCombinado(this.sql);
    return { success: true, results: this.banco.db.prepare(this.sql).all(...this.args).map(semProto) };
  }

  async run() {
    this.banco.falharSeCombinado(this.sql);
    const r = this.banco.db.prepare(this.sql).run(...this.args);
    return { success: true, meta: { last_row_id: Number(r.lastInsertRowid), changes: r.changes } };
  }
}

export class D1Falso {
  constructor() {
    this.db = new DatabaseSync(":memory:");
    for (const nome of readdirSync(MIGRATIONS).filter((n) => n.endsWith(".sql")).sort()) {
      this.db.exec(readFileSync(join(MIGRATIONS, nome), "utf8"));
    }
    this.falhar = false;
  }

  // true = tudo falha; "insert" = só gravações falham (o commit no GitHub já terá acontecido)
  falharSeCombinado(sql) {
    if (this.falhar === true || (this.falhar === "insert" && /^\s*INSERT/i.test(sql))) {
      throw new Error("D1 indisponível (simulado)");
    }
  }

  prepare(sql) {
    return new Comando(this, sql);
  }

  // atalho dos testes: todas as linhas cruas (inclui ip_hash)
  linhas() {
    return this.db.prepare("SELECT * FROM eventos ORDER BY id").all().map(semProto);
  }
}
