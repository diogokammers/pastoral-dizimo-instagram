# 05 — Medições locais (execução real nesta máquina)

## M1 — Esquema de saída de `claude -p --output-format json` (2026-09-25)
Comando: `claude -p "Responda apenas a palavra: ok" --output-format json --model haiku --max-turns 1`
Versão: Claude Code 2.1.228. Resultado: a chamada **falhou por autenticação** ("OAuth session expired and
could not be refreshed") — o CLI standalone desta máquina precisa de `claude login` em terminal; o app
desktop usa sessão própria. Mesmo assim o envelope JSON foi emitido e **confirma o esquema**:

- `total_cost_usd`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, `terminal_reason`, `session_id`
- `usage.input_tokens`, `usage.output_tokens`, `usage.cache_creation_input_tokens`,
  `usage.cache_read_input_tokens`, `usage.cache_creation.ephemeral_5m_input_tokens|ephemeral_1h_input_tokens`,
  `usage.output_tokens_details.thinking_tokens`, `usage.server_tool_use.web_search_requests|web_fetch_requests`
- `modelUsage` (por modelo; vazio aqui porque não houve chamada)
- `permission_denials`, `stop_reason`, `subtype`, `result`

Implicação: um GitHub Action ou script local que rode `claude -p` consegue medir tokens e custo por
execução lendo esse JSON — atende à regra "medir, não estimar". Em plano de assinatura, `total_cost_usd`
tende a vir 0 (a confirmar quando autenticado); os campos de tokens continuam válidos.

Pré-requisito do piloto: Diogo rodar `claude login` no terminal (ou `claude setup-token` para CI).

Saída bruta:
```json
{"is_error":true,"duration_api_ms":0,"num_turns":1,"stop_reason":"stop_sequence","session_id":"c5777441-9292-4901-b24a-387228165b70","total_cost_usd":0,"usage":{"output_tokens_details":{"thinking_tokens":0},"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard"},"modelUsage":{},"permission_denials":[],"terminal_reason":"api_error","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subtype":"success","api_error_status":null,"result":"Failed to authenticate: OAuth session expired and could not be refreshed","type":"result","duration_ms":602,"uuid":"1c2d3b57-9a9a-4166-a547-d13f7d51e9af"}

```
