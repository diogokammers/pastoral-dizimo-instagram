// Camada de repositório do D1 (ADR-011). Só esta classe fala SQL; os testes usam um D1 falso sobre
// node:sqlite que aplica as mesmas migrations (worker/migrations/). A tabela `eventos` é append-only:
// aqui só existe INSERT e SELECT, e o banco recusa UPDATE/DELETE por gatilho.

const COLUNAS = "id, post, semana, acao, comentario, versao_conteudo, autor, criado_em, origem, commit_sha";

const limpo = (linha) => (linha ? Object.fromEntries(Object.entries(linha)) : null);

export class Banco {
  constructor(db) {
    if (!db) throw new Error("banco D1 (binding DB) não configurado");
    this.db = db;
  }

  // Grava um evento e devolve o id. `ev`: post, semana, acao, comentario, versao_conteudo, autor,
  // criado_em, origem, commit_sha, ip_hash.
  async registrar(ev) {
    const r = await this.db
      .prepare(
        `INSERT INTO eventos (post, semana, acao, comentario, versao_conteudo, autor, criado_em, origem, commit_sha, ip_hash)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id`,
      )
      .bind(ev.post, ev.semana, ev.acao, ev.comentario ?? "", ev.versao_conteudo, ev.autor, ev.criado_em,
        ev.origem ?? "painel", ev.commit_sha ?? null, ev.ip_hash ?? null)
      .first();
    return r.id;
  }

  // Último evento do post (estado atual) ou null.
  async ultimo(post) {
    return limpo(await this.db.prepare(`SELECT ${COLUNAS} FROM estado_atual WHERE post = ?`).bind(post).first());
  }

  // Estado atual de todos os posts com algum evento.
  async estado() {
    const { results } = await this.db.prepare(`SELECT ${COLUNAS} FROM estado_atual ORDER BY post`).all();
    return results.map(limpo);
  }

  // Todos os eventos, em ordem (backup para o repositório). Sem ip_hash.
  async todos() {
    const { results } = await this.db.prepare(`SELECT ${COLUNAS} FROM eventos ORDER BY id`).all();
    return results.map(limpo);
  }
}
