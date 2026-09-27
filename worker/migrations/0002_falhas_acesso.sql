-- Limite de tentativas do código de envio (ADR-012). Uma linha por tentativa com código errado,
-- identificada só pelo HMAC do IP (nunca o IP). Esta tabela NÃO é append-only: as falhas antigas
-- (mais de 1 dia) são apagadas pelo Worker e as de um IP somem quando ele acerta o código.
CREATE TABLE falhas_acesso (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ip_hash   TEXT NOT NULL,
  criado_em TEXT NOT NULL            -- ISO 8601 UTC com milissegundos (Date.toISOString)
);

CREATE INDEX falhas_por_ip ON falhas_acesso (ip_hash, criado_em);
