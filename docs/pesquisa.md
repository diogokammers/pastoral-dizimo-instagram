# Pesquisa validada — Fase 1

Data: 2026-09-25. Método: 4 subagentes (Sonnet 5) lendo só documentação oficial + verificações diretas do orquestrador (navegador e execução local). Cada afirmação abaixo tem link no documento detalhado indicado. O que não foi confirmado está na seção final, tratado como risco.

| Documento | Conteúdo | Custo medido (tokens do subagente) |
|---|---|---|
| [00-auditoria-conta.md](pesquisa/00-auditoria-conta.md) | Estado real da conta @pastoraldodizimo.arquifln | — (navegação direta) |
| [01-instagram-api.md](pesquisa/01-instagram-api.md) | Instagram Platform API: variantes, permissões, publicação, tokens, insights, limites | 120.625 + 154.773 (2ª rodada) |
| [02-claude-code-e-api.md](pesquisa/02-claude-code-e-api.md) | Claude Code (subagentes, skills, hooks, headless, CI) e API Anthropic (Batch, cache, preços) | 245.126 |
| [03-infra-render-hospedagem.md](pesquisa/03-infra-render-hospedagem.md) | GitHub Actions/Pages, Cloudflare, Playwright, e-mail, HMAC, calendário | 181.326 |
| [04-igreja-doutrina-lgpd.md](pesquisa/04-igreja-doutrina-lgpd.md) | CNBB, Catecismo, CIC, Arquidiocese, datas litúrgicas, LGPD, imagens sacras, termos | 144.831 |
| [05-medicoes-locais.md](pesquisa/05-medicoes-locais.md) | Esquema JSON real de `claude -p` | — (execução local) |

Total de tokens de pesquisa nos subagentes: **≈ 846 mil** (fase que roda uma vez só).

## 1. Fatos que decidem a arquitetura

### Conta e API do Instagram
- A conta é **pessoal**, sem Página do Facebook vinculada, 0 posts, bio pronta. Precisa virar **profissional** (Business ou Creator) — ação do Diogo. (00)
- Rota escolhida: **Instagram API with Instagram Login** — "does not require a Facebook Page". Permissões: `instagram_business_basic` + `instagram_business_content_publish` (+ `instagram_business_manage_comments` se quisermos comentários). Host `graph.instagram.com`, versão vista nos exemplos: v26.0. (01 §1, adendo)
- **Standard Access em modo Development basta** quando só quem tem papel no app usa; **App Review não é necessário** para uso próprio. (01 §2)
- Fluxo de publicação: `POST /{ig}/media` (image_url) → poll `status_code` até `FINISHED` (1×/min, máx. 5 min) → `POST /{ig}/media_publish`. Carrossel: itens com `is_carousel_item=true` → contêiner `CAROUSEL` com `children` (2–10) → publish. (01 §3)
- **Imagem: JPEG apenas, ≤ 8 MB, proporção 4:5 a 1,91:1, largura 320–1440 px, sRGB.** Em carrossel, **todos os slides são cortados pela proporção do primeiro** (padrão 1:1). Decisão derivada: render em **1080×1350 (4:5)** para tudo. (01 adendo)
- Legenda: **2.200 caracteres, 30 hashtags, 20 @menções**; `alt_text` até 1.000 caracteres (imagem/carrossel). `is_ai_generated=true` existe para autodeclaração. (01 §3, adendo)
- Limite: 100 posts/24h (a doc também cita 50 na seção de carrossel — usar 50 como teto). **Não existe agendamento nativo**: o cron do GitHub Action é o agendador. (01 §5–6)
- Tokens (Instagram Login): curto 1 h → longo **60 dias** via `/access_token`; **refresh** via `/refresh_access_token` (`grant_type=ig_refresh_token`) desde que o token tenha ≥ 24 h e não esteja expirado. Renovação automática semanal resolve o problema do sistema anterior. (01 §7)
- Insights de mídia FEED: `views, reach, likes, comments, saved, shares, total_interactions, follows, profile_visits, profile_activity, reposts`. `impressions` descontinuada para mídia após 02/07/2024 (explica o erro 400 anterior em métricas descontinuadas/incompatíveis). Álbuns: **não há insights para os filhos**, só para o carrossel. Conta: `follower_count` só com ≥ 100 seguidores. (01 §8)
- Rate limit (BUC): `4800 × impressões/24h` — irrelevante para 2 posts/semana. (01 §12)

