# ADR-014 — Publicação na hora e sem falha silenciosa

Data: 2026-10-13. Status: aceito. Complementa o ADR-008 (portão) e o ADR-012 (rascunho → envio).

## Contexto
O post 6 (2026-W41, agendado para 06/10) foi aprovado pelo aprovador, mas não foi publicado. Diagnóstico:
- o D1 só tinha um evento (post 4, 28/09) e `falhas_acesso` só um registro de 27/09: a aprovação ficou como
  **rascunho no aparelho** e nunca foi enviada com o código (ADR-012, decisão 2);
- o portão rodou todos os dias em modo real e, sem `aprovacao.json`, terminou "com sucesso" sem avisar ninguém;
- além disso, o cron do GitHub (`15 22 * * *`) rodava com 3–5 h de atraso (entre 22h e 0h de Brasília).

## Decisões
1. **Alerta no portão** (`publicar.py`): post da `agenda.json` com data a até 30 h de agora (véspera e o
   próprio dia), fora de qualquer `aprovacao.json` e do ledger, sai como `[ALERTA] … SEM APROVAÇÃO` e o
   comando retorna 1: o job fica vermelho e o GitHub avisa por e-mail.
2. **Disparo na hora**: o Worker de aprovação ganhou o cron `0 22 * * *` (19:00 em Brasília), que manda
   `repository_dispatch` `publicar` (`EVENTO_PUBLICAR`); o `publicar.yml` aceita esse evento como execução
   real. O cron do GitHub continua como reserva (o ledger impede publicar duas vezes).
3. **Rascunho visível no painel**: com resposta não enviada, o aviso do topo fica vermelho
   ("N respostas ainda NÃO foram enviadas…") e fechar a página pede confirmação (`beforeunload`).

## Consequências
- Post da reserva com data provisória perto de hoje e ainda não aprovado também deixa o job vermelho: é o
  aviso desejado (ou se aprova, ou se reagenda a `agenda.json`).
- Os dois crons (Worker e GitHub) podem gerar dois e-mails de alerta no mesmo dia.
