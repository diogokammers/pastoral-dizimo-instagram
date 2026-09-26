# ADR-009 — Prévia semanal, e-mail de aprovação e Worker (fatias 5 e 6)

Data: 2026-09-26. Status: aceito (implementado e testado localmente; **sem deploy, sem segredos cadastrados,
nenhuma API real chamada**). Depende do ADR-008 (formato do `aprovacao.json`).

## Contexto
A arquitetura (§1, §1.1, §5) prevê um único portão humano: um e-mail semanal com links assinados que levam a
um Worker da Cloudflare, o qual grava `aprovacao.json` assinado para o `publicar.py` aceitar. Não há domínio
próprio (Worker em `*.workers.dev`, e-mail sem domínio verificado na Resend) e o repositório é público.

## Decisões
1. **Prévia semanal** (`python -m pastoral.preview --semana AAAA-Www`): lê `content/semanas/<semana>/`
   (`posts.json`, `briefing.json`, `render/`), grava `agenda.json` (para cada post: `agendado_para` com fuso,
   calculado de `data`+`hora`+`fuso` do briefing, e a lista das artes), copia as artes para
   `site/midia/<semana>/` (as URLs públicas que o `publicar.py` usa; artes velhas da mesma semana são
   apagadas) e gera `site/semanas/<semana>/index.html`, que aponta para essas mesmas imagens. Convenção:
   `numero` do post = `indice` do briefing (posição global da série).
2. **Regras comuns em `src/pastoral/aprovacao.py`**, espelhadas em `worker/src/nucleo.js`:
   - itens = exatamente os `posts[]` do ADR-008 (`numero`, `agendado_para`, `legenda_sha256`,
     `alt_text_sha256`, `artes[{arquivo, sha256}]`), com o mesmo `texto_legenda`/`texto_alt` do portão
     (no JS, o `strip()` do Python é reproduzido com o conjunto exato de `str.isspace()`);
   - **versão** = 32 primeiros hex do sha256 do JSON canônico `{semana, posts: itens}`;
   - **link** = HMAC-SHA256 (`LINK_HMAC_SECRET`) sobre `pastoral-link-v1` + `s` (semana), `a` (ação),
     `p` (post; vazio em `aprovar_tudo`), `e` (expiração, epoch, 7 dias), `n` (nonce próprio de cada link) e
     `v` (versão), um por linha; hex minúsculo em `h`. Formatos validados antes do HMAC (só ASCII).
3. **E-mail** (`python -m pastoral.notificar AAAA-Www`): API HTTP da Resend (`POST /emails`, `urllib`,
   User-Agent próprio), remetente `onboarding@resend.dev`, destinatário `aprovacao.email` do `config.yaml`
   (`pastoraldodizimo.arquifln@gmail.com`, que precisa ser o dono da conta Resend). Corpo HTML simples:
   resumo de cada post, link da prévia no Pages e botões "Aprovar tudo", "Aprovar post N",
   "Pedir ajuste no post N". `RESEND_API_KEY` e `LINK_HMAC_SECRET` só por ambiente, com `strip()` e chave
   mascarada nos erros. Envio real recusado enquanto `aprovacao.worker_url` for o placeholder.
   `--dry-run` grava o HTML **fora do repositório** (os links são credenciais de aprovação).
4. **Worker** (`worker/`, ES modules, sem dependências): `GET /a` valida HMAC (`crypto.subtle.verify`,
   comparação em tempo constante) e expiração e **só mostra** a confirmação (ou o formulário de ajuste) —
   o pré-carregamento de links do Gmail não aprova nada. `POST /a` valida de novo e:
   - **aprovar**: lê pela Contents API (`application/vnd.github.raw+json`) `agenda.json`, `posts.json` e as
     artes em `site/midia/<semana>/`, calcula os sha256, confere a versão do link (conteúdo mudou → 409,
     nada gravado), junta ao `aprovacao.json` existente (cuja assinatura precisa conferir), assina com
     `APROVACAO_HMAC_SECRET` e commita (`PUT /contents`, com releitura em conflito de `sha`);
   - **ajustar**: grava `content/semanas/<semana>/ajuste-<n>.json` (`semana`, `post`, `texto` ≤ 2000,
     `pedido_em`, `nonce`) e dispara `repository_dispatch` com `event_type: ajustar_post`.
   Idempotência: mesmo nonce (link já usado) ou posts já aprovados com o mesmo conteúdo → nenhum commit.
   `aprovado_em` em UTC (`+00:00`); `aprovado_por` = `APROVADO_POR` do `wrangler.toml`.
   Páginas com CSP `default-src 'none'`, `no-store`, `noindex`; o PAT é mascarado em qualquer erro.
