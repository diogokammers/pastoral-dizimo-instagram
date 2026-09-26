# ADR-008 — Portão de publicação e cliente da Meta (fatia 7)

Data: 2026-09-26. Status: aceito (implementado; ainda sem segredos cadastrados nem chamada real à API).

## Contexto
A estreia foi publicada à mão (`content/estreia/publicado.json`). Para as semanas seguintes, a arquitetura
(§1.1, §5, §6) exige um portão determinístico que só publique o que foi aprovado, exatamente como aprovado.

## Decisões
1. **Cliente próprio e mínimo** (`src/pastoral/meta.py`), só com a biblioteca padrão (`urllib`), sem SDK nem
   `requests`. Instagram API with Instagram Login, host `graph.instagram.com`, versão em `config.yaml`
   (`meta.versao_api: v26.0`, a exibida na doc em 2026-09-25). Operações: item de carrossel
   (`is_carousel_item`, `alt_text`), imagem única, carrossel (`media_type=CAROUSEL`, `children`, `caption`),
   poll de `status_code` (60 s, máx. 300 s, como a doc recomenda), `media_publish`, `permalink`,
   `refresh_access_token` (`grant_type=ig_refresh_token`) e `GET /me`.
2. **Segredos só por ambiente:** `IG_ACCESS_TOKEN`, `IG_USER_ID`, `APROVACAO_HMAC_SECRET`. Em POST o token vai
   no corpo; toda mensagem de erro passa por `mascarar()`; `repr` do cliente não mostra o token; o token
   renovado é gravado em arquivo e nunca impresso.
3. **Portão** (`src/pastoral/publicar.py`) publica um post só se: existe `aprovacao.json` da semana; o
   HMAC-SHA256 confere; a semana assinada é a da pasta; os sha256 das artes em `site/midia/<semana>/`, da
   legenda final (legenda + hashtags) e dos alt-texts batem com o aprovado; `agendado_para` (com fuso) já
   passou; o número não está em nenhum ledger (numeração global, inclui a estreia); e, na publicação real, a
   URL pública do Pages serve exatamente a arte aprovada. Ledger: `content/semanas/<semana>/publicado.json`
   com `ig_media_id` e `permalink`.
4. **JSON canônico** para o HMAC (o Worker da fatia 6 precisa gerar igual): chaves ordenadas em todos os
   níveis, separadores `,`/`:` sem espaço, UTF-8 sem escapar acentos, sem o campo `assinatura`; assinatura em
   hex minúsculo. Formato de `aprovacao.json`: `semana`, `aprovado_por`, `aprovado_em`, `nonce`,
   `posts[{numero, agendado_para, legenda_sha256, alt_text_sha256, artes[{arquivo, sha256}]}]`, `assinatura`.
5. **Dry-run é o padrão.** Publicação real exige `PUBLICAR=1` e ausência de `--dry-run`. No Action,
   `PUBLICAR=1` só quando a variável de repositório `PUBLICAR_ATIVO` = `1` **e** a execução é a agendada (ou
   manual com "publicar" marcado). Assim o Diogo liga a automação com uma chave explícita.
6. **Workflows:** `publicar.yml` (diário 22:15 UTC = 19:15 em Brasília, `concurrency`, commita o ledger) e
   `token.yml` (segundas, renova; com `GH_PAT_SECRETS` atualiza o secret via `gh secret set`, sem ele só
   alerta). Nenhum dos dois foi disparado.
7. Recusas "normais" (sem aprovação, data futura, já publicado) saem com código 0; recusas graves
   (assinatura, hash, arte ausente, URL divergente) e erros da API saem com 1, para o Action alertar.

## Consequências
- Imagens precisam estar em `site/midia/<semana>/` e o Pages já implantado antes da hora agendada.
- `IG_USER_ID` fica em GitHub **Variables** (arquitetura §1.3), não em Secrets.
- Pendente de verificação real: `python -m pastoral.meta --verificar` depois que o Diogo cadastrar o token.
- Risco: a doc não garante que o token antigo siga válido após o refresh; se o secret não for atualizado
  (sem PAT), o job alerta toda semana.
