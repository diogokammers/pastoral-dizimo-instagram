# ADR-015 — Uma publicação por semana (quarta, 18h) e fila por ordem de aprovação

Data: 2026-10-19. Status: aceito. Altera o ADR-000 (ritmo), o ADR-008 (portão) e o ADR-011 (versão do post).

## Contexto
O Diogo pediu: passar a publicar **um post por semana, às quartas-feiras às 18h**; no site de aprovação,
manter a publicação que já está aprovada para **esta quarta** e **tirar a data das demais**: quando forem
aprovadas, elas entram numa fila e saem **na ordem em que foram aprovadas**, uma por quarta.

Situação em 2026-10-19: o post 7 (2026-W41) foi aprovado às 19:03 com a data antiga (09/10, já passada);
pelo portão de então ele sairia na terça 20/10 às 19h. Os posts 8–11 (W42 e W43) estão gerados, sem aprovação,
com datas provisórias de terça/sexta.

## Decisões
1. **Ritmo** (`config.yaml`): `posts_por_semana: 1`, `dias: [{dia: quarta, hora: "18:00"}]`, `fila: true`.
   A numeração da série continua de onde parou: `pauta.ritmos_anteriores` guarda que até 2026-W43 saíam
   2 posts por semana (posts 4–11); de 2026-W44 em diante é 1 por semana, a partir do post 12. Regerar a
   pauta de uma semana antiga dá o mesmo briefing de antes (determinismo mantido).
2. **Agenda sem data.** Com `fila: true`, `preview.py` grava `agendado_para: null` no `agenda.json` (a data
   do briefing vira só referência). Um post pode ter data fixa: campo `agendado_para` (ISO com fuso) no
   post do `briefing.json`, ou editando o `agenda.json`. A data fixa significa "não antes de": o post sai
   na primeira quarta às 18h a partir dela.
3. **Carimbo por post.** `montar_aprovacao` (Python e JS, vetores cruzados) passa a gravar `aprovado_em` em
   cada item de `posts[]` do `aprovacao.json`; o carimbo do arquivo continua sendo o da última decisão.
   Itens já existentes sem o campo usam o carimbo do arquivo. A idempotência ignora o carimbo.
4. **Portão com fila** (`publicar.py`, `fila.py`): a cada execução, com `fila: true`,
   - `S` = o último horário de publicação (quarta 18h, `America/Sao_Paulo`) até agora;
   - se alguma publicação do ledger saiu em `S` ou depois, a semana está servida: nada sai;
   - senão sai **uma** publicação: primeiro a de data fixa já vencida mais antiga; se não houver, a da fila
     com `aprovado_em` mais antigo (empate: menor número). As outras ficam "aguarda a próxima quarta".
   - Alertas (código de saída 1, o GitHub avisa por e-mail): no dia da quarta sem nada aprovado
     ("fila vazia") e na véspera (até 30 h antes) sem nenhuma aprovação pronta. O alerta de post com data
     fixa sem aprovação (ADR-014) continua.
   Com `fila` desligada, o portão se comporta como antes (todo aprovado com data vencida sai).
5. **Horário do disparo**: cron do Worker `0 21 * * *` (18:00 em Brasília) e reserva do GitHub
   `15 21 * * *`; continuam diários, para o portão se recuperar sozinho se uma quarta falhar (a semana
   fica "não servida" até sair).
6. **A data deixa de exigir reaprovação.** A versão do post (`versao_post`) continua sendo o hash do item,
   e o item da fila tem `agendado_para: null`, estável; a data real é escolhida pelo sistema. Por isso o
   post 7 mantém no `agenda.json`/`aprovacao.json` a data antiga (09/10, vencida): a aprovação de hoje
   continua válida, a versão não muda no painel e o portão o publica na **quarta 21/10 às 18h** (regra 4).
   Não se reassina `aprovacao.json` fora do Worker/portão (o segredo não está na máquina do Diogo).
7. **Painel** (`simulador.py`): item sem data mostra "Sem data fixa: ao ser aprovada entra na fila (uma
   publicação por quarta-feira, às 18h)"; "Agendadas" ordena os aprovados como o portão (data fixa vencida
   primeiro, depois ordem de aprovação pelo `criado_em` do evento) e mostra a quarta prevista de cada um,
   calculada no navegador a partir de agora (previsão, no horário do aparelho). Prévia semanal e e-mail
   mostram "na fila" quando não há data.

## Consequências e riscos
- Dois posts com data fixa vencida na mesma semana saem em quartas seguidas, não juntos.
- Se o portão não rodar por duas semanas, sai só uma publicação (a quarta perdida não é recuperada).
- A previsão do painel depende do relógio do aparelho; a verdade é o portão.
- `semanal.yml` (desligado) e `gerar-reserva.yml` passam a gerar 1 post por semana a partir de 2026-W44.
