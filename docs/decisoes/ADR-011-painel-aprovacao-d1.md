# ADR-011 — Painel de aprovação com banco D1, código de acesso e link curto

Data: 2026-09-27. Status: aceito (implementado, testado e validado de ponta a ponta em ambiente de teste
isolado; produção implantada — evidências em `docs/validacao/2026-09-27-painel-aprovacao.md`).
Depende do ADR-008 (portão e `aprovacao.json`) e do ADR-009 (Worker, JSON canônico, links do e-mail).

## Contexto
O simulador (`site/aprovacao/`) virou o instrumento de trabalho do Padre, mas guardava as respostas só no
aparelho (localStorage) e mandava um resumo por WhatsApp: nada chegava ao portão de publicação e nada
ficava registrado. O Diogo pediu: posts publicados fora de "Pendentes"; "Agendadas" só com aprovados;
um banco que não perca nenhuma decisão; aprovar no painel = aprovar pelo link do e-mail; desfazer que
realmente impede a publicação; acesso por código secreto; link curto; CORS restrito; validação real.

## Decisões
1. **Banco: Cloudflare D1** (`pastoral-aprovacoes`, conta da Pastoral), ligado ao Worker como `env.DB`.
   Migrations versionadas em `worker/migrations/` (`0001_eventos.sql`). Tabela **`eventos` append-only**
   (`id`, `post`, `semana`, `acao` aprovar|ajustar|desfazer, `comentario`, `versao_conteudo`, `autor`,
   `criado_em` UTC, `origem` painel|email, `commit_sha`, `ip_hash`), com gatilhos que **recusam UPDATE e
   DELETE**, e a visão **`estado_atual`** (último evento de cada post). Nenhum código apaga eventos.
2. **Versão do conteúdo por post**: `aprovacao.versao_post(semana, item)` (Python) = `versaoPost` (JS) =
   32 hex do sha256 do JSON canônico `{semana, post: item}`, onde `item` é o `posts[]` do ADR-008
   (legenda, alt-texts, artes e data). A página leva `data-versao` (calculado de `site/midia/`, o que o
   Pages mostra); o Worker recalcula a partir do GitHub e **recusa aprovar (409)** se não bater.
   Se o conteúdo mudar depois de uma resposta, a versão guardada deixa de bater: a página devolve o post
   a "Pendentes" e o portão já recusa por hash.
3. **API no mesmo Worker** (`worker/src/painel.js`): `GET /api/estado` e `POST /api/decisao`
   (`{semana, post, acao, versao, comentario}`). Reaproveita o núcleo: `acoes.js` concentra ler a semana,
   calcular itens, gravar `aprovacao.json` assinado (com releitura em conflito) e registrar ajuste — o
   link do e-mail (`/a`) passou a usar as mesmas funções.
   - **aprovar** = o que o `POST /a` de `aprovar_post` faz (ADR-009): confere os hashes no GitHub,
     mescla e assina `aprovacao.json` (`APROVACAO_HMAC_SECRET`) e commita; o `publicar.py` o publica na
     data agendada quando `PUBLICAR_ATIVO=1` (**continua desligado**).
   - **ajustar** = grava `ajuste-<n>.json` + `repository_dispatch` (evento `EVENTO_AJUSTE`, padrão
     `ajustar_post`) e **tira o post do `aprovacao.json`** (post com ajuste pedido não pode sair). O link
     do e-mail de ajuste passou a fazer o mesmo.
   - **desfazer** = `removerDaAprovacao` / `remover_da_aprovacao`: tira o post e **reassina**; sem o post
     no arquivo, o portão não o publica. Espelho Python↔JS verificado por vetor.
   - Ordem: GitHub primeiro, D1 depois. Idempotente: mesma decisão sobre a mesma versão não gera commit
     nem evento; se o D1 falhar depois do commit, a resposta avisa e tocar de novo só registra o evento.
   - Decisões feitas pelos links do e-mail também viram eventos (`origem = email`).
4. **Backup fora do D1**: depois de cada decisão (`waitUntil`) e todo dia às 06:30 de Brasília (cron do
   Worker), o D1 inteiro é exportado para `content/aprovacoes/eventos.jsonl` (um evento por linha, JSON
   canônico, ordem do id; sem commit se nada mudou). O `ip_hash` **não** vai para o backup (repo público).
