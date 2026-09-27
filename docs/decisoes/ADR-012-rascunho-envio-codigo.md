# ADR-012 — Rascunho no aparelho, envio com código, limite de tentativas e termo neutro

Data: 2026-09-27. Status: aceito (implementado, validado em ambiente de teste isolado e implantado;
evidências em `docs/validacao/2026-09-27-painel-rascunho-envio.md`). Atualiza o ADR-011 (decisões 5 e 6).

## Contexto
O Diogo pediu: (1) nenhuma menção ao cargo do aprovador no sistema — termo neutro "aprovador";
(2) respostas marcadas como rascunho e enviadas de uma vez com um código curto dado por ele;
(3) estado público; link sem código; (4) validação real. Depois, relatou que no celular o painel não aparecia.

## Decisões
1. **Termo neutro.** Autor gravado: `"Aprovador"`; secret `CODIGO_APROVADOR` (o antigo foi apagado do
   Worker). Textos da página, do gerador da prévia da estreia, ADRs, testes e scripts usam "aprovador".
   Ficam, por não serem do sistema: a estratégia de marca (`docs/marca/`, lives "com padre") e a bio real
   do perfil (`@pe.alexjr`).
2. **Rascunho → Enviar.** Aprovar / Pedir ajuste / Desfazer viram rascunho no `localStorage`
   (`pastoral-painel-rascunho-v1`, sempre com try/catch) e aparecem nos blocos como **"a enviar"**;
   "Agendadas" continua mostrando só o que já vale no servidor. "Enviar respostas" abre um diálogo que pede
   o código (campo de senha, nunca guardado). A página apaga o código guardado pela versão anterior.
3. **Código só no Worker.** `CODIGO_APROVADOR` é gravado por stdin (`wrangler secret put`); o valor não
   está no HTML, no JS nem no repositório. Comparação sensível a maiúsculas, em tempo constante (sha256 dos
   dois lados, sem saída antecipada). Formato aceito: 1–128 caracteres ASCII visíveis.
4. **Limite de tentativas** (`limite.js`, tabela `falhas_acesso`, migration `0002`): 5 códigos errados
   em 15 min vindos do mesmo IP (só o HMAC do IP) bloqueiam o envio por 15 min, com mensagem dizendo até
   que horas (Brasília); durante o bloqueio nem o código certo passa. Acertar apaga as falhas daquele IP;
   falhas com mais de 1 dia são apagadas. Liberar à mão:
   `… d1 execute pastoral-aprovacoes --remote --command "DELETE FROM falhas_acesso"`.
5. **Envio em lote** `POST /api/decisoes {decisoes: [...]}` (até 10): lote malformado → 400 e nada é
   decidido; cada post é decidido à parte (GitHub e depois D1, idempotente, como no ADR-011); se um falha
   (409, 502…), os outros seguem e a resposta traz o resultado de cada um. A página manda **um post por
   pedido**, em sequência, por causa dos limites do plano gratuito (50 subpedidos e 10 ms de CPU por
   pedido; um carrossel de 10 artes já usa ~15 subpedidos); um 401/429 para tudo antes de gravar.
6. **Estado público**: `GET /api/estado` sem código, sem `ip_hash`. CORS continua restrito ao Pages.
7. **Link curto sem código**: `https://aprovar.pastoral-dizimo-aprovacao.workers.dev/` → 302 para a
   página. `/p/<código>` desativado (404) nos dois Workers.
8. **Celular — causa e correção.** Reproduzido com Playwright em emulação real (WebKit "iPhone 13"/"iPhone
   SE" e Chromium "Pixel 7"): tocar em "Aprovações (N)" dava `scrollY = 0` no WebKit. Instrumentando os
   eventos: o salto para `#painel` dispara `popstate`, e o manipulador tratava todo popstate sem post como
   "voltar do feed", chamando `fechar()` → `rolarPara(0)`. No Safari/iOS o salto acontece antes e o
   manipulador devolvia a página ao topo; no Chromium o salto vem depois, por isso lá funcionava. Sem o
   manipulador, o mesmo toque chegava a y = 917. Correção: `fechar()` só se o feed estiver aberto; o
   botão rola até o painel por JS (sem mexer no histórico), abre "Pendentes" e some enquanto o painel está
   na tela, para não cobrir o "Enviar respostas" (fixo no pé do painel). Teste de regressão no WebKit e no
   Chromium, que falha com o código antigo.

## Consequências e riscos
- O código é curto: a proteção é o limite por IP. Alguém com muitos IPs pode tentar mais vezes; se isso
  preocupar, trocar por um código mais longo (o Worker aceita até 128 caracteres) ou acrescentar um limite
  global — que, por outro lado, deixaria um atacante bloquear o aprovador.
- Quem souber o código decide como "Aprovador". Trocar: `printf '%s' '<novo>' | wrangler secret put CODIGO_APROVADOR`.
- Rascunhos ficam só no aparelho: trocar de celular ou limpar os dados do navegador apaga o que não foi enviado.
