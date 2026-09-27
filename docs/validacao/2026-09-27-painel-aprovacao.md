# Validação do painel de aprovação (ADR-011) — 2026-09-27

> Registro histórico da primeira versão. Depois disso o ADR-012 trocou o acesso por link com código por
> rascunho + envio com código, renomeou o autor gravado para "Aprovador" e desativou `/p/<código>`;
> a validação dessa versão está em `2026-09-27-painel-rascunho-envio.md`.

Tudo abaixo foi executado de verdade nesta data. Os códigos de acesso e segredos nunca aparecem aqui
(nas saídas dos scripts o código é trocado por `<CODIGO>`). Horários em UTC.

## 1. Testes automatizados
| Suíte | Resultado |
|---|---|
| `PYTHONPATH=src python -m pytest -q` | **362 passed** (inclui `test_painel_worker.py`: o `aprovacao.json` gravado pela API do Worker passa no `publicar.avaliar_semana`; o desfazer tira o post do portão; e `test_simulador_navegador.py`: o JS da página no Chromium com a API simulada) |
| `cd worker && npm test` | **54 pass, 0 fail** (inclui `painel.test.js`: D1 falso sobre `node:sqlite` com as migrations reais — gatilhos append-only, CHECKs, visão `estado_atual`) |
| Vetores cruzados | `versao_post` e `remover_da_aprovacao` do Python reproduzidos byte a byte no JS |

## 2. Ponta a ponta com chamadas HTTP reais (ambiente de TESTE isolado)
- Worker `pastoral-dizimo-aprovacao-teste` (`wrangler deploy --env teste`), D1 `pastoral-aprovacoes-teste`
  (migration `0001_eventos.sql` aplicada remotamente: tabela, índice, visão e os 2 gatilhos),
  ramo `teste-aprovacao` (base `dafb3df` = master + semana de TESTE `2099-W01`), evento de dispatch
  `ajustar_post_teste` (nenhum workflow o consome). Segredos de teste próprios, gerados e gravados por stdin.
- Semana de teste: post **901** = cópia do post 10 (carrossel de **10 artes reais**, ~1 MB — custo de CPU
  realista no plano Free) e post **902** = cópia do post 6 (1 arte).
- Roteiro: `scripts/e2e_painel.py` (recusa produção). O portão foi rodado localmente sobre os arquivos do
  ramo com o segredo de teste e `agora = 2099-02-01`.

| # | Passo | Resultado (status HTTP · commit no ramo · D1) |
|---|---|---|
| 1 | Preflight `OPTIONS` do origin permitido | 204, `Access-Control-Allow-Origin: https://diogokammers.github.io` |
| 2 | Código errado / ausente (estado e decisão) | 401 / 401 / 401 · nenhum commit (último commit da semana = `dafb3df`) · D1 = 0 eventos |
| 3 | Origin `https://evil.example` / sem Origin, **com código válido** | 403 / 403 / 403, sem cabeçalho CORS · nenhum commit · D1 = 0 |
| 4 | `GET /api/estado` com código | 200 com o autor do código e `posts` vazio, `Cache-Control: no-store` |
| 5 | Aprovar 901 (versão `246dd267…`) | 200 · commit `a43829d` · `aprovacao.json` com `aprovado_por` = autor do código, assinatura válida · portão: **prontos [901]** · D1 id 1 (`commit_sha a43829d`, `ip_hash` gravado) |
| 6 | Aprovar 901 de novo | 200 `idempotente: true` · nenhum commit de decisão · D1 continua com 1 evento |
| 7 | Aprovar 902 com versão velha | **409** `conteudo_mudou` · nada gravado |
| 8 | Aprovar 902 | 200 · commit `2e7a50e` · portão: **prontos [901, 902]** |
| 9 | Desfazer 901 | 200 · commit `1770131` · `aprovacao.json` = [902], reassinado e válido · portão: **prontos [902]** (901 não sai) |
| 10 | Desfazer 901 de novo | 200 `idempotente: true` · nenhum commit · D1 = 3 |
| 11 | Pedir ajuste 902 | 200 · commits `2623e3f` (902 sai da aprovação) e `41edf7d` (`ajuste-902.json` com o texto) · portão: prontos [] · o 200 só sai depois de o GitHub aceitar o `repository_dispatch` (204) |
| 12 | Mesmo ajuste de novo | 200 `idempotente: true` · sem arquivo nem dispatch novo · D1 = 4 |
| 13 | Aprovar 901, depois **mudar a legenda** no ramo (commit `7496a61`) | `GET /api/estado`: versão aprovada `246dd267…` ≠ atual `1ba740d8…` (a página devolve o post a Pendentes) · portão: **901 recusado — "legenda difere da aprovada"** · aprovar com a versão velha → **409** |
| 14 | Aprovar 901 na versão nova | 200 · commit `d52f9fc` · portão: prontos [901]. *O script conferiu o portão antes de atualizar o checkout e marcou falha; reconferido em seguida com o CLI real (`python -m pastoral.publicar --semana 2099-W01 --agora 2099-02-01… --dry-run` → `[ok] post 901: publicaria (10 artes)`) e o script foi corrigido.* |
| 15 | Backup | `content/aprovacoes/eventos.jsonl` no ramo com os ids 1–6 = D1, sem `ip_hash`; um commit "aprovacoes: backup de N evento(s)" depois de cada decisão |
| 16 | `UPDATE` e `DELETE` no D1 remoto | recusados: `eventos: append-only (UPDATE proibido)` / `(DELETE proibido)` — `SQLITE_CONSTRAINT_TRIGGER` |
| 17 | `GET /p/<código>` | 302 → `…/aprovacao-teste/#c=<CODIGO>` (sem query string), `Referrer-Policy: no-referrer`, `no-store` |

