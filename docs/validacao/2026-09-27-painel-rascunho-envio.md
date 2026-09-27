# Validação do painel com rascunho e envio por código (ADR-012) — 2026-09-27

Tudo executado de verdade nesta data. Nenhum código aparece aqui (nas saídas dos scripts ele é mascarado);
o ambiente de teste usou um código de teste próprio, de 4 letras, diferente do de produção.

## 1. Testes automatizados
- `PYTHONPATH=src python -m pytest -q` → **365 passed** (inclui o JS da página no Chromium e, no celular,
  WebKit "iPhone 13"/"iPhone SE" e Chromium "Pixel 7" com o fluxo por toque; o teste do celular **falha com
  o código antigo** — conferido revertendo a correção).
- `cd worker && npm test` → **55 pass, 0 fail** (código curto e sensível a maiúsculas; 5 erros → 429 por
  15 min, outro IP livre, libera depois de 15 min, acerto apaga as falhas, falhas antigas apagadas, IP só
  como hash; GET público sem `ip_hash`; lote misto com 409; lote inválido → 400 sem gravar; `/p/` → 404;
  Worker `aprovar` redireciona a raiz).

## 2. Ponta a ponta com HTTP real (ambiente de TESTE isolado)
Worker `pastoral-dizimo-aprovacao-teste`, D1 `pastoral-aprovacoes-teste` (migrations 0001 e 0002 aplicadas
remotamente), ramo `teste-aprovacao` (base `e8f5ef1`, semana 2099-W01: post 901 = 10 artes reais, 902 = 1
arte), evento `ajustar_post_teste`. Roteiro `scripts/e2e_painel.py`: **20/20 passos OK**.

| Passo | Resultado |
|---|---|
| GET `/api/estado` sem código | 200 `{"posts":{}}`, sem `ip_hash` |
| Código com maiúsculas/minúsculas trocadas / sem código | 401 (restam 4 / 3) · nenhum commit · D1 = 0 eventos |
| Origin errado ou ausente, com código certo | 403 · nada gravado |
| 5º código errado / código certo durante o bloqueio | **429** "Tente de novo depois das 16:05 (horário de Brasília)" · 5 linhas em `falhas_acesso` (hash de 16 hex) · nada gravado |
| Falhas apagadas no D1 | liberado |
| Código certo: aprovar 901 | commit `9221150` · `aprovado_por: Aprovador`, assinatura válida · portão: **prontos [901]** · falhas do IP zeradas |
| Aprovar 901 de novo | idempotente (sem commit, sem evento) |
| **Lote misto num pedido**: 902 com versão velha + desfazer 901 | 902 → **409** `conteudo_mudou`; 901 desfeito mesmo assim (commit `9ed8099`) · portão: prontos [] |
| Lote com 901 (10 artes) + 902 | commits `ae87987` e `0f363a8` · portão: prontos [901, 902] |
| Desfazer 901 | commit `d4fe65e` · `aprovacao.json` = [902], reassinado · portão: prontos [902] |
| Desfazer de novo | idempotente |
| Pedir ajuste 902 | commit `289f5db` (`ajuste-902.json`) · sai da aprovação · dispatch aceito (senão seria 502) |
| Mesmo ajuste de novo | idempotente |
| Legenda do 901 muda depois da aprovação | versão guardada `246dd267…` ≠ atual `1ba740d8…` · portão: "legenda difere da aprovada" · aprovar com a versão velha → 409 |
| Aprovar 901 na versão nova | commit `0258afd` · portão: prontos [901] |
| Backup | `content/aprovacoes/eventos.jsonl` no ramo = ids 1–8 do D1, sem `ip_hash` |
| UPDATE/DELETE em `eventos` | recusados pelo gatilho append-only |
| `/p/<qualquer coisa>` | 404 |

Eventos do D1 de teste (todos `autor = Aprovador`): 1 aprovar 901 · 2 desfazer 901 · 3 aprovar 901 ·
4 aprovar 902 · 5 desfazer 901 · 6 ajustar 902 · 7 aprovar 901 · 8 aprovar 901 (versão nova).

