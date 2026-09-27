-- Painel de aprovação (ADR-011): registro APPEND-ONLY das decisões por post.
-- Nunca apagar nem alterar eventos: os gatilhos abaixo recusam UPDATE e DELETE.
CREATE TABLE eventos (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  post            INTEGER NOT NULL CHECK (post BETWEEN 1 AND 9999),
  semana          TEXT    NOT NULL CHECK (length(semana) = 8 AND semana GLOB '[0-9][0-9][0-9][0-9]-W[0-9][0-9]'),
  acao            TEXT    NOT NULL CHECK (acao IN ('aprovar', 'ajustar', 'desfazer')),
  comentario      TEXT    NOT NULL DEFAULT '' CHECK (length(comentario) <= 2000),
  versao_conteudo TEXT    NOT NULL CHECK (length(versao_conteudo) = 32),  -- aprovacao.versao_post no momento
  autor           TEXT    NOT NULL,                                        -- "Padre", "Diogo"…
  criado_em       TEXT    NOT NULL,                                        -- ISO 8601 UTC (+00:00)
  origem          TEXT    NOT NULL DEFAULT 'painel' CHECK (origem IN ('painel', 'email')),
  commit_sha      TEXT,                                                    -- commit do GitHub desta decisão
  ip_hash         TEXT                                                     -- HMAC do IP (só no D1, não vai ao backup)
);

CREATE INDEX eventos_por_post ON eventos (post, id);

CREATE TRIGGER eventos_sem_update BEFORE UPDATE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'eventos: append-only (UPDATE proibido)');
END;

CREATE TRIGGER eventos_sem_delete BEFORE DELETE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'eventos: append-only (DELETE proibido)');
END;

-- Estado atual = último evento de cada post.
CREATE VIEW estado_atual AS
SELECT e.*
FROM eventos AS e
JOIN (SELECT post, MAX(id) AS ultimo FROM eventos GROUP BY post) AS u ON u.ultimo = e.id;