### Claude Code e API Anthropic
- **Preços (USD/MTok, oficiais):** Fable 5.1 $10/$50 · Opus 5.5 $4/$20 · Sonnet 5 $2/$10 · Haiku 4.5 $1/$5. **Batch −50%.** Cache: escrita 5 min 1,25×, 1 h 2×; leitura 0,1× (Opus 5.5: **0,05×**; Fable: 0,025×). (02 tabela)
- Subagentes têm contexto isolado e `model:` fixável (`haiku|sonnet|opus|fable|inherit`); consumo por subagente aparece só como % em `/usage` — mas o **Agent tool desta sessão reporta tokens absolutos** por subagente (usado acima). (02 §A.1)
- Skills carregam só a descrição até serem invocadas; `context: fork` roda em subagente. Hooks com exit 2 / `permissionDecision: deny` são **gate determinístico** real. (02 §A.2–A.3)
- `claude -p --output-format json` devolve `total_cost_usd`, `usage` (input/output/cache write 5m/1h/cache read), `modelUsage`, `duration_ms`, `num_turns` — **confirmado por execução local**. `--max-budget-usd` existe. (05; 02 §A.4)
- **Assinatura Pro/Max em GitHub Actions é documentada oficialmente** (`CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token`) no repositório `anthropics/claude-code-action`. Não lemos os Termos de Uso para uso institucional — risco registrado. (02 §A.5)
- API: `output_config.format` (structured outputs, GA); Batch = até 100k requests/256 MB, resultado em ≤ 24 h, compatível com cache; `count_tokens` é **gratuito** (serve para medir o cartão de marca). (02 §B)
- Planos: Pro US$ 20/mês; Max "a partir de US$ 100/mês"; limites por janela de 5 h + semanal, **sem número de tokens publicado**. (02 §A.7)

### Infraestrutura
- GitHub Actions Free: 2.000 min/mês em repo privado, ilimitado em público; cron pode atrasar; regra de desativação após 60 dias sem atividade documentada para repo **público**. (03 §1)
- **GitHub Pages não funciona em repo privado no plano Free.** `raw.githubusercontent.com` e Releases de repo privado exigem token → descartados. (03 §2)
- Cloudflare Free: Pages (500 builds/mês), Workers (100k req/dia), R2 (10 GB; `r2.dev` "não recomendado para produção" → precisa domínio próprio), Access Zero Trust (50 usuários, OTP por e-mail). **Bot Fight Mode do plano Free não permite exceção** para `facebookexternalhit` — não ativar na zona das imagens. (03 §3)
- Playwright Python roda nativo no Windows e no runner Ubuntu; esperar `document.fonts.ready` antes do screenshot; doc desaconselha cachear binários do Chromium no CI. (03 §4)
- E-mail: Resend Free 3.000/mês, **sem domínio verificado só envia para o dono da conta**; Gmail SMTP com senha de app = 100/dia; Cloudflare Email Sending em Beta; notificações nativas do GitHub (Issue/PR) chegam por e-mail com zero infra. (03 §5)
- HMAC: `hmac.compare_digest`, `itsdangerous.TimestampSigner`, `crypto.subtle` no Worker — todos oficiais. (03 §6)
- Calendário litúrgico: `dateutil.easter` + derivação determinística (sem biblioteca Python madura tipo romcal). Datas conferidas por dois métodos independentes: Advento 29/11/2026, Cinzas 10/02/2027, Páscoa 28/03/2027, Pentecostes 16/05/2027, Corpus Christi 27/05/2027. CF 2027: "Fraternidade e o Cuidado das Crianças". (03 §8, 04 §5)