## 3. Página publicada (Pages) com Playwright — `scripts/e2e_pagina.py`
Página de teste temporária `site/aprovacao-teste/` (commit `df33814`, Worker de teste):
- Computador (Chromium): abre sem código (GET público, sem `Authorization`), publicados fora de Pendentes,
  nenhuma menção ao cargo · **rascunho** de aprovar 901 e ajuste 902 aparece "a enviar" e **nada chega ao
  servidor** (ramo inalterado) · recarregar mantém o rascunho · **Enviar com o código de caixa trocada →
  recusado**, nada gravado, rascunho mantido · **código certo** → 901 no `aprovacao.json` do ramo e
  `ajuste-902.json` com o texto, Agendadas = [901] · **Desfazer (rascunho) + Enviar** → 901 sai do
  `aprovacao.json`, Agendadas vazia · **5 códigos errados** → mensagem de bloqueio; o código certo também
  é recusado; nada gravado. As falhas do teste foram apagadas no D1 de teste em seguida.
- Celular, pelo toque (1 captura por cenário): **WebKit "iPhone 13" (390×664)** e **Chromium "Pixel 7"
  (412×839)**, com isMobile/hasTouch/userAgent reais: rascunho → Enviar → código → gravado no ramo
  (Agendadas = [901]) → Desfazer → Enviar → removido. OK nos dois.
- Uma execução anterior parou por defeito do roteiro (o post aprovado vai para o bloco "Aprovadas", que
  começa fechado, e o roteiro tentava tocar num botão escondido); corrigido o roteiro, a página não mudou.

## 4. Celular: causa do painel "sumido" e correção
- Reproduzido na página publicada antiga: no **WebKit** ("iPhone 13", "iPhone SE") o toque em
  "Aprovações (8 pendentes)" terminava em `scrollY = 0`; no Chromium ("Pixel 7") descia até o painel.
- Instrumentação dos eventos: `popstate` (y=0) → `scrollTo({top:0})` → `hashchange`. O manipulador de
  `popstate` chamava `fechar()` → `rolarPara(0)` sempre que não havia post no histórico. Desligando só esse
  manipulador, o mesmo toque chegava a y = 917. Sem erros de console; `localStorage` não era a causa.
- Correção descrita no ADR-012 §8; teste de regressão em `tests/test_simulador_navegador.py`.

## 5. Produção
- D1 `pastoral-aprovacoes`: migration 0002 aplicada. Secret `CODIGO_APROVADOR` gravado por stdin;
  **`CODIGO_PADRE` apagado** (lista de secrets: APROVACAO_HMAC_SECRET, CODIGO_APROVADOR, GH_PAT_WORKER,
  LINK_HMAC_SECRET). Workers `pastoral-dizimo-aprovacao` e `aprovar` reimplantados. `PUBLICAR_ATIVO` intocado.
- Fumaça sem gravar decisões: GET estado sem código → 200 `{"posts":{}}` (sem `ip_hash`) · código em
  minúsculas → 401 "restam 4" · código certo com lote vazio → 400 "nenhuma decisão enviada" (autenticou,
  nada gravado) · origin errado → 403 · `/p/…` → 404 nos dois Workers · `aprovar…/` → 302 para
  `…/aprovacao/` · `/a` do e-mail intacto (403 "link malformado").
- Falhas de acesso em produção: a do teste de fumaça foi apagada pelo próprio acerto seguinte (regra do
  limite) e um `DELETE FROM falhas_acesso` confirmou **0 falhas**; **0 eventos** em produção.
- Playwright na página real, **sem enviar nada**: computador, WebKit "iPhone 13" pelo link curto e Chromium
  "Pixel 7" pela URL direta — painel fora da tela no início, botão "Aprovações" visível, após o toque o
  painel fica no topo (y = 0), rascunho e diálogo do código funcionam; 0 pedidos POST.

## 6. Limpeza
Worker de teste (com seus segredos, inclusive o token do `gh` usado para gravar no ramo de teste), D1 de
teste e ramo `teste-aprovacao` apagados; página `site/aprovacao-teste/` e artes `site/midia/2099-W01/`
removidas da master.