5. **Teste cruzado Python ↔ JS**: `python -m pastoral.aprovacao --vetores tests/fixtures/vetores-python.json`
   gera casos (JSON canônico com acentos, controles, chaves astrais × BMP alto, HMAC, strip da legenda,
   itens/versão da semana de exemplo, links e um `aprovacao.json` completo) que o `node:test` verifica byte a
   byte; `node worker/scripts/vetor-worker.mjs` roda o Worker de verdade (GitHub falso) e grava
   `tests/fixtures/semana-exemplo/aprovacao-worker.json`, que o pytest passa pelo `publicar.avaliar_semana`.
   O pytest também confere que os dois arquivos versionados estão atualizados (regenera e compara).
6. **Testes JS com `node:test`** (embutido no Node ≥ 20), não vitest: zero dependências e nenhum
   `npm install`. `fetch` é sempre mockado (`worker/test/github-falso.js`).
7. **`semanal.yml`**: cron segunda 09:00 UTC + manual; job real só com a variável `SEMANAL_ATIVO = 1`
   (hoje desligado, sem data de estreia — ADR-005). Sem `CLAUDE_CODE_OAUTH_TOKEN`, falha com mensagem clara.
   Como push feito com `GITHUB_TOKEN` não dispara outros workflows, o job chama `gh workflow run pages.yml`.
8. Segredos com quebra de linha no fim (comum ao colar ou usar pipe no PowerShell) são aparados em todos os
   lados (`notificar.py`, `publicar.py`, Worker), então o mesmo segredo vale no GitHub e no Worker.

## Passos que exigem o Diogo (nesta ordem)
1. Criar conta gratuita na Cloudflare (se ainda não tiver).
2. `cd worker` e `npx wrangler login` (ele loga no navegador).
3. `npx wrangler deploy` (dentro de `worker/`). Na primeira vez o wrangler pode pedir para registrar o
   subdomínio `*.workers.dev`. Anotar a URL impressa: `https://pastoral-dizimo-aprovacao.<subdominio>.workers.dev`.
4. Trocar `aprovacao.worker_url` no `config.yaml` por essa URL e commitar.
5. Segredos HMAC, gerados e gravados sem aparecer na tela (exigem `gh auth login`):
   `powershell -ExecutionPolicy Bypass -File scripts\gerar-segredos-hmac.ps1` (ou `bash scripts/gerar-segredos-hmac.sh`).
   O script faz, para cada um, `gh secret set` e `npx wrangler secret put` (via stdin) com o mesmo valor:
   - `npx wrangler secret put LINK_HMAC_SECRET`
   - `npx wrangler secret put APROVACAO_HMAC_SECRET`
6. PAT do Worker: GitHub → Settings → Developer settings → Fine-grained tokens → Generate; *Repository
   access*: só `pastoral-dizimo-instagram`; *Permissions*: **Contents: Read and write** (nada mais);
   expiração a critério (ex.: 1 ano, com lembrete). Depois, dentro de `worker/`:
   `npx wrangler secret put GH_PAT_WORKER` e colar o token quando pedir.
7. Resend: criar a conta **com `pastoraldodizimo.arquifln@gmail.com`**, gerar API key (Sending access) e
   `gh secret set RESEND_API_KEY`.
8. Geração no Action: `claude setup-token` e `gh secret set CLAUDE_CODE_OAUTH_TOKEN`.
9. Conferência sem aprovar nada: abrir `https://…workers.dev/a` → deve mostrar "Link recusado — link
   malformado" (se mostrar "Worker sem configuração", faltam os segredos do passo 5).
10. Só depois da estreia e de definir `pauta.semana_inicial`: `gh variable set SEMANAL_ATIVO --body 1`.

## Consequências e riscos
- Ninguém consome ainda o evento `ajustar_post`: o pedido fica gravado em `ajuste-<n>.json`, mas refazer
  só aquele post é uma fatia futura (até lá, o Diogo roda a geração à mão).
- Repositório público: o texto do ajuste fica público (o formulário avisa para não escrever dado pessoal).
- Os links do e-mail aprovam a publicação: não encaminhar o e-mail. Validade de 7 dias; reenviar o e-mail
  da semana gera links novos. Trocar os segredos invalida links e aprovações anteriores.
- Resend sem domínio só entrega ao e-mail dono da conta; mandar para outra pessoa exige domínio verificado.
- Plano Free do Workers: 10 ms de CPU por requisição. O sha256 das artes usa `crypto.subtle` (nativo), mas
  semanas com muitas artes grandes podem encostar no limite; se acontecer, a mensagem será de erro do
  Worker e nada é gravado (aprovação por link não fica "meio feita").
- O Pages leva ~1 min para publicar após o `gh workflow run pages.yml`; o e-mail pode chegar antes da prévia
  estar no ar. O Worker não depende do Pages (lê o repositório).
- Não verificado nesta sessão: `npx wrangler deploy` real, entrega real da Resend e escopo do PAT
  fine-grained para `/dispatches` (a documentação do GitHub indica Contents: write).
