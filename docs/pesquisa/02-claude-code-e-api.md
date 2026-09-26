# Pesquisa 02 — Claude Code e API Anthropic (fontes oficiais)

> Data da pesquisa: 2026-09-25. Todas as afirmações abaixo foram verificadas nesta sessão, com WebFetch, diretamente em `docs.claude.com` / `code.claude.com` / `platform.claude.com` (domínio atual da documentação Anthropic) ou `github.com/anthropics`. Onde não foi possível confirmar em fonte oficial, está marcado **NÃO VERIFICADO**.

---

## A. Claude Code

### A.1 Subagentes (`.claude/agents/*.md`)

- **Fato:** o frontmatter suporta `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `omitClaudeMd`, `effort`, `isolation`, `color`, `initialPrompt`, `experimental`. — Fonte: https://code.claude.com/docs/en/sub-agents (trecho: "Tools the subagent can use... Inherits every tool available to subagents if omitted").
- **Fato:** é possível fixar o modelo por subagente. O campo `model` aceita `sonnet`, `opus`, `haiku`, `fable`, um ID completo (ex.: `claude-opus-5-5`) ou `inherit`. — Fonte: idem (trecho: "Model to use: `sonnet`, `opus`, `haiku`, `fable`, a full model ID... or `inherit`").
- **Fato:** ordem de resolução do modelo: (1) parâmetro por invocação, (2) frontmatter do subagente (`inherit` = modelo da conversa principal), (3) variável de ambiente `CLAUDE_CODE_SUBAGENT_MODEL`, (4) modelo da conversa principal. — Fonte: idem.
- **Fato:** cada subagente roda com **contexto isolado**: "A fresh, isolated context window"; "Doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read". Exceção: quando é um "fork", que herda a conversa pai. — Fonte: idem.
- **Fato:** o que carrega no início de um subagente não-fork: system prompt próprio, mensagem de tarefa, arquivos CLAUDE.md (salvo `omitClaudeMd: true`), snapshot do git status, skills pré-carregadas (campo `skills`), lista de agentes irmãos. Não chegam: output style, memória automática (exceto via campo `memory` do próprio subagente), tamanho da janela de contexto do pai. — Fonte: idem.
- **Fato (consumo de tokens do subagente):** a documentação não descreve um mecanismo específico de relatório de tokens por subagente na página de subagentes. O comando `/tasks` mostra apenas o **modelo** e o **nível de effort** usados por cada subagente em execução (requer Claude Code ≥ v2.1.242). — Fonte: idem (trecho: "run `/tasks`. Claude Code names the model on the subagent's row, and adds the effort level...").
- **Fato:** o guia oficial de custos confirma que o resumo de sessão (`/usage`) soma tokens **apenas da conversa principal** — o cache de prompt reportado ali é "main conversation only, not subagents" — e que a atribuição por skill/subagente/plugin/MCP aparece como percentuais em `/usage` (breakdown de uso do plano), não como tokens absolutos por subagente. — Fonte: https://code.claude.com/docs/en/costs (trecho: "It covers the main conversation only, not subagents." e "Attribution: recent usage attributed to skills, subagents, plugins, and individual MCP servers, each shown as a percentage of the total").

### A.2 Skills (`.claude/skills/*/SKILL.md`)

- **Fato:** frontmatter suporta `name`, `description`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context` (`fork`), `arguments`, `paths`. — Fonte: https://code.claude.com/docs/en/skills.
- **Fato (carregamento progressivo):** "Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it." A `description` fica sempre no contexto; o corpo completo do `SKILL.md` só entra quando a skill é invocada, e então persiste na conversa. — Fonte: idem.
- **Fato (`disable-model-invocation`):** quando `true`, só o usuário pode invocar a skill (Claude não a carrega automaticamente); usado para ações com efeitos colaterais como `/deploy`, `/commit`. — Fonte: idem.
- **Fato (`context: fork`):** faz o Claude Code iniciar um subagente novo (do tipo definido em `agent`) e entregar o conteúdo da skill como prompt dele; "the subagent doesn't see your conversation history"; roda em background por padrão (pode ser `background: false` para esperar o resultado). — Fonte: idem.
- **Fato (argumentos):** placeholders `$ARGUMENTS`, `$0`/`$1`/`$2`, `$name` (via campo `arguments`), `${CLAUDE_SESSION_ID}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SKILL_DIR}`. — Fonte: idem.
- **Fato (diferença para CLAUDE.md):** CLAUDE.md carrega **integralmente a cada turno**; skills carregam a descrição sempre e o corpo só sob demanda. Recomendação oficial: "Create a skill when you keep pasting the same instructions, checklist, or multi-step procedure into chat, or when a section of CLAUDE.md has grown into a procedure rather than a fact." — Fonte: idem.
- **Fato (diferença para comandos):** skills podem ser invocadas automaticamente pelo modelo (quando `disable-model-invocation` não está setado) ou explicitamente via `/nome-da-skill`; comandos de barra tradicionais (slash commands) não têm o mecanismo de correspondência automática por `description`. — Fonte: idem (seção "Skills vs. CLAUDE.md" / "When to Use Skills").

### A.3 Hooks

- **Fato (eventos disponíveis):** por sessão — `SessionStart`, `SessionEnd`, `Setup`; por turno — `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`; por chamada de ferramenta — `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`; adicionais — `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult`. — Fonte: https://code.claude.com/docs/en/hooks.
- **Fato (bloqueio determinístico por código de saída):** "Exit 2 means a blocking error." Exit 2 **sempre bloqueia**, independentemente da saída JSON: "Even a JSON `permissionDecision` of `'allow'` can't override it." — Fonte: idem.
- **Fato (bloqueio via JSON):** hooks nos eventos de decisão padrão podem retornar `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}` para negar a ação com exit 0. — Fonte: idem.
- **Fato (matcher por ferramenta):** campo `matcher` filtra por nome de ferramenta em `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied` — combinação exata (`"Bash"`, `"Edit|Write"`), regex (`"^Notebook"`, `"mcp__memory__.*"`) ou coringa (`"*"`/omitido). — Fonte: idem.
- **Conclusão sobre "portão determinístico":** sim — hooks (especialmente `PreToolUse` com exit code 2 ou `permissionDecision: "deny"`) servem como gate determinístico de código, executado pelo harness antes/depois da ferramenta, e não dependem do modelo "decidir obedecer".

### A.4 Modo headless / não interativo (`claude -p`)

- **Fato:** flags confirmadas na referência de CLI: `--print`/`-p`, `--output-format` (`text`, `json`, `stream-json`), `--input-format` (`text`, `stream-json`), `--model`, `--effort`, `--max-turns` ("Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached. No limit by default"), `--allowedTools`/`--allowed-tools`, `--disallowedTools`, `--permission-mode`, `--permission-prompts`, `--permission-prompt-tool`, `--dangerously-skip-permissions`, `--append-system-prompt`, `--append-system-prompt-file`, `--append-subagent-system-prompt(-file)`, `--exclude-dynamic-system-prompt-sections`, `--autocompact`, `--advisor`, `--init`, `--maintenance`. — Fonte: https://code.claude.com/docs/en/cli-reference.
- **Fato — existe limite de orçamento em dólares:** `--max-budget-usd` — "Maximum dollar amount to spend on API calls before stopping (print mode only). Spend from subagents counts toward the cap. Once spend reaches the cap, spawning another subagent fails with `Budget limit reached`, and Claude Code stops background subagents that are still running." — Fonte: idem.
- **Fato (custo multiplicado por data residency):** o valor multiplicado por 1.1x (quando a resposta usa `inference_geo: "us"`) também conta para `--max-budget-usd`. — Fonte: https://code.claude.com/docs/en/costs.
- **NÃO VERIFICADO (schema JSON exato / `--json-schema`):** a página oficial de headless do Claude Code (`code.claude.com/docs/en/sdk/sdk-headless`) redirecionou para a documentação do **Agent SDK** (`docs.claude.com/en/docs/agent-sdk/headless`), que é um produto correlato mas distinto do CLI `claude -p`; não consegui confirmar nesta sessão, na página de CLI reference, um exemplo literal do JSON de saída do `claude -p --output-format json` contendo `total_cost_usd`, `usage`, `duration_ms`, `num_turns`. A referência de CLI (fonte acima) confirma a existência das flags `--output-format json|stream-json`, mas não reproduziu o schema completo do objeto de resultado nesta consulta. **Recomenda-se confirmar o schema exato rodando `claude -p "teste" --output-format json` localmente** antes de depender dele no pipeline do GitHub Action.
- **Fato indireto:** o próprio Claude Code calcula o custo da sessão localmente a partir da contagem de tokens ("Claude Code computes the dollar figure locally from token counts at list price"), o que confirma que o CLI tem acesso a `usage` (tokens de input/output/cache) por resposta da API — consistente com esses campos estarem disponíveis também na saída JSON do modo `-p`, mas o texto exato do schema não foi visto nesta sessão. — Fonte: https://code.claude.com/docs/en/costs.

### A.5 GitHub Actions — `anthropics/claude-code-action`

- **Fato (autenticação):** "Either `ANTHROPIC_API_KEY` for API key authentication" ou "`CLAUDE_CODE_OAUTH_TOKEN` for OAuth token authentication (Pro and Max users can generate this by running `claude setup-token` locally)". — Fonte: https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md.
- **Fato — isto é a orientação oficial atual:** o uso de assinatura Pro/Max em CI via GitHub Actions é **documentado oficialmente e explicitamente suportado** pelo repositório oficial `anthropics/claude-code-action`, através da variável de secret `CLAUDE_CODE_OAUTH_TOKEN`, gerada localmente com `claude setup-token`. Está listado lado a lado com `ANTHROPIC_API_KEY` como opção de autenticação de primeira classe, sem aviso de depreciação ou de "apenas para teste". — Fonte: idem.
- **NÃO VERIFICADO:** não encontrei, no `docs/setup.md` nem no README do repositório, nenhuma cláusula explícita de Termos de Serviço proibindo ou restringindo o uso do plano de assinatura (Pro/Max) especificamente em automação/CI — a documentação técnica simplesmente oferece o recurso. Isso **não é o mesmo** que uma declaração de política de uso aceitável; para uma decisão de compliance formal recomenda-se checar os Termos de Uso do Consumidor da Anthropic (não uma página técnica), que não foi objeto desta consulta.
- **Fato adicional:** o README do repositório também menciona que a action "supports multiple authentication methods including Anthropic direct API (API key or workload identity federation), Amazon Bedrock, Google Vertex AI, and Microsoft Foundry" — ou seja, API key e Bedrock/Vertex/Foundry também são caminhos suportados, além do OAuth de assinatura. — Fonte: https://github.com/anthropics/claude-code-action (README).

### A.6 Medição de uso — `/cost`, `/context`, `/usage`, `/stats`

- **Fato:** o comando atual e documentado é **`/usage`** (não há `/cost` nem `/stats` como comandos distintos confirmados na página de custos — `/usage` incorpora o antigo bloco de "Session cost"). — Fonte: https://code.claude.com/docs/en/costs.
- **Fato:** "The Session block in `/usage` shows API token usage and is intended for API users. Claude Max and Pro subscribers have usage included in their subscription, so the session cost figure isn't relevant for billing purposes. Subscribers see plan usage bars, activity stats, and a usage breakdown on the same screen." — Fonte: idem.
- **Fato (exemplo de saída do bloco de sessão):**
  ```text
  Total cost:            $0.55
  Total duration (API):  6m 20s
  Total duration (wall): 6h 33m 10s
  Total code changes:    0 lines added, 0 lines removed
  Usage by model:
     claude-sonnet-4-6:  1.2k input, 5.3k output, 940.0k cache read, 50.0k cache write ($0.55)
  ```
  — Fonte: idem.
- **Fato:** `/usage` também mostra estatísticas de cache de prompt da conversa principal (`Prompt cache (main)`), breakdown de atribuição por skill/subagente/plugin/MCP (em %), flags de comportamento (ex.: contexto longo, cache miss) e, em planos Pro/Max/Team/Enterprise, gasto de "usage credits". — Fonte: idem.
- **Fato (`/context`):** é referenciado como comando para ver o que está consumindo espaço de contexto (ex.: "Run `/context` to see what's consuming space" ao falar de overhead de servidores MCP). — Fonte: idem.
- **NÃO VERIFICADO:** não encontrei, nesta sessão, uma página dedicada descrevendo exaustivamente `/context` e um comando `/stats` separado; a documentação de custos trata `/usage` como o comando central de monitoramento, com `/insights` para análise de padrões de uso (não de custo).
- **Fato (transcritos locais):** Claude Code armazena o histórico de sessão em `~/.claude/projects/<projeto>/<sessão>.jsonl` (no Windows, `~/.claude` resolve para `%USERPROFILE%\.claude`), contendo "every message, tool call, and tool result" — o transcrito completo da conversa. — Fonte: https://code.claude.com/docs/en/claude-directory.
- **NÃO VERIFICADO (usage por mensagem no `.jsonl`):** a página consultada não afirma explicitamente que cada linha do `.jsonl` contém o objeto `usage` (tokens) por mensagem; ela menciona que estatísticas agregadas de token/custo ficam em `stats-cache.json` ("Aggregated token and cost counts shown by `/usage`"), separado do transcrito bruto. Para medir tokens por subagente a partir dos arquivos locais, é necessário inspecionar diretamente um `.jsonl` real (não confirmado via documentação oficial nesta sessão) — **recomenda-se validação empírica**: abrir um `.jsonl` de sessão e verificar se blocos de resposta de assistente carregam `usage`.

### A.7 Limites dos planos Pro e Max (5x / 20x)

- **Fato (janelas de uso):** os planos usam "a rolling five-hour session window" e um limite semanal, compartilhados entre Claude Code, Claude chat e Cowork/Teams conforme o "seat tier" (Standard ou Premium) em planos de equipe. — Fonte: https://code.claude.com/docs/en/costs (seção "Claude for Teams and Enterprise") e https://claude.com/pricing.
- **Fato (preços mensais USD):** Claude Pro = **US$ 20/mês** (cobrança mensal) ou US$ 17/mês com assinatura anual; Claude Max 5x = **"From $100 Per month"**; Claude Max 20x = **"From $100 Per month"** (a página lista as duas faixas Max a partir de US$ 100, com a diferenciação 5x/20x referindo-se ao múltiplo de uso, não necessariamente a um preço-base diferente exibido). — Fonte: https://claude.com/pricing.
- **Fato (disponibilidade de modelos por plano):** Pro tem acesso a Opus, Sonnet e Haiku; Fable fica disponível via "Usage credits" no Pro. Max 5x e Max 20x têm acesso a todos os modelos, incluindo Fable, "at 50% of weekly limits". — Fonte: idem.
- **NÃO VERIFICADO:** a página de pricing consultada (via WebFetch/resumo) **não mencionou preço em BRL** — não há confirmação oficial de conversão para Real brasileiro nesta consulta; a Anthropic cobra em USD por padrão (ver seção B/pricing). Se o checkout mostrar BRL, é conversão de processador de pagamento/App Store, não tabela oficial da Anthropic.
- **NÃO VERIFICADO (número de tokens):** como esperado, a Anthropic **não publica um número fixo de tokens** para os limites de sessão de 5 horas ou semanais dos planos Pro/Max — os limites são descritos em termos de janelas de tempo e "seat tier", não em contagem de tokens. Isso está de acordo com a keyword do usuário ("provavelmente não").

### A.8 Structured outputs / JSON na API

- **Fato (nome exato do parâmetro):** `output_config.format` — "The `output_format` parameter has moved to `output_config.format`, and beta headers are no longer required. The `output_format` parameter is deprecated and will be removed in the future." — Fonte: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.
- **Fato (beta header):** **não é necessário** beta header para `output_config.format` — é GA. Apenas o parâmetro legado `output_format` (deprecated) ainda exigiria o header `structured-outputs-2025-11-13` como workaround. — Fonte: idem.
- **Fato (modelos suportados):** inclui `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-sonnet-4-5`, `claude-opus-4-5`, `claude-haiku-4-5`, `claude-mythos-5-1`, `claude-mythos-5`, `claude-fable-5-1`, `claude-fable-5`, e variantes anteriores de Opus/Sonnet (4.8, 4.7, 4.6). — Fonte: idem.
- **Fato ("strict tool use"):** é um recurso relacionado mas distinto — `strict: true` no nível da definição da tool (não em `tool_choice`), exige `additionalProperties: false` + `required` no schema, e garante que `tool_use.input` valide exatamente o schema. "JSON outputs control Claude's response format (what Claude says)" vs. "Strict tool use validates tool parameters (how Claude calls your functions)". — Fonte: idem (via skill `claude-api`, confirmado na doc oficial).

### A.9 Modelos atuais — IDs, status, contexto, preço

| Modelo | ID | Contexto | Max output | Input | Output |
|---|---|---|---|---|---|
| Claude Fable 5.1 | `claude-fable-5-1` | 1M | 128K | $10/MTok | $50/MTok |
| Claude Opus 5.5 (lançamento) | `claude-opus-5-5` | 1M | 128K | $4/MTok | $20/MTok |
| Claude Opus 5 | `claude-opus-5` | 1M | 128K | $5/MTok | $25/MTok |
| Claude Sonnet 5 | `claude-sonnet-5` | 1M | 128K | $2/MTok¹ | $10/MTok¹ |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | — | $1/MTok | $5/MTok |

¹ Preço de lançamento tornado permanente: "The $2/$10 per million input/output token pricing for Claude Sonnet 5... is now the standard price." — Fonte: https://platform.claude.com/docs/en/about-claude/pricing (tabela "Model pricing", verificada nesta sessão).

- **Fato (status):** Claude Opus 5.5 está descrito na tabela oficial de preços como modelo corrente (não mais "beta"/preview) ao lado de Fable 5.1, mas a skill interna do agente o classifica como "launching — use only when the user names it", sugerindo lançamento recente/gradual. — Fonte: https://platform.claude.com/docs/en/about-claude/pricing.
- **Fato (Fable 5.1 nos planos Pro/Max):** confirmado na seção A.7 acima — Fable está disponível no Max 5x/20x diretamente (a 50% do limite semanal) e no Pro apenas via "usage credits" pagos adicionais, não incluído no limite padrão do plano Pro. — Fonte: https://claude.com/pricing.

---

## B. API Anthropic

### B.1 Message Batches API

- **Fato (desconto):** 50% em input e output. — Fonte: https://platform.claude.com/docs/en/build-with-claude/batch-processing (trecho: "cutting costs by 50% and increasing throughput").
- **Fato (limites):** um Message Batch é limitado a **100.000 requests** ou **256 MB**, o que ocorrer primeiro. — Fonte: idem.
- **Fato (tempo de processamento):** "most batches completing within 1 hour"; resultados ficam disponíveis quando todas as mensagens terminam ou após **24 horas**, o que vier primeiro; batches expiram se não completarem em 24h. Resultados ficam disponíveis para download por **29 dias** após a criação. — Fonte: idem.
- **Fato (como recuperar resultados):** o batch expõe `results_url` quando `processing_status == "ended"`; os resultados vêm em `.jsonl`, um objeto JSON por linha, **em qualquer ordem** (usar `custom_id` para casar request/resultado, nunca a posição). Quatro tipos de resultado: `succeeded`, `errored`, `canceled`, `expired` (os três últimos não são cobrados). — Fonte: idem.
- **Fato (compatibilidade com prompt caching):** sim, suportado e os descontos **acumulam** (batch 50% + cache); porém, como o processamento é assíncrono/concorrente, "cache hits are provided on a best-effort basis" com taxa de acerto entre 30% e 98% dependendo do padrão de tráfego. Recomenda-se usar cache de 1 hora (`ttl: "1h"`) para batches, já que podem levar mais que 5 minutos. — Fonte: idem.
- **Fato (compatibilidade com structured outputs):** a página lista "Most beta features" como suportados dentro de batch, sem exclusão para structured outputs; parâmetros explicitamente **não suportados** em batch são apenas `stream: true`, `speed` (fast mode) e `max_tokens: 0`. — Fonte: idem.

### B.2 Prompt caching

- **Fato (preço de escrita):** cache de 5 minutos = **1,25×** o preço base de input; cache de 1 hora = **2×** o preço base de input. — Fonte: https://platform.claude.com/docs/en/about-claude/pricing (seção "Prompt caching") e https://platform.claude.com/docs/en/build-with-claude/prompt-caching.
- **Fato (preço de leitura):** cache hit = **0,1×** o preço base de input na maioria dos modelos (inclui Sonnet 5, Opus 5, Haiku 4.5); exceções: Claude Fable 5.1/Mythos 5.1 = **0,025×**; Claude Opus 5.5 = **0,05×**. — Fonte: idem.
- **Fato (tamanho mínimo cacheável):** varia por modelo — **512 tokens** (Fable 5.1, Mythos 5.1, Opus 5.5, Opus 5, Fable 5, Mythos 5); **1.024 tokens** (Opus 4.8, Sonnet 5, Sonnet 4.6/4.5, Opus 4.1/4); **2.048 tokens** (Mythos Preview, Opus 4.7, Haiku 3.5); **4.096 tokens** (Opus 4.6/4.5, Haiku 4.5). Prompts abaixo do mínimo não são cacheados, sem erro. — Fonte: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.
- **Fato (TTL):** 5 minutos (padrão, sem custo adicional de manutenção) ou 1 hora (via `cache_control: {"type": "ephemeral", "ttl": "1h"}`, 2× no write). — Fonte: idem.
- **Fato (máximo de breakpoints):** **4 breakpoints explícitos** por request (caching automático usa um desses 4 slots). — Fonte: idem.
- **Fato (o que invalida o cache):** hierarquia `tools → system → messages`; mudar definições de tools invalida tudo; alternar web search/citations ou `speed` invalida system+messages; mudar `tool_choice`, imagens ou parâmetros de thinking/effort invalida messages (e possivelmente mais, dependendo do modelo). Mensagens de sistema mid-conversation (`{"role": "system"}` anexado) **não** invalidam o prefixo cacheado. — Fonte: idem.

### B.3 Token counting endpoint

- **Fato (gratuito):** "Token counting is **free to use** but subject to requests per minute rate limits based on your usage tier." — Fonte: https://platform.claude.com/docs/en/build-with-claude/token-counting.
- **Fato (limites de RPM só para o endpoint):** Start = 5.000 RPM; Build = 10.000 RPM; Scale = 20.000 RPM — "Token counting and message creation have separate and independent rate limits." — Fonte: idem.
- **Fato (uso para medir "cartão de marca"):** sim, serve exatamente para medir o tamanho de um prompt/system prompt fixo antes de gastar — o endpoint aceita o mesmo formato estruturado de mensagens/tools/sistema da Messages API e devolve `{"input_tokens": N}` sem cobrar nem gerar resposta. Não usa lógica de cache real durante a contagem ("token counting provides an estimate without using caching logic"). — Fonte: idem.

### B.4 Rate limits / tier inicial

- **Fato (estrutura de tiers atual):** a documentação oficial atual usa os nomes **Start, Build, Scale** (não mais "Tier 1/2/3/4" como em versões antigas da doc). Novas organizações podem começar em um "Evaluation tier" com limites abaixo do padrão, que sobem automaticamente com histórico de uso. — Fonte: https://platform.claude.com/docs/en/api/rate-limits.
- **Fato (spend caps por tier):** Start = US$ 500/mês; Build = US$ 1.000/mês; Scale = US$ 200.000/mês; Custom = sem cap fixo (negociado). — Fonte: idem.
- **Fato (RPM/ITPM/OTPM no tier Start, para os principais modelos):** Claude Opus 5, Opus 5.5, Sonnet 5, Haiku 4.5 = 1.000 RPM / 2.000.000 ITPM / 400.000 OTPM cada; família Fable = 1.000 RPM / 500.000 ITPM / 100.000 OTPM (limite combinado entre Fable 5 e 5.1); Haiku 3.5 (legado) = 1.000 RPM / 100.000 ITPM / 20.000 OTPM. — Fonte: idem (tabela "Start tier").
- **NÃO VERIFICADO (depósito mínimo):** a documentação oficial consultada **não especifica um valor de depósito mínimo em dólares** para entrar no tier Start — ela descreve apenas que o tier é atribuído "automatically based on usage history and account standing". Buscas na web (fontes terceiras, não oficiais, como blogs de terceiros) mencionam um valor histórico de US$ 5 associado ao antigo "Tier 1", mas isso **não foi confirmado em página oficial nesta sessão** e pode estar desatualizado frente à nomenclatura Start/Build/Scale atual. Recomenda-se checar o valor exato diretamente em https://platform.claude.com/settings/billing ao criar a conta.
- **Fato (Batch tem limites separados):** sim — RPM próprio (compartilhado entre todos os modelos), mais um limite de "batch requests em fila de processamento" e um limite de "requests por batch" (100.000, igual ao limite geral de batch). No tier Start: 1.000 RPM / 200.000 na fila / 100.000 por batch. — Fonte: https://platform.claude.com/docs/en/api/rate-limits (seção "Message Batches API").
- **Fato (cache-aware ITPM):** tokens lidos do cache (`cache_read_input_tokens`) **não contam** para o limite de ITPM na maioria dos modelos (exceção: Haiku 3.5), o que efetivamente aumenta o throughput real quando se usa prompt caching agressivamente. — Fonte: idem.

### B.5 Web search / web fetch na API

- **Fato (web search — preço):** "Web search is available on the Claude API for **$10 per 1,000 searches**, plus standard token costs for search-generated content." Cada busca conta como um uso, independentemente do número de resultados; se der erro, a busca não é cobrada. — Fonte: https://platform.claude.com/docs/en/about-claude/pricing (seção "Web search tool").
- **Fato (web fetch — preço):** "The web fetch tool is available on the Claude API at **no additional cost**. You only pay standard token costs for the fetched content." — Fonte: idem.
- **Implicação para o projeto:** buscar "o Evangelho do dia" via `web_search` custaria US$ 0,01 por chamada (1 busca = US$ 10/1000) mais tokens de input do conteúdo retornado — tecnicamente viável, mas como o usuário já indicou que provavelmente não vai usar esse caminho (preferindo fonte fixa/local do Evangelho), não é necessário no MVP.

---

## Tabela de preços consolidada (USD por MTok — Claude API, first-party)

Fonte única para toda a tabela: https://platform.claude.com/docs/en/about-claude/pricing (verificada nesta sessão em 2026-09-25).

| Modelo | Input | Output | Cache write 5m (1,25×) | Cache write 1h (2×) | Cache read (hit) | Batch input (50%) | Batch output (50%) |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 | $10,00 | $50,00 | $12,50 | $20,00 | $0,25 (0,025×) | $5,00 | $25,00 |
| Claude Opus 5.5 | $4,00 | $20,00 | $5,00 | $8,00 | $0,20 (0,05×) | $2,00 | $10,00 |
| Claude Opus 5 | $5,00 | $25,00 | $6,25 | $10,00 | $0,50 (0,1×) | $2,50 | $12,50 |
| Claude Sonnet 5 | $2,00 | $10,00 | $2,50 | $4,00 | $0,20 (0,1×) | $1,00 | $5,00 |
| Claude Haiku 4.5 | $1,00 | $5,00 | $1,25 | $2,00 | $0,10 (0,1×) | $0,50 | $2,50 |

Observações importantes que afetam custo real:
- **Batch + cache acumulam** (ex.: Sonnet 5 em batch com cache hit fica ainda mais barato que os valores isolados acima, pois os multiplicadores se aplicam em conjunto).
- **`inference_geo: "us"`** aplica 1,1× sobre todos os componentes de preço (não usado por padrão — padrão é `"global"`).
- Web search: **+US$ 10 por 1.000 buscas**, cobrado à parte, se usado.
- Sonnet 5 tem preço "de lançamento tornado padrão": não haverá o aumento antes previsto para 1º de setembro de 2026.

---

## Riscos e NÃO VERIFICADOS

1. **Schema JSON exato de `claude -p --output-format json`** (campos `total_cost_usd`, `usage`, `duration_ms`, `num_turns`) — a página de headless redirecionou para a doc do Agent SDK (produto correlato, não o CLI). Recomenda-se rodar localmente `claude -p "teste" --output-format json` e inspecionar o JSON real antes de construir o parser do GitHub Action.
2. **Depósito mínimo para o tier "Start"** da API — não encontrado em página oficial atual; nomenclatura de tiers mudou de "Tier 1-4" para "Start/Build/Scale/Custom" e o valor de US$ 5 citado por blogs de terceiros não foi confirmado oficialmente nesta sessão.
3. **Conteúdo exato do `.jsonl` de transcrição** (`~/.claude/projects/.../*.jsonl`) quanto a conter ou não o objeto `usage` por mensagem — a doc oficial menciona que dados agregados de custo ficam em `stats-cache.json`, separado do transcrito bruto; não há confirmação textual oficial de que cada mensagem no `.jsonl` carrega tokens de input/output. Requer inspeção empírica de um arquivo real.
4. **Cláusula de Termos de Uso sobre CI/automação com assinatura Pro/Max** — a documentação técnica do `claude-code-action` permite e documenta `CLAUDE_CODE_OAUTH_TOKEN`, mas isso não substitui uma checagem dos Termos de Uso ao Consumidor da Anthropic para uso institucional/organizacional (ex.: para uma pastoral/organização, não pessoa física). Não foi objeto desta pesquisa.
5. **Preço em BRL** dos planos Pro/Max — não confirmado oficialmente; Anthropic cobra em USD, qualquer BRL exibido no checkout é conversão de terceiros (App Store/Play Store/processador de cartão), sujeita a câmbio do dia e possível IOF.
6. **Comandos `/context` e `/stats` isolados** — não encontrei documentação dedicada e exaustiva para eles nesta sessão; `/usage` parece ser hoje o comando central e `/insights` o de análise de padrões (não de custo).

---

## Implicações para o projeto (geração semanal de conteúdo para Instagram)

Considerando o volume esperado (geração semanal, baixo throughput, não tempo-sensível):

- **Sessão interativa no Claude Code (Pro/Max) é o caminho de menor atrito** para prototipagem e para revisão humana no loop (usa subagentes com modelo fixado por tarefa — ex. `model: haiku` para tarefas simples de formatação, Sonnet/Opus para redação), mas os limites de uso do plano não são expressos em tokens, dificultando estimar headroom exato; e o consumo de tokens por subagente **não é diretamente auditável** hoje (apenas % de atribuição em `/usage`).
- **GitHub Action com API + Batch + prompt caching é o caminho de menor custo e mais auditável** para um pipeline semanal automatizado: como o conteúdo não é urgente (roda 1×/semana, prazo de até 24h é aceitável), o desconto de 50% do Batch API mais cache de prompt (system prompt/brand voice fixos, 1h TTL) reduz o custo por post drasticamente — ex.: com Sonnet 5, batch input $1/MTok + leitura de cache a $0,20/MTok (0,1× sobre $2, batch já aplicado) é uma fração do custo de sessão interativa equivalente.
- **Uso de `CLAUDE_CODE_OAUTH_TOKEN` (assinatura Max) dentro do GitHub Action é tecnicamente suportado e documentado oficialmente**, mas não oferece os descontos de Batch API nem a granularidade de custo por chamada que a API "pura" oferece — é a opção certa apenas se o objetivo for reaproveitar um plano Max já pago em vez de pagar por token via API.
- **Token counting** (`/v1/messages/count_tokens`, gratuito) deve ser usado no CI para medir o tamanho do "cartão de marca"/brand voice/system prompt fixo antes de rodar o batch de verdade, evitando surpresas de custo.
- **Web search da API não é necessária** para buscar o Evangelho do dia — mais barato e mais confiável usar uma fonte de dados própria (arquivo/calendário litúrgico local) e reservar tokens de input só para o texto relevante, evitando o custo de US$ 10/1000 buscas e a variabilidade de resultados de busca.
