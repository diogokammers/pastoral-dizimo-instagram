# Link na bio + formulários de escuta — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Página `dizimoarquifln.pages.dev` com dois formulários (agente / fiel), respostas num D1 privado e exportação para o repositório privado `pastoral-dizimo-dados`.

**Architecture:** Uma fonte única (`content/formularios.yaml` + `content/paroquias.yaml`) gera, via `python -m pastoral.links`, a página estática (`links/public/index.html`) e o módulo de campos do servidor (`links/lib/campos.js`) — página e servidor validam contra as mesmas listas. Uma Pages Function (`links/functions/api/resposta.js`) valida e grava no D1 `pastoral-formularios`. `python -m pastoral.formularios --exportar` baixa o D1 via wrangler para o clone privado.

**Tech Stack:** Python 3 (pytest, PyYAML), JS puro (node:test + node:sqlite, Node ≥ 22.13), Cloudflare Pages Functions + D1, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-28-link-bio-formularios-design.md`

## Global Constraints
- `encoding="utf-8"` explícito em toda leitura/escrita (Windows); comentários em português; código simples.
- TDD: teste antes do código; `python -m pytest -q` e `cd links && npm test` verdes ao fim de cada tarefa.
- Nenhuma resposta de formulário no repositório público; exportador recusa pasta dentro dele.
- Textos da página: linguagem simples (ADR-010), sem `lint.TERMOS_PROIBIDOS`, sem "%", sem "dizimista" como rótulo, sem "voluntário".
- Wrangler sempre com o login da Pastoral: `env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID XDG_CONFIG_HOME="C:/Users/odnac/.config-pastoral-dizimo" npx wrangler …`.
- Credenciais: só o nome `IP_HMAC_SECRET`; o Diogo cadastra o valor.
- Commits em português com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Estrutura de arquivos
| Arquivo | Responsabilidade |
|---|---|
| `content/paroquias.yaml` | lista pública das paróquias (fonte + data) |
| `content/formularios.yaml` | versão, textos, opções de cada campo, consentimento |
| `src/pastoral/links.py` | carrega os YAML, valida coerência, gera `index.html` e `campos.js` |
| `templates/links.html` | HTML/CSS/JS da página com o marcador `/*__DADOS__*/null` |
| `links/lib/campos.js` | GERADO: `export const CAMPOS = {...}` |
| `links/lib/validar.js` | `validar(corpo, CAMPOS) -> {ok, dados, erros}` |
| `links/lib/resposta.js` | `tratar(request, env, agora) -> Response` (limite, honeypot, gravação) |
| `links/functions/api/resposta.js` | rota Pages: `onRequestPost = ({request, env}) => tratar(request, env, new Date())` |
| `links/migrations/0001_respostas.sql` | tabelas `respostas` e `envios_ip` |
| `links/test/*.test.js`, `links/test/d1-falso.js` | testes node |
| `links/wrangler.toml`, `links/package.json` | projeto Pages `dizimoarquifln` |
| `src/pastoral/formularios.py` | exportador para o repositório privado |
| `tests/test_links.py`, `tests/test_formularios.py`, `tests/test_links_navegador.py` | pytest |
| `docs/decisoes/ADR-013-link-bio-formularios.md`, `content/estreia/bio.md`, `CLAUDE.md`, `config.yaml`, `.gitignore` | docs/config |

---

### Task 1: Paróquias e definição dos formulários (dados)
**Files:** Create `content/paroquias.yaml`, `content/formularios.yaml`; Test `tests/test_links.py`
**Produces:** YAML com chaves `paroquias.yaml: {fonte, consultado_em, paroquias: [str]}`; `formularios.yaml: {versao: 1, textos: {...}, agente: {funcoes, pedidos, pedidos_com_contato, temas}, fiel: {assuntos}, consentimento: str, limites: {texto_curto: 120, texto_longo: 2000}}`.
- [ ] Conferir a lista no https://arquifln.org.br/paroquias (página e categoria), linha a linha; registrar total real.
- [ ] Teste: paróquias sem duplicatas, ≥ 70 itens, formato `Cidade - Nome` ou `Cidade - Nome (Bairro)`; temas = os 13 da spec 3.3; `pedidos_com_contato` ⊂ `pedidos`; nenhum texto com termo proibido/"%".
- [ ] Rodar (falha) → escrever YAML → rodar (passa) → commit.

### Task 2: D1 e validação no servidor
**Files:** Create `links/migrations/0001_respostas.sql`, `links/lib/validar.js`, `links/test/d1-falso.js`, `links/test/validar.test.js`, `links/package.json`
**Consumes:** `CAMPOS` com a forma `{versao, limites, paroquias, agente:{funcoes,pedidos,pedidos_com_contato,temas}, fiel:{assuntos}}` (fixture no teste até a Task 4 gerar o real).
**Produces:** `validar(corpo, CAMPOS) -> {ok: true, tipo, dados} | {ok: false, erros: [campo]}`.
SQL:
```sql
CREATE TABLE respostas (id TEXT PRIMARY KEY, criado_em TEXT NOT NULL, tipo TEXT NOT NULL CHECK (tipo IN ('agente','fiel')),
  versao_form INTEGER NOT NULL, dados TEXT NOT NULL CHECK (json_valid(dados)));
CREATE TRIGGER respostas_sem_update BEFORE UPDATE ON respostas BEGIN SELECT RAISE(ABORT, 'respostas é append-only'); END;
CREATE TABLE envios_ip (ip_hash TEXT NOT NULL, criado_em TEXT NOT NULL);
CREATE INDEX envios_ip_busca ON envios_ip (ip_hash, criado_em);
```
Regras de `validar` (casos de teste, um por linha): tipo desconhecido; agente sem paróquia; paróquia fora da lista; "Outra" sem `paroquia_outra`; função/pedido fora da lista; temas vazio ou fora da lista; descrição vazia ou > 2000; capacitação/material sem nome ou contato; sem consentimento; fiel válido sem paróquia/contato; campos extras são descartados; strings aparadas.
- [ ] Testes → falha → implementação → passa → commit.

### Task 3: Rota de resposta (limite, honeypot, gravação)
**Files:** Create `links/lib/resposta.js`, `links/functions/api/resposta.js`, `links/test/resposta.test.js`, `links/wrangler.toml`
**Consumes:** `validar`, `CAMPOS` (import de `./campos.js`).
**Produces:** `tratar(request, env, agora)`; env: `DB`, `IP_HMAC_SECRET`. IP de `CF-Connecting-IP`.
Casos: POST válido → 200 `{ok:true}` e 1 linha em `respostas` (sem IP); honeypot `site` preenchido → 200, 0 linhas; corpo > 16 KB → 413; JSON inválido → 400; inválido → 400 `{erros}`; 11º envio do mesmo IP em 1 h → 429 e nada gravado; outro IP segue livre; `envios_ip` > 1 dia apagado; sem `IP_HMAC_SECRET` → 500 sem gravar.
- [ ] Testes → falha → implementação → passa → commit.

### Task 4: Página e geração (`pastoral.links`)
**Files:** Create `templates/links.html`, `src/pastoral/links.py`, gera `links/public/index.html`, `links/lib/campos.js`; Test `tests/test_links.py`
**Produces:** `carregar(raiz) -> dict`, `montar_pagina(dados) -> str`, `montar_campos_js(dados) -> str`, `main()` grava os dois arquivos.
Testes: arquivos gerados em disco == geração atual (não ficaram velhos); página contém cada paróquia e tema; sem termo proibido/"%"; CSP sem `unsafe-eval`; fontes e paleta do `config.yaml`.
- [ ] Testes → falha → implementação → gerar → passa → commit.

### Task 5: Página no navegador
**Files:** Test `tests/test_links_navegador.py`
Servidor local com `links/public/`, rota `/api/resposta` interceptada pelo Playwright. Casos (Chromium e WebKit, viewport 390×844): os dois botões abrem o formulário certo; "Outra" mostra o campo; capacitação torna contato obrigatório; enviar sem consentimento bloqueia; envio ok mostra agradecimento; erro 429/500 mostra mensagem e preserva o texto.
- [ ] Testes → ajustes no template → passa → commit.

### Task 6: Exportador
**Files:** Create `src/pastoral/formularios.py`; Modify `config.yaml` (`formularios: {d1: pastoral-formularios, dados_dir: ../pastoral-dizimo-dados}`), `.gitignore`; Test `tests/test_formularios.py`
**Produces:** `buscar_respostas(executar) -> list[dict]` (executar = função que roda o wrangler e devolve o JSON; injetável no teste), `escrever(respostas, pasta)`, `dentro_do_repo(pasta) -> bool`, `main(argv)` com `--exportar`, `--dados-dir`, `--push`.
Testes: JSONL uma linha por resposta, ordenado; CSV com BOM, colunas fixas + temas unidos por " | "; recusa pasta dentro do repo público; commit feito no repo de dados (git temporário) e sem push por padrão; sem respostas → arquivos vazios válidos.
- [ ] Testes → falha → implementação → passa → commit.

### Task 7: Documentação
**Files:** Create `docs/decisoes/ADR-013-link-bio-formularios.md`; Modify `content/estreia/bio.md`, `CLAUDE.md` (comandos), `docs/arquitetura.md` se listar componentes.
- [ ] Escrever → `python -m pytest -q` → commit.

### Task 8: Implantação (com o Diogo)
- [ ] `wrangler d1 create pastoral-formularios` → id no `links/wrangler.toml`; `wrangler d1 migrations apply pastoral-formularios --remote`.
- [ ] `wrangler pages project create dizimoarquifln --production-branch master`; conferir endereço.
- [ ] Diogo: `wrangler pages secret put IP_HMAC_SECRET --project-name dizimoarquifln` (valor aleatório, fora da conversa).
- [ ] `wrangler pages deploy public --project-name dizimoarquifln` (de dentro de `links/`).
- [ ] Teste real: um envio de teste marcado "TESTE" → exportar → apagar a linha de teste no D1.
- [ ] `gh repo create diogokammers/pastoral-dizimo-dados --private` + clone na pasta irmã; primeira exportação.
- [ ] Diogo troca o link na bio pelo app.
