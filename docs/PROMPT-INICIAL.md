# Prompt inicial — Sistema de conteúdo Instagram da Pastoral do Dízimo

> Como usar: abra o Claude Code na raiz deste repositório, selecione o modelo
> indicado em "Modelo por fase" e cole tudo a partir de "## MISSÃO".
> O material de marca deve estar em `docs/marca/` antes de começar.

---

## MISSÃO

Você vai projetar e construir, **do zero**, um sistema que produz, aprova, publica e
mede conteúdo para o Instagram da **Pastoral do Dízimo da Arquidiocese de
Florianópolis**, cobrindo o fluxo da pauta até a publicação e a análise.

Objetivo central: **custo por post drasticamente menor que o sistema anterior, com
qualidade de texto e de arte igual ou superior**, e o mínimo de trabalho manual
compatível com aprovação humana obrigatória.

Não reaproveite código, prompts ou estrutura de nenhum projeto anterior. Você
**pode e deve** aprender com os fatos medidos listados abaixo, que custaram caro para
descobrir.

## REGRAS DE TRABALHO (inegociáveis)

1. **Zero achismo.** Toda afirmação sobre API, limite, preço, permissão ou
   comportamento de ferramenta precisa de fonte oficial consultada nesta sessão
   (documentação da Meta/Instagram Graph API, Anthropic/Claude Code, Cloudflare,
   GitHub etc.), citada com link no documento de decisão. Se não conseguir
   confirmar, escreva "NÃO VERIFICADO" e trate como risco, não como fato.
2. **Medir, não estimar.** Consumo de tokens, tempo e custo são medidos em execução
   real (ex.: `/cost`, `/context`, uso por subagente no transcript, `usage` da API).
   Estimativas só como hipótese antes da medição, e marcadas como tal.
3. **Não desista.** Se um caminho falhar, registre a evidência (erro, doc, teste),
   descarte-o e siga para a próxima alternativa. Dificuldade não é motivo para parar.
   Só pare para perguntar ao Diogo o que é decisão dele: credenciais, gasto de
   dinheiro, conteúdo/posicionamento e aprovação para publicar.
4. **Credenciais nunca passam por você.** Tokens, senhas e chaves são cadastrados
   pelo Diogo diretamente (GitHub Secrets, painel Cloudflare, variáveis de
   ambiente). Você só diz o nome exato da variável e onde cadastrar.
5. **Nada é publicado sem aprovação humana explícita** do conteúdo final (texto +
   arte). Esta regra precisa ser imposta por código e testada, não só por instrução.
6. **Decisões registradas.** Cada escolha de arquitetura vira um ADR curto em
   `docs/decisoes/` com: contexto, alternativas avaliadas, evidência, custo medido e
   decisão.
7. Scripts em Python com `encoding="utf-8"` explícito em toda leitura/escrita
   (ambiente Windows; sem isso o acento se corrompe).

## FATOS MEDIDOS DO SISTEMA ANTERIOR (use como ponto de partida, não como código)

O sistema anterior (outra conta, DNACX) funcionava, mas era caro:

- **Pipeline:** 7 subagentes em cadeia (estrategista → redator → curador → diretor de
  arte → agendador → analista → aprendizado), rodados **por dia**, 7 dias por semana,
  cada um relendo arquivos grandes de contexto (voz da marca, playbook, rascunhos).
- **Custo observado:** uma única chamada de subagente chegou a **~84 mil tokens**.
  No plano Pro, o limite prático observado ficou em torno de ~44 mil tokens por
  janela de 5 horas, de modo que **gerar uma semana não cabia numa sessão**. Foi
  preciso tornar o fluxo "resumível".
- **Aprovação em 2 gates por e-mail** (conteúdo e depois publicação), com um link
  assinado (HMAC) que um Cloudflare Worker validava, gravando o arquivo de
  aprovação no repositório via GitHub API. Funcionava, mas eram duas sessões
  manuais por semana (segunda e terça à noite) e dois cliques por post.