5. **Acesso por código (capability)**: segredos do Worker `CODIGO_PADRE` (autor "Padre") e, quando
   existir, `CODIGO_DIOGO` (autor "Diogo") — basta o secret; o par código→autor está em `acesso.js`.
   24 bytes aleatórios em base64url (192 bits). Validação: formato, sha256 dos dois lados e comparação
   sem saída antecipada, conferindo todos os códigos. O código vai **só** no header
   `Authorization: Bearer`; nunca em URL. A página é pública; sem código ela fica **só leitura**.
6. **Link curto**: `/p/<código>` responde 302 para a página do Pages com o código no **fragmento**
   (`#c=…`), que não vai ao Pages, a logs nem ao Referer; a página grava o código só no aparelho e o
   apaga da barra de endereço. Para encurtar, um segundo Worker **`aprovar`** (`wrangler --env curto`,
   `src/curto.js`: só o redirecionamento, sem segredos/banco/GitHub) dá
   `https://aprovar.pastoral-dizimo-aprovacao.workers.dev/p/<código>`. O Worker antigo continua com
   `/a`, `/api` e `/p/`. Nada de encurtador de terceiros. Logs de invocação desligados.
7. **CORS**: `/api/*` exige `Origin: https://diogokammers.github.io` (`ORIGEM_PERMITIDA`); outro origin ou
   nenhum → 403 sem tocar em nada. A página tem CSP (`connect-src` só a API, `img-src 'self'`) e
   `referrer no-referrer`. CORS não é autenticação: quem autentica é o código.
8. **Página** (`python -m pastoral.simulador`): "Pendentes" só com posts **não publicados** (ledger da
   estreia e das semanas); "Agendadas" começa vazia e mostra só os aprovados (data do `agenda.json`,
   provisória); sai a frase "nada disso foi publicado ainda…" e o botão de WhatsApp (a resposta é gravada
   na hora). `--api`, `--destino`, `--semanas`, `--site` geram a página de teste.
9. **Ambiente de teste** (`wrangler --env teste`): Worker `pastoral-dizimo-aprovacao-teste`, D1
   `pastoral-aprovacoes-teste`, ramo `teste-aprovacao`, evento `ajustar_post_teste` (nada o consome).
   Roteiro real em `scripts/e2e_painel.py` (recusa produção). Depois da validação, tudo de teste é apagado.
10. Testes: `worker/test/painel.test.js` usa um D1 falso sobre `node:sqlite` (Node ≥ 22.13) com as
    **mesmas migrations**; `tests/test_painel_worker.py` passa o `aprovacao.json` do painel pelo portão;
    `tests/test_simulador_navegador.py` roda o JS da página no Chromium (Playwright) com a API simulada.

## Operação (sempre com o login da Pastoral, dentro de `worker/`)
`W() { env -u CLOUDFLARE_API_TOKEN -u CLOUDFLARE_ACCOUNT_ID XDG_CONFIG_HOME="C:/Users/odnac/.config-pastoral-dizimo" npx wrangler "$@"; }`
- Deploy: `W deploy` (principal) e `W deploy --env curto` (link curto).
- Migrations: `W d1 migrations apply pastoral-aprovacoes --remote`.
- Novo código (ou revogar o atual): gerar e gravar sem exibir, p. ex.
  `python -c "import secrets;print(secrets.token_urlsafe(24),end='')" > arq && W secret put CODIGO_PADRE < arq`,
  montar o link `https://aprovar.pastoral-dizimo-aprovacao.workers.dev/p/<código>` e entregar por canal
  seguro; apagar o arquivo. Trocar o secret invalida o link antigo na hora.
- Segundo aprovador: `W secret put CODIGO_DIOGO` (mesmo procedimento).
- Consultar: `W d1 execute pastoral-aprovacoes --remote --command "SELECT * FROM estado_atual"`.

## Consequências e riscos
- O D1 é a fonte do "estado" do painel; o `aprovacao.json` assinado continua sendo a única coisa que o
  portão aceita. Se alguém mexer no `aprovacao.json` à mão, o painel pode divergir até a próxima decisão.
- Plano Free do Workers: 10 ms de CPU por pedido. Aprovar lê e faz hash só das artes do post decidido
  (validado com um carrossel real de 10 artes, ~1 MB). Semanas maiores não mudam isso.
- Cada decisão gera 1–2 commits (decisão + backup) na master; o backup não dispara o Pages.
- O texto dos ajustes e os eventos (sem IP) ficam públicos no repositório: o painel avisa para não
  escrever dado pessoal.
- Quem tiver o link pode decidir como "Padre": não encaminhar; se vazar, trocar o `CODIGO_PADRE`.
- As respostas que o Padre tenha marcado na versão anterior da página (só no aparelho dele) não migram.
