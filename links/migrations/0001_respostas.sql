-- Formulários da página de links (ADR-013). Respostas append-only; o IP nunca fica junto da resposta.
CREATE TABLE respostas (
  id TEXT PRIMARY KEY,
  criado_em TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('agente', 'fiel')),
  versao_form INTEGER NOT NULL,
  dados TEXT NOT NULL CHECK (json_valid(dados))
);
CREATE TRIGGER respostas_sem_update BEFORE UPDATE ON respostas
BEGIN SELECT RAISE(ABORT, 'respostas é append-only'); END;

-- Limite de envios por IP (só o HMAC do IP; linhas com mais de 1 dia são apagadas a cada envio).
CREATE TABLE envios_ip (
  ip_hash TEXT NOT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX envios_ip_busca ON envios_ip (ip_hash, criado_em);