- **Parte mecânica em GitHub Actions** (publicação diária, coleta de métricas em 3
  e 7 dias, lembrete de renovação do token), sem chamar LLM. Isso deu certo.
- **Armadilhas reais já encontradas**. Confirme cada uma na documentação atual:
  - App da Meta em modo Development + Standard Access bastou para publicar na
    **própria** conta. Token de longa duração expira em cerca de 60 dias. O papel
    "Instagram Tester" fica em App roles → Roles → "Additional roles", e o convite
    só aparece na versão web do Instagram.
  - A métrica `reposts` da Insights API retornou erro 400 para o tipo de mídia usado.
  - Resend no modo sandbox só envia para o e-mail do dono da conta.
  - O Cloudflare bloqueou requisições sem `User-Agent` customizado (erro 1010).
  - No PowerShell, fazer pipe para stdin adiciona uma quebra de linha (segredo
    gravado com 1 byte a mais).

## CONTEXTO DA CONTA

- Conta: Instagram da Pastoral do Dízimo — Arquidiocese de Florianópolis.
- Material de estratégia e posicionamento: `docs/marca/` (leia **tudo** antes de
  propor qualquer coisa; é a fonte da verdade para voz, público, pilares e
  identidade visual).
- Sensibilidades do tema, a validar contra fontes oficiais da Igreja (ex.: documento
  da CNBB sobre o dízimo, que deve ser localizado e confirmado):
  - Dízimo como gesto de fé, gratidão e partilha. **Nunca** tom de cobrança,
    barganha ou "retorno" financeiro.
  - Fidelidade doutrinária e ao calendário litúrgico.
  - Imagens sacras com respeito. Não usar fotos de fiéis ou dizimistas sem
    consentimento (LGPD).
  - Uso correto da marca da Arquidiocese.
- Aprovador(es) do conteúdo: **pergunte ao Diogo** (pode ser alguém da Pastoral e
  não o próprio Diogo, e isso afeta o canal de aprovação).
- Frequência de posts por semana: **pergunte ao Diogo**, junto com a recomendação
  derivada do material de marca e do orçamento medido.

## PRINCÍPIOS DE EFICIÊNCIA A AVALIAR

Trate estes princípios como **hipóteses a validar com medição**, não como ordens. Se
algum se provar pior, descarte-o com evidência.

1. **LLM só onde há julgamento.** Calendário (inclusive o litúrgico, que pode ser
   calculado), pastas, agendamento, render, upload, publicação, métricas e
   verificações de formato ficam em código determinístico.
2. **Lote em vez de cadeia.** Gerar a semana inteira numa única chamada com saída
   estruturada (JSON validado por schema) contra 7 dias × N agentes. Compare custo
   e qualidade medidos.
3. **Contexto mínimo e estável.** Destile `docs/marca/` num "cartão de marca"
   compacto, com tamanho medido em tokens, e reutilize. Use um `CLAUDE.md` curto e
   skills com carregamento progressivo. Não releia arquivos grandes a cada etapa.
4. **Curadoria barata.** Checklist determinístico (tamanho, hashtags, termos
   proibidos, CTA, regras doutrinárias listáveis) mais uma autocrítica dentro da
   mesma geração, em vez de um agente curador que relê tudo. Meça se a qualidade se
   mantém.
5. **Arte por sistema de design, não por geração livre.** Templates HTML/CSS com os
   tokens da identidade visual. O LLM só preenche campos (JSON) e o render é feito
   por navegador headless. QA visual automático, também sem LLM: texto
   estourando a caixa via medição do DOM, contraste WCAG, área segura do Instagram,
   dimensões. Imagem gerada por IA só se o Diogo aprovar e com revisão humana.
6. **Modelo certo por tarefa.** Avalie, com medição, modelos menores (Sonnet 5 /
   Haiku 4.5) para etapas simples, e subagentes só quando o isolamento de contexto
   compensar o custo.