### Igreja, doutrina e lei
- **Doc. CNBB 106 — "O Dízimo na Comunidade de Fé: orientações e propostas"** existe nas Edições CNBB; texto integral **não está online** — os conceitos (dimensões religiosa/missionária/caritativa/social; dízimo ≠ oferta; sem percentual fixo) vêm de fontes secundárias e devem ser citados com cautela até o Diogo obter o exemplar. (04 §1)
- Confirmados em vatican.va: **CIC 2043** (5º mandamento da Igreja), **cân. 222 §1**, cân. 1260–1261. DGAE vigente: **2026–2032 (Doc. 114)**. (04 §2–3)
- Arquidiocese: site arquifln.org.br, Dom Wilson Tadeu Jönck SCJ, **há página oficial do Brasão** (sem manual de marca localizado), Instagram oficial @arquifloripa; o perfil da Pastoral **não aparece no site**. (04 §4)
- LGPD: convicção religiosa é **dado sensível** (art. 5º II, art. 11) → foto identificável de fiel exige consentimento específico e destacado; criança exige responsável (ECA 17). Sem fotos no piloto, o risco fica zerado. (04 §6)
- Imagens sacras: domínio público (Lei 9.610 art. 41, 70 anos) e acervos CC0 (Met, AIC, Rijksmuseum) confirmados — opção futura para arte com obra sacra. (04 §7)
- Lista de 20+ termos proibidos/preferidos com fonte, pronta para virar lint de conteúdo. (04 §8, §10)

## 2. O que a pesquisa muda em relação ao brief
1. O erro 400 em `reposts` do sistema anterior não se repete pela métrica em si (é válida para FEED); a métrica problemática hoje é `impressions`. Vamos coletar só a lista confirmada.
2. Renovação de token é **automatizável** (refresh a cada semana), eliminando o "lembrete de renovação" manual.
3. Aprovação pode ser mais barata que Worker + HMAC: notificação nativa do GitHub tem zero infra. Comparação na Fase 2.
4. Repositório **público** desbloqueia GitHub Pages para imagem e prévia sem Cloudflare — pergunta ao Diogo.

## 3. NÃO VERIFICADOS (tratados como risco)
| # | Item | Impacto | Como fechar |
|---|---|---|---|
| R1 | Caminho de menu do papel "Instagram Tester" | Baixo (Diogo é admin do app) | Ver no App Dashboard ao criar o app |
| R2 | Exigência de Business Portfolio / Privacy Policy URL para app "Business" em Standard Access | Médio (pode travar criação do app) | Fluxo real de criação do app (Fase 3, com Diogo) |
| R3 | Janela máxima `since/until` em insights de conta | Baixo | Testar na API |
| R4 | "Sem redirecionamento" para `image_url` | Baixo | Servir URL direta sempre |
| R5 | Termos de Uso da assinatura Max para automação institucional | Médio (compliance) | Ler Consumer Terms; rota API é o fallback |
| R6 | Desativação de cron após 60 dias em repo privado | Baixo | Heartbeat semanal + alerta de ausência |
| R7 | Doc. CNBB 106: **localizado** (Edições CNBB, ISBN 9788579725197, aprovado pelo Conselho Permanente em 2016); "Estudos 77" não existe — o correto é Estudos nº 8 | Baixo | Ver [06-cnbb-doc-106.md](pesquisa/06-cnbb-doc-106.md); texto integral só comprado |
| R8 | Manual de marca da Arquidiocese (só Brasão localizado) | Médio (identidade visual) | Diogo confirmar com a Cúria; estudo de identidade respeita o Brasão |
| R9 | Perfil não referenciado no site da Arquidiocese | Baixo (Diogo é admin) | Registrar como comunicação institucional |
| R10 | Requisitos de vídeo para Reels | Nulo no piloto | Só se Reels entrar no escopo |