## 3. Página publicada no GitHub Pages, com Playwright (Chromium)
Página de teste temporária `site/aprovacao-teste/` (commit `4cbb5b2`, Worker de teste), roteiro
`scripts/e2e_pagina.py --modo teste` — decisões **só nos posts de teste 901/902**:
- Sem código: modo só leitura, **nenhuma chamada à API**, Pendentes sem os posts 1–3 (estão em
  "Já publicadas" = [1, 2, 3]), sem botões de decisão, Agendadas vazia, sem a frase removida. ✔
- Pelo link curto: redireciona, **o código sai da barra de endereço**, "Você está aprovando como <autor>",
  `GET /api/estado` com `Authorization: Bearer <CODIGO>` e o código em nenhuma URL. ✔
- Aprovar 901 → Aprovadas + Agendadas; 901 no `aprovacao.json` do ramo (commit `e506520`). ✔
- Pedir ajuste 902 → Em ajuste com o texto; `ajuste-902.json` no ramo (commit `71a87ce`). ✔
- Recarregar a página → decisões mantidas (vêm do D1). ✔
- Desfazer 901 → volta a Pendentes, sai de Agendadas e do `aprovacao.json` (commit `d8b1d1a`). ✔
- Desfazer 902 (ajuste) → volta a Pendentes (evento sem commit: não havia aprovação a tirar). ✔
- Todas as decisões foram `POST /api/decisao` com o código só no cabeçalho. ✔

Eventos finais do D1 de teste (12, todos com o autor do código de teste, `origem = painel`, `ip_hash` presente):
1 aprovar 901 · 2 aprovar 902 · 3 desfazer 901 · 4 ajustar 902 · 5 aprovar 901 · 6 aprovar 901 (versão nova)
· 7–12 da sessão Playwright (desfazer 901, desfazer 902, aprovar 901, ajustar 902, desfazer 901, desfazer 902).

## 4. Produção (depois de tudo acima)
- D1 `pastoral-aprovacoes` com a migration aplicada; Worker `pastoral-dizimo-aprovacao` implantado
  (D1 ligado, cron `30 9 * * *`); secret do código de acesso gerado e gravado por stdin (nunca exibido);
  Worker `aprovar` (só o link curto) implantado. `PUBLICAR_ATIVO` **não** foi mexido.
- Fumaça sem alterar decisões:
  `GET /api/estado` com o código → 200 com o autor do código e `posts` vazio · `POST /api/decisao` com código
  inválido → 401 · sem código → 401 · origin errado com código válido → 403 · preflight → ACAO correto ·
  `GET /a` (link do e-mail) → 403 "link malformado" (rota antiga intacta) · `aprovar…/p/<código>` → 302
  para `…/aprovacao/#c=<CODIGO>` · outras rotas do Worker curto → 404 · `/p/` no Worker principal → 302.
- Playwright na página real (`--modo fumaca`, **nenhum clique de decisão**): sem código = só leitura,
  Pendentes = [4…11], Já publicadas = [1, 2, 3]; com o link real = modo de decisão, estado vazio.
- D1 de produção: **0 eventos** ao fim da validação.

## 5. Limpeza
Worker de teste apagado (com seus segredos, inclusive o token usado para gravar no ramo de teste),
D1 de teste apagado, ramo `teste-aprovacao` apagado, página `site/aprovacao-teste/` e artes
`site/midia/2099-W01/` removidas da master. As execuções anteriores do roteiro (uma com defeito de
medição no script e outra interrompida por um laço no próprio script) usaram D1s de teste que foram
apagados e recriados; nada disso tocou produção.

## Limitações conhecidas
- O cron diário de backup foi testado só por teste automatizado (`backupAgendado`); o disparo real às
  09:30 UTC não foi observado. O backup por decisão foi observado de verdade (passo 15).
- Não há como listar `repository_dispatch` pela API do GitHub: a prova é o 200 do Worker, que só vem
  depois de o GitHub devolver 204.
- O Worker de teste usou, temporariamente, o token do `gh` do Diogo para gravar no ramo de teste (o PAT
  fine-grained de produção não pode ser copiado de um Worker para outro); o Worker foi apagado ao fim.
