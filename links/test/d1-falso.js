// D1 falso para os testes: a mesma API do D1 (prepare → bind → first/all/run) sobre o SQLite do Node,
// com as MESMAS migrations de links/migrations/ (mesmo padrão de worker/test/d1-falso.js).
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const MIGRATIONS = fileURLToPath(new URL("../migrations/", import.meta.url));
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
    return semProto(this.banco.db.prepare(this.sql).get(...this.args));
  }
  async all() {
    return { success: true, results: this.banco.db.prepare(this.sql).all(...this.args).map(semProto) };
  }
  async run() {
    const r = this.banco.db.prepare(this.sql).run(...this.args);
    return { success: true, meta: { changes: r.changes } };
  }
}

export class D1Falso {
  constructor() {
    this.db = new DatabaseSync(":memory:");
    for (const nome of readdirSync(MIGRATIONS).filter((n) => n.endsWith(".sql")).sort()) {
      this.db.exec(readFileSync(join(MIGRATIONS, nome), "utf8"));
    }
  }
  prepare(sql) {
    return new Comando(this, sql);
  }
  linhas(tabela) {
    return this.db.prepare(`SELECT * FROM ${tabela}`).all().map(semProto);
  }
}