7. **Uma aprovação só, rica.** Avalie um único gate semanal com uma página de
   prévia (feed simulado com arte + legenda de todos os posts), com aprovar ou
   pedir ajuste por post, contra os dois gates do sistema anterior. Compare opções
   de canal (e-mail com link assinado, página estática, PR no GitHub etc.) por
   custo, segurança e fricção para quem aprova.
8. **Plano Pro contra API.** Calcule o custo mensal real em R$ das duas rotas: sessão
   interativa no plano Pro, e API com Batch (50% de desconto) + prompt caching num
   GitHub Action agendado. Use preços oficiais consultados e o consumo medido no
   piloto. A decisão é do Diogo. Apresente os números.
9. **Aprendizado agregado.** Análise e atualização do playbook mensais (ou a cada N
   posts), a partir de métricas coletadas por código, e não um agente por post.

## MODELO POR FASE

- **Fases 1 e 2 (pesquisa + arquitetura):** Claude Fable 5.1, se estiver disponível
  no plano; é a fase de maior alavancagem e roda uma vez só. Caso contrário, Opus
  5.5 com esforço alto.
- **Fases 3 e 4 (implementação + piloto):** Opus 5.5 (mais barato que o Fable
  5.1). Troque de modelo com `/model`.
- **Em produção:** o que o piloto provar ser o mais barato que mantém a qualidade.

## FASES (pare nos pontos marcados com ⛔)

**Fase 0 — Leitura.** Leia `docs/marca/` inteiro. Liste o que falta para operar
(ex.: paleta, fontes, logotipos, aprovador, frequência) e pergunte ao Diogo de uma
vez só. ⛔

**Fase 1 — Pesquisa validada.** Use subagentes em paralelo, com modelo mais barato
quando for pura leitura, para confirmar na documentação oficial atual:
- Instagram Graph API: requisitos de conta (Business/Creator + Página),
  permissões, modo Development para conta de terceiro em que o Diogo é admin,
  publicação de carrossel e reels, limites de publicação, validade e renovação de
  token, se existe agendamento nativo via API, e métricas de Insights disponíveis.
- Claude Code: subagentes (modelo por subagente), skills, hooks, headless e
  GitHub Actions, medição de uso.
- Anthropic API: Batch, prompt caching, preços atuais.
- Render e hospedagem de mídia: opções gratuitas ou baratas com URL pública,
  exigida pela API do Instagram.
- Fontes oficiais da Igreja sobre o dízimo.
Registre tudo em `docs/pesquisa.md`, com link por afirmação.

**Fase 2 — Proposta de arquitetura.** Em `docs/arquitetura.md`:
- Diagrama do fluxo.
- Pelo menos 2 alternativas comparadas em custo por semana (tokens e R$), trabalho
  manual por semana (minutos e cliques), riscos e qualidade esperada.
- Recomendação e orçamento de tokens por etapa.
- Rubrica de qualidade objetiva (texto e arte), derivada de `docs/marca/`.
- Plano de testes.
⛔ Aguarde aprovação do Diogo.

**Fase 3 — Implementação incremental.** Uma fatia vertical por vez, cada uma com
teste automatizado e ADR. Portão de publicação imposto por código e com teste
provando que post não aprovado não sai. Idempotência em tudo que roda por agenda.
Alerta por e-mail em caso de falha.

**Fase 4 — Piloto medido.** Gere uma semana real:
- Meça tokens por etapa e total, e o tempo.
- Avalie cada post na rubrica.
- Mostre a prévia ao Diogo.
- Publicação real só com aprovação explícita dele. ⛔
Entregue `docs/relatorio-piloto.md` com os números medidos, comparação com os fatos
do sistema anterior, o que falhou e o que ajustar.

## CRITÉRIOS DE PRONTO

- Semana completa (texto + arte) gerada numa única sessão, com consumo **medido**
  e reportado.
- Qualidade ≥ rubrica em todos os posts do piloto.
- Aprovação humana obrigatória, imposta e testada.
- Publicação, métricas e renovação de token automáticas e testadas.
- `README.md` com o passo a passo operacional semanal em no máximo 10 linhas.
- Toda decisão com ADR e fonte.

Comece pela Fase 0.
