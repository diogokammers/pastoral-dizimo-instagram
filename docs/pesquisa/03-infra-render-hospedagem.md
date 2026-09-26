# Pesquisa 03 — Infraestrutura gratuita/barata para pipeline de publicação no Instagram

> Pesquisa realizada em 2026-09-25. Cada fato cita a fonte oficial consultada nesta sessão. Onde a documentação oficial não confirmou algo, está marcado como **NÃO VERIFICADO**.

---

## 1. GitHub Actions

- **Fato:** conta GitHub Free tem 2.000 minutos/mês de runners hospedados para repositórios privados; repositórios públicos têm minutos ilimitados nos runners padrão. — Fonte: https://docs.github.com/en/billing/concepts/product-billing/github-actions (trecho: "2,000" minutos/mês para GitHub Free).
- **Fato:** o multiplicador de minutos por SO é cobrado por preço-por-minuto, não como "multiplicador" nomeado assim na doc: Linux 2-core = $0.006/min, Windows 2-core = $0.010/min, macOS 3-core/4-core = $0.062/min. Isso equivale, na prática, a Windows consumindo minutos do orçamento a uma taxa maior que Linux (a doc de billing usa a razão de custo, não um "2x" explícito para Windows). — Fonte: https://docs.github.com/en/billing/concepts/product-billing/github-actions. **NÃO VERIFICADO**: a documentação não usa literalmente "2x" para Windows; o fator histórico "Windows 2x, macOS 10x" citado em várias fontes de terceiros não foi encontrado com esse texto exato na página atual — a proporção calculada a partir dos preços por minuto é ~1.67x para Windows e ~10.33x para macOS.
- **Fato (schedule/cron):** "The `schedule` event can be delayed during periods of high loads of GitHub Actions workflow runs. High load times include the start of every hour." Recomenda-se agendar em minutos não redondos. — Fonte: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule.
- **Fato (desativação automática):** "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." — Fonte: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule. **Importante:** a doc atual só menciona explicitamente repositórios **públicos** nessa frase. **NÃO VERIFICADO** oficialmente se o mesmo prazo/regra vale para repositório privado (relatos de comunidade sugerem que sim, mas a página oficial não afirma isso para repositórios privados nesta sessão). Como este projeto usará repositório privado, tratar como risco e mitigar com atividade periódica no repo (commits/PRs) e/ou monitoramento externo do cron.
- **Fato (workflow_dispatch):** permite executar manualmente com inputs; até 25 inputs por evento `workflow_dispatch`. Exemplo via CLI: `gh workflow run greet.yml -f name=mona -f greeting=hello`. — Fonte: https://docs.github.com/en/actions/using-workflows/manually-running-a-workflow.
- **Fato (concurrency):** agrupa execuções por `group`; apenas uma execução por grupo roda por vez; `cancel-in-progress: true` cancela a anterior. Exemplo:
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```
  — Fonte: https://docs.github.com/en/actions/using-jobs/using-concurrency.
- **Fato (GITHUB_TOKEN contents: write):** conceder via `permissions: contents: write` no nível do workflow ou do job para permitir commit dentro do workflow. — Fonte: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication.
- **Fato (secrets, tamanho e vazamento):** "To use secrets that are larger than 48 KB, you can use a workaround..." (confirma limite de 48 KB por secret). GitHub mascara automaticamente o valor de secrets nos logs, mas alerta: ao usar o workaround de secrets grandes (gpg), "GitHub does not redact secrets that are printed in logs" nesse cenário específico. — Fonte: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions.
- **Fato (artifacts, retenção padrão):** por padrão, checks, workflow runs, commit statuses e artifacts/logs são retidos por 90 dias antes de exclusão automática; em repositórios privados/internos o valor de `retention-days` pode ser configurado entre 1 e 400 dias (em públicos, entre 1 e 90 dias). — Fonte: https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization.

## 2. GitHub Pages

- **Fato:** "If the account that owns the repository uses GitHub Free or GitHub Free for organizations, the repository must be public." — ou seja, GitHub Pages a partir de repositório **privado** exige plano pago (GitHub Pro, Team, Enterprise Cloud/Server); não funciona em repositório privado com conta Free. — Fonte: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site.
- **Fato (limites):** "Published GitHub Pages sites may be no larger than 1 GB." "GitHub Pages sites have a *soft* bandwidth limit of 100 GB per month." "GitHub Pages sites have a *soft* limit of 10 builds per hour." — Fonte: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits.
- **Fato:** mesmo publicando a partir de um repositório privado (em plano pago), o site do GitHub Pages resultante é público na internet, a menos que o plano/organização permita "private pages" (recurso do GitHub Enterprise Cloud). — Fonte: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site (trecho: "GitHub Pages sites are publicly available on the internet, even if the repository for the site is private").
- **Implicação para o projeto:** como o repositório é privado e a conta é Free, **GitHub Pages não é viável** sem upgrade para GitHub Pro (pago) — descartar como opção de hospedagem de imagem/prévia neste projeto, a menos que se decida pagar o Pro.
- **Fato (raw.githubusercontent.com):** não é um serviço com autenticação suportada oficialmente; para repositório privado a única forma documentada de acesso autenticado é via API REST do GitHub (`/repos/:owner/:repo/contents/:path`) com token, não via URL direta pública. — Fonte: https://docs.github.com/en/rest/repos/contents (confirma uso de `Authorization: Bearer <token>` na API REST; a documentação da API REST não expõe raw.githubusercontent.com como caminho de acesso público a repositório privado). Portanto **raw.githubusercontent.com não serve como `image_url` pública para repo privado** — precisa de token, e a Meta não pode fornecer token nas requisições do crawler.
- **Fato (GitHub Releases assets em repo privado):** a API de assets de release exige autenticação (`Accept: application/octet-stream` + token) para repositórios privados; não há URL de download direta/pública sem autenticação para release assets de repositório privado. **NÃO VERIFICADO** com uma página única e específica de docs.github.com que declare isso de forma explícita e concisa (a doc de referência da API de Releases Assets implica isso, mas não há uma frase objetiva equivalente à do raw content); a mecânica foi confirmada por discussões oficiais da comunidade GitHub, não por uma declaração normativa de docs.github.com nesta sessão.

## 3. Cloudflare

### (a) Workers / Pages Free

- **Fato:** Workers Free = 100.000 requisições/dia, resetando à meia-noite UTC; ao exceder, retorna **Error 1027**. CPU time: 10 ms por requisição HTTP e 10 ms por Cron Trigger no plano Free. — Fonte: https://developers.cloudflare.com/workers/platform/limits/.
- **Fato (Static Assets, Workers):** 20.000 arquivos por versão do Worker no Free (100.000 no Paid), tamanho de arquivo individual até 25 MiB. — Fonte: https://developers.cloudflare.com/workers/platform/limits/.
- **Fato (Cloudflare Pages Free):** 500 builds/mês, 1 build por vez (build concorrente), timeout de build 20 minutos; até 20.000 arquivos por site; tamanho máximo de arquivo individual 25 MiB; domínios customizados por projeto: 100 no Free. — Fonte: https://developers.cloudflare.com/pages/platform/limits/.
- **Fato:** deploy via `wrangler` com API token em CI e domínio `*.pages.dev`/`*.workers.dev` com HTTPS automático são o fluxo padrão documentado (uso confirmado nas próprias páginas de Workers/Pages, sem necessidade de configuração extra de certificado). **NÃO VERIFICADO** uma frase textual isolada que declare "HTTPS automático incluso" nesta sessão de busca — inferido da documentação geral de Pages/Workers (domínios `*.pages.dev`/`*.workers.dev` são servidos via a rede Cloudflare, que serve tudo por HTTPS por padrão).

### (b) R2

- **Fato (free tier R2):** Storage 10 GB-month/mês grátis; Class A Operations 1 milhão de requisições/mês grátis; Class B Operations 10 milhões de requisições/mês grátis; Egress sempre grátis (sem cobrança de saída de dados). O free tier só vale para Standard storage, não para Infrequent Access. — Fonte: https://developers.cloudflare.com/r2/pricing/.
- **Fato (r2.dev):** "Public access through r2.dev subdomains is rate-limited and should only be used for development purposes." "Managed public bucket access through an r2.dev subdomain is not intended for production usage and has a variable rate limit applied to it... (hundreds of requests/second)... Bandwidth (throughput) may also be throttled." Para produção, recomenda-se domínio customizado. — Fonte: https://developers.cloudflare.com/r2/platform/limits/ e https://developers.cloudflare.com/r2/buckets/public-buckets/.

### (c) Workers KV (free tier)

- **Fato:** Free plan — leituras 100.000/dia, escritas 1.000/dia, exclusões 1.000/dia, list requests 1.000/dia, dados armazenados 1 GB. Todos os limites resetam diariamente às 00:00 UTC; ao exceder qualquer um, as operações desse tipo falham com erro. — Fonte: https://developers.cloudflare.com/workers/platform/pricing/ (seção Workers KV).

### (d) `wrangler secret put` e newline no PowerShell

- **Fato:** a doc oficial mostra o uso via pipe: `echo "-----BEGIN PRIVATE KEY-----\nM...==\n-----END PRIVATE KEY-----\n" | wrangler secret put PRIVATE_KEY`. — Fonte: https://developers.cloudflare.com/workers/wrangler/commands/workers/#secret-put. **NÃO VERIFICADO**: não existe nota oficial da Cloudflare especificamente sobre o comportamento de `echo`/pipe no PowerShell (CRLF vs LF, aspas simples ausentes no Windows) — esse é um problema conhecido de shells Windows, não documentado pela Cloudflare. Recomenda-se, para uso no Windows, escrever o secret em um arquivo temporário sem quebra de linha final e usar `Get-Content -Raw arquivo | wrangler secret put NOME`, testando explicitamente para evitar newline indesejada — **prática recomendada não-oficial**, não confirmada em documentação.

### (e) Erro 1010 e necessidade de User-Agent

- **Fato:** Erro 1010 = "The owner of this website has banned your access based on your browser's signature". Causa comum: "A website owner blocked your request based on your client's web browser." Resolução para o dono do site: desativar "Browser Integrity Check" nas configurações de segurança. — Fonte: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/. **NÃO VERIFICADO**: a página oficial do erro 1010 não menciona User-Agent explicitamente como causa/solução; a recomendação de enviar um User-Agent identificável em requisições programáticas é prática geral, não uma instrução textual da página do erro 1010.

### (f) Cloudflare Access / Zero Trust Free

- **Fato:** o plano Zero Trust Free ("Free Plan — $0 forever") é indicado para "teams under 50 users or enterprise proof-of-concept tests"; acima de 50 usuários, o Pay-as-you-go plan cobra $7/usuário/mês. — Fonte: https://www.cloudflare.com/plans/zero-trust-services/ (via busca; conteúdo consultado nesta sessão, página oficial de pricing da Cloudflare). Cloudflare Access permite proteger uma aplicação self-hosted com política de e-mail (ex.: OTP por e-mail) via **Access controls > Applications > Self-hosted**, com política do tipo "Allow — Emails ending in @dominio.com". — Fonte: https://developers.cloudflare.com/ai-search/configuration/retrieval/public-endpoint/cloudflare-access/ (exemplo de policy Access, aplicável de forma equivalente a qualquer app self-hosted).
- **Implicação:** Cloudflare Access (Zero Trust) Free serve bem para proteger a página de prévia com login por e-mail (One-Time PIN), dentro do limite de 50 usuários — mais do que suficiente para 1 aprovador.

## 4. Render headless (Playwright)

- **Fato (instalação):** `pip install pytest-playwright` (ou `pip install playwright`) seguido de `playwright install` (ou `playwright install chromium` para instalar apenas Chromium). — Fonte: https://playwright.dev/python/docs/intro.
- **Fato (Windows nativo):** requisitos de sistema listados incluem "Windows 11+, Windows Server 2019+ or Windows Subsystem for Linux (WSL)" — ou seja, roda nativamente no Windows, sem exigir WSL. — Fonte: https://playwright.dev/python/docs/intro.
- **Fato (screenshot de elemento):** `page.locator(".header").screenshot(path="screenshot.png")` — captura apenas o elemento. — Fonte: https://playwright.dev/python/docs/screenshots.
- **Fato (parâmetros de screenshot):** `type` ("png" ou "jpeg"), `quality` ("The quality of the image, between 0-100. Not applicable to png images."), `full_page` (booleano, página inteira rolável), `clip` (região x/y/width/height). — Fonte: https://playwright.dev/python/docs/api/class-page#page-screenshot.
- **Fato (device_scale_factor):** definido ao criar o contexto do navegador via `browser.new_context(device_scale_factor=...)`; "Specify device scale factor (can be thought of as dpr). Defaults to 1." — Fonte: https://playwright.dev/python/docs/api/class-browser#browser-new-context.
- **Fato (fontes web prontas antes do screenshot):** usar `page.wait_for_function("() => document.fonts.ready")` para aguardar todas as fontes carregarem antes de capturar. Existe também a variável de ambiente `PW_TEST_SCREENSHOT_NO_FONTS_READY` para pular essa espera automática em testes visuais. — Fonte: confirmado via busca cruzando documentação do Playwright e discussões oficiais do repositório GitHub microsoft/playwright (a lógica de espera de fontes é comportamento documentado da API de screenshot dos testes visuais do Playwright).
- **Fato (cache de binário em CI):** a documentação oficial **desaconselha** cachear os binários do navegador: "Caching browser binaries is not recommended, since the amount of time it takes to restore the cache is comparable to the time it takes to download the binaries." Recomenda-se rodar `playwright install --with-deps` (ou `python -m playwright install --with-deps` para Python) diretamente em cada execução de CI. — Fonte: https://playwright.dev/python/docs/ci.
- **Fato (medir overflow de texto):** medir `scrollHeight > clientHeight` de um elemento é feito via `page.evaluate("el => el.scrollHeight > el.clientHeight", element_handle)` ou `locator.evaluate(...)` — mecanismo padrão do DOM, documentado na API `evaluate` do Playwright (`page.evaluate`/`locator.evaluate` aceitam uma função JS executada no contexto da página). **NÃO VERIFICADO** um exemplo textual específico de "scrollHeight > clientHeight" na doc oficial do Playwright nesta sessão — a técnica é padrão de DOM (MDN), aplicável via `evaluate`, mas não foi encontrado um trecho oficial do Playwright citando esse padrão literalmente.
- **Fato (alternativa `chromium --headless --screenshot`):** existe a flag nativa do Chromium `--headless --screenshot=output.png <url>`, mas isso é um recurso do próprio binário Chromium/Chrome (não documentado pelo Playwright); não foi verificado nesta sessão em documentação oficial do Chromium devido a escopo (fora do conjunto de domínios oficiais solicitado). **NÃO VERIFICADO**.

## 5. E-mail transacional

- **Fato (Resend Free):** "$0/mo"; limite de "3,000" e-mails/mês; "100 emails a day"; até 3 domínios. — Fonte: https://resend.com/pricing.
- **Fato (sem domínio verificado):** "By default, you can only send emails to your own email address." Para enviar a outros destinatários, é preciso adicionar e verificar um domínio próprio. — Fonte: páginas de integração oficiais do Resend (ex.: https://resend.com/docs/lovable-integration, https://resend.com/docs/base44-integration, https://resend.com/docs/v0-integration), que repetem esse texto padrão do onboarding do Resend.
- **Fato (verificação exige domínio):** "You must add and verify at least one domain to send emails with Resend." — Fonte: https://resend.com/docs/dashboard/domains/introduction. **NÃO VERIFICADO** nesta sessão a lista específica e completa dos registros DNS (tipo exato de cada registro DKIM/SPF/MX de retorno com nomes/valores) — a página consultada não detalhou a tabela de registros; recomenda-se consultar a página "Add a domain" (https://resend.com/docs/add-a-domain) diretamente no fluxo de configuração real, pois os valores são gerados dinamicamente por conta/domínio.
- **Fato (Cloudflare Email Service / Email Sending):** o recurso de envio (Email Sending) está em **Beta** ("Email Sending Beta for outbound transactional emails"). Envio para "verified destination addresses" (endereços de destino verificados na própria conta) é gratuito em todos os planos; para envio geral, a doc indica a necessidade de configuração adicional. — Fonte: https://developers.cloudflare.com/email-routing/email-workers/send-emails/. **NÃO VERIFICADO** de forma conclusiva nesta sessão se o Email Sending da Cloudflare exige obrigatoriamente Workers Paid plan para uso em produção (a resposta agregada mencionou isso, mas não foi possível confirmar com uma citação textual isolada e inequívoca da página de pricing do Email Service, que não foi aberta diretamente).
- **Fato (Gmail SMTP / senha de app):** limite de envio "500 emails per rolling 24 hours" pela interface web do Gmail; "100 messages per rolling 24 hours" para clientes de e-mail/SMTP (ex.: uso de senha de app via SMTP) em conta pessoal do Gmail. — Fonte: https://support.google.com/mail/answer/22839 (Gmail Help, página oficial do Google). Observação: o valor "500/dia" citado no enunciado da pesquisa corresponde ao limite via interface web; o envio via SMTP com senha de app (o cenário mais provável para este projeto) tem limite documentado de **100 mensagens/24h** para contas pessoais do Gmail — mais restritivo do que o suposto inicialmente.
- **Fato (GitHub Issues/Notifications como canal de aprovação):** o GitHub envia notificações nativas por e-mail para atividades em Issues/PRs (menções, atribuições, comentários) conforme as configurações de notificação do usuário — mecanismo padrão e documentado da plataforma. **NÃO VERIFICADO** com uma citação textual específica nesta sessão (não foi aberta a página de configuração de notificações do GitHub), mas é comportamento amplamente documentado e nativo, sem necessidade de infraestrutura extra.

## 6. Assinatura HMAC de link

- **Fato (`hmac.compare_digest`):** "Return a == b. This function uses an approach designed to prevent timing analysis by avoiding content-based short circuiting behaviour, making it appropriate for cryptography." Aceita `str` (somente ASCII) ou bytes-like object, ambos do mesmo tipo. — Fonte: https://docs.python.org/3/library/hmac.html.
- **Fato (itsdangerous `TimestampSigner`):** permite assinar um valor com timestamp embutido e validar a idade da assinatura via `max_age`; se expirado, levanta exceção do tipo `SignatureExpired` com mensagem como "Signature age 15 > 5 seconds". Exemplo oficial:
  ```python
  from itsdangerous import TimestampSigner
  s = TimestampSigner('secret-key')
  string = s.sign('foo')
  s.unsign(string, max_age=5)
  ```
  — Fonte: https://itsdangerous.palletsprojects.com/en/stable/timed/.
- **Fato (Web Crypto no Workers):** o runtime dos Workers suporta a Web Crypto API nativamente (`crypto.subtle`, `crypto.getRandomValues()`, `crypto.randomUUID()`), incluindo `crypto.subtle.timingSafeEqual()` para comparação de HMAC/tokens em tempo constante, sem precisar do compat flag `nodejs_compat`. Exemplo oficial de verificação segura via hash + `timingSafeEqual`:
  ```js
  async function verifyToken(provided, expected) {
    const encoder = new TextEncoder();
    const [providedHash, expectedHash] = await Promise.all([
      crypto.subtle.digest("SHA-256", encoder.encode(provided)),
      crypto.subtle.digest("SHA-256", encoder.encode(expected)),
    ]);
    return crypto.subtle.timingSafeEqual(providedHash, expectedHash);
  }
  ```
  — Fonte: https://developers.cloudflare.com/workers/best-practices/workers-best-practices/. Além disso, o módulo Node `node:crypto` (incluindo HMAC via `sign`/`verify` ou `createHmac`) também é totalmente suportado nos Workers. — Fonte: https://developers.cloudflare.com/workers/runtime-apis/nodejs/crypto/.

## 7. Requisitos de URL pública para a Meta / bots

- **Fato (facebookexternalhit):** o servidor deve usar "gzip e deflate encodings"; o conteúdo precisa ser "crawled by the crawler within a few seconds or Facebook will be unable to display the content" (exigência implícita de resposta rápida); propriedades Open Graph devem estar nos primeiros 1 MB da página; o crawler pode enviar cabeçalho `Range` e a aplicação deve responder de acordo. — Fonte: https://developers.facebook.com/docs/sharing/webmasters/crawler/.
- **Fato (Instagram Graph API / image_url):** a URL de imagem deve ser publicamente acessível e retornar HTTP 200 com `content-type` apropriado; URLs devem usar apenas caracteres US-ASCII (padrão HTTP/IETF), senão a requisição falha. — Fonte: consolidado a partir da documentação de Content Publishing / IG Media do Meta for Developers (páginas https://developers.facebook.com/docs/instagram-platform/content-publishing/ e referência de IG Media); **NÃO VERIFICADO** uma citação textual isolada e literal de "must return HTTP 200 and proper content-type" extraída diretamente nesta sessão — a página específica de criação de mídia (`ig-user/media`, método POST) não pôde ser aberta com sucesso via WebFetch nesta sessão (a página retornada mostrou apenas os métodos de leitura/edição, não criação). Recomenda-se validar esse ponto abrindo diretamente https://developers.facebook.com/docs/instagram-platform/content-publishing/ antes de finalizar a implementação.
- **Fato (Cloudflare Bot Fight Mode e crawlers verificados):** o Bot Fight Mode do plano Free "Protects entire domains without endpoint restrictions" e "Cannot be customized, adjusted, or reconfigured via WAF custom rules" nem pode ser ignorado via ação "Skip" de custom rules — ou seja, no plano Free **não há como criar uma exceção explícita para permitir um bot específico** (como o `facebookexternalhit`) caso o Bot Fight Mode o desafie incorretamente; a única opção documentada é desativar o Bot Fight Mode inteiro. — Fonte: https://developers.cloudflare.com/bots/get-started/bot-fight-mode/ (trechos: "Cannot be customized, adjusted, or reconfigured via custom rules" e "Cannot be bypassed with custom rule Skip actions"). Alocar exceções granulares por categoria de bot (ex.: permitir "Verified bots") só é possível no **Super Bot Fight Mode**, disponível a partir do plano **Pro** (pago) — não no Free. — Fonte: https://developers.cloudflare.com/bots/get-started/super-bot-fight-mode/ e https://developers.cloudflare.com/waf/feature-interoperability/.
- **Implicação:** se as imagens forem hospedadas atrás de um domínio Cloudflare com Bot Fight Mode ativo no plano Free, há risco real de o crawler da Meta ser desafiado/bloqueado, sem uma forma granular de liberar exceção nesse plano. Mitigação: não ativar Bot Fight Mode na zona que serve as imagens públicas, ou hospedar as imagens num subdomínio/zona sem esse recurso ativo.

## 8. Calendário litúrgico

- **Fato (`dateutil.easter`):** função `dateutil.easter.easter(year, method=3)`; suporta três métodos: `EASTER_JULIAN` (1, calendário juliano, válido a partir de 326 d.C.), `EASTER_ORTHODOX` (2, data juliana convertida ao calendário gregoriano, válido entre 1583–4099), `EASTER_WESTERN` (3, padrão, cálculo revisado no calendário gregoriano, válido entre 1583–4099). — Fonte: https://dateutil.readthedocs.io/en/stable/easter.html.
- **Fato (licença python-dateutil):** licenciamento dual — "Apache 2.0 License" ou "BSD 3-Clause License" para contribuições após 1º de dezembro de 2017; contribuições anteriores permanecem sob BSD 3-Clause apenas. — Fonte: https://pypi.org/project/python-dateutil/.
- **Fato (romcal):** é uma biblioteca **JavaScript** (não Python) para gerar calendários litúrgicos do Rito Romano, com suporte a tempos litúrgicos (advent, christmastide, ordinary-time, lent, easter-triduum, eastertide) e períodos especiais (christmas-octave, holy-week, easter-octave). — Fonte: repositório oficial https://github.com/romcal/romcal (conteúdo consultado via busca nesta sessão). **NÃO VERIFICADO** a licença exata do romcal nesta sessão (não foi possível abrir o arquivo LICENSE do repositório diretamente); é necessário confirmar antes de qualquer uso/porte do código.
- **NÃO VERIFICADO:** não foi localizado, nesta sessão, um pacote Python específico e maduro chamado literalmente "liturgical-calendar" com documentação oficial robusta equivalente ao romcal — a pesquisa encontrou apenas um pacote experimental (`LiturgicalCalendarUtils`, GitHub, uso e licença não confirmados) e a biblioteca Ruby dual-licenciada (LGPL 3 / MIT) `calendarium-romanum`. Para o calendário litúrgico completo (tempos, cores, ciclos A/B/C, santoral), a alternativa mais robusta é calcular a Páscoa com `dateutil.easter` e derivar os demais tempos litúrgicos (Advento, Quaresma, Tríduo Pascal, Pentecostes etc.) manualmente a partir dela, já que não há uma biblioteca Python oficial e amplamente mantida equivalente ao romcal.
- **Fato (fonte oficial CNBB):** a CNBB mantém a página institucional de Liturgia Diária em https://www.cnbb.org.br/liturgia-diaria/ e o portal dedicado https://liturgiadiaria.edicoescnbb.com.br/, além do app oficial "Liturgia Diária CNBB". — Fonte: páginas oficiais cnbb.org.br listadas (consultadas via busca nesta sessão; não citar/reproduzir conteúdo litúrgico dessas páginas, apenas usá-las como referência institucional).

---

## Tabela comparativa — hospedagem de imagem pública

| Opção | Custo | Limite relevante (Free) | Fricção / risco |
|---|---|---|---|
| **GitHub Pages (repo público)** | Grátis | 1 GB/site, 100 GB/mês banda (soft), 10 builds/hora (soft) | Exige repositório **público** no plano Free (não serve para este projeto, que é privado) — ou upgrade pago (GitHub Pro) para publicar de repo privado |
| **GitHub Pages (repo privado)** | Pago (GitHub Pro+) | mesmos limites acima | Requer assinatura paga só para isso; site publicado continua público na internet mesmo com repo privado |
| **Cloudflare Pages** | Grátis | 500 builds/mês, 1 build por vez, 20.000 arquivos, 25 MiB/arquivo | Fácil deploy via `wrangler`; HTTPS automático em `*.pages.dev`; sem custo de banda documentado como limite duro |
| **Cloudflare R2 (r2.dev)** | Grátis (10 GB, 1M Class A, 10M Class B) | `r2.dev` é rate-limited e "não recomendado para produção" | Deve usar domínio custom (também grátis, exige domínio próprio na Cloudflare) para uso em produção |
| **Cloudflare R2 (domínio custom)** | Grátis dentro do free tier | mesmos limites de R2 acima | Requer domínio próprio configurado na Cloudflare; ideal para produção; sem egress cobrado |
| **Cloudflare Workers Static Assets** | Grátis | 20.000 arquivos/versão, 25 MiB/arquivo, 100.000 req/dia | Adequado para servir imagens junto com lógica do Worker (ex.: assinatura de link) |
| **raw.githubusercontent.com (repo privado)** | N/A | — | Não serve: exige token, que a Meta não consegue fornecer no crawler — **descartado** |
| **GitHub Releases assets (repo privado)** | N/A | — | Exige autenticação via API; sem URL pública direta sem token — **descartado** |

**Recomendação:** Cloudflare Pages ou R2 com domínio custom (não usar `r2.dev` em produção) são as opções mais robustas e sem custo dentro do escopo deste projeto.

## Tabela comparativa — e-mail transacional

| Opção | Custo | Limite relevante | Fricção / risco |
|---|---|---|---|
| **Resend** | Grátis | 3.000 e-mails/mês, 100/dia, 3 domínios | Sem domínio verificado, só envia para o e-mail da própria conta Resend; precisa configurar DNS do domínio para enviar a terceiros |
| **Cloudflare Email Service (Email Sending)** | Beta; grátis para destinatários verificados na conta | Não totalmente detalhado nesta pesquisa | Recurso em **Beta**; requer mais validação antes de depender dele em produção |
| **Gmail SMTP (senha de app, conta pessoal)** | Grátis | 500/dia via webmail; **100/dia via SMTP/cliente de e-mail** (mais restritivo do que o suposto) | Suficiente para 1 destinatário/semana, mas é um uso "não oficial" de automação em conta pessoal — risco de bloqueio por política de abuso do Google |
| **GitHub Issues/Notifications** | Grátis | Ilimitado (nativo da plataforma) | Não é "e-mail transacional" customizável (texto/HTML livre), mas serve bem como canal zero-infra para aprovação/alerta |

**Recomendação:** Resend é a opção mais simples e madura, desde que se verifique um domínio próprio (necessário de qualquer forma para enviar a diogokammers@gmail.com sem ser a própria conta). GitHub Issues/Notifications é um bom complemento de baixíssima fricção para alertas de falha, sem precisar de nenhuma configuração de e-mail.

---

## Riscos e NÃO VERIFICADOS (resumo)

1. Regra de desativação de workflows agendados após 60 dias de inatividade: documentada oficialmente só para repositórios **públicos**; comportamento em repositório privado não confirmado na documentação consultada nesta sessão.
2. HTTPS automático em `*.pages.dev`/`*.workers.dev`: inferido, não citado textualmente em uma frase isolada nesta sessão.
3. Nota oficial da Cloudflare sobre newline ao usar `wrangler secret put` via pipe no PowerShell: **inexistente** — é um problema de shell, não documentado pela Cloudflare.
4. Menção oficial a User-Agent como causa/solução do erro 1010: **não encontrada** na página oficial do erro.
5. Exigência de Workers Paid plan para uso geral do Cloudflare Email Sending: não confirmada com citação textual isolada nesta sessão (Email Sending está em Beta).
6. Lista completa/exata dos registros DNS exigidos pelo Resend para verificação de domínio: não detalhada na página consultada nesta sessão (os valores são gerados dinamicamente por domínio no dashboard).
7. Requisito textual literal do Instagram Graph API sobre "HTTP 200 e content-type" para `image_url`: não foi possível abrir a página de criação de mídia (POST) diretamente nesta sessão; a página de referência retornada só cobria leitura/edição.
8. Licença exata do pacote JS `romcal` e existência de uma biblioteca Python madura equivalente: não confirmadas nesta sessão.
9. Frase oficial do Playwright citando literalmente o padrão `scrollHeight > clientHeight`: não encontrada (é técnica padrão de DOM, não um exemplo textual do Playwright).
10. Comportamento de GitHub Releases assets em repositório privado: confirmado por discussões da comunidade GitHub, não por uma declaração normativa isolada de docs.github.com nesta sessão.

## Implicações para o projeto

1. **Hospedagem de imagens públicas:** usar Cloudflare Pages ou R2 com domínio custom próprio — nunca GitHub Pages (exigiria repo público ou plano pago) nem raw.githubusercontent.com/Releases de repo privado (não funcionam sem token).
2. **Cuidado com Bot Fight Mode:** não ativar no domínio/zona que serve as imagens, pois no plano Free não há como abrir exceção para o `facebookexternalhit`; só o Super Bot Fight Mode (pago) permite isso.
3. **GITHUB_TOKEN com `contents: write`** resolve o commit automático de aprovação/ajuste dentro do próprio workflow, sem precisar de PAT adicional, desde que o endpoint de aprovação rode como parte de um `workflow_dispatch` ou de uma Cloudflare Worker que depois dispare um `repository_dispatch`/commit via API do GitHub (usando um PAT/GitHub App, já que o `GITHUB_TOKEN` só existe durante a execução do workflow).
4. **Cron agendado:** mitigar o risco de desativação por inatividade (ainda que documentado só para público) mantendo alguma atividade periódica no repositório privado, e/ou monitorando externamente se o workflow agendado realmente rodou (ex.: heartbeat que grava um arquivo/commit, ou alerta se o e-mail semanal não chegar).
5. **E-mail:** Resend com domínio verificado é a opção mais robusta; Gmail SMTP com senha de app é viável como fallback mas está sujeito a um limite mais apertado (100/dia via SMTP, não 500) e é um uso não oficial de automação pessoal — priorizar Resend.
6. **Aprovação:** GitHub Issues (com notificação nativa por e-mail) é uma alternativa de baixíssima fricção ao endpoint HTTP customizado com HMAC — vale considerar como MVP antes de construir o Worker de aprovação assinado.
7. **Render headless:** Playwright funciona nativamente no Windows (sem WSL) e em GitHub Actions Ubuntu; não cachear os binários do Chromium em CI (contraindicado pela própria doc); sempre aguardar `document.fonts.ready` antes do screenshot para evitar flakiness visual com Google Fonts.
8. **Calendário litúrgico:** basear o cálculo da Páscoa em `dateutil.easter` (método Western/Gregoriano, `method=3`) e derivar os tempos litúrgicos manualmente, pois não há uma biblioteca Python oficial e madura equivalente ao romcal (JS) confirmada nesta pesquisa.
