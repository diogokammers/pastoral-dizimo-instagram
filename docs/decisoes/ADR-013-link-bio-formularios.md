# ADR-013 — Link na bio com formulários de escuta (agentes e fiéis)

Data: 2026-09-28. Status: aceito (implementado e implantado; envio real conferido e apagado).
Revoga a nota "Link na bio: nenhum por enquanto" de `content/estreia/bio.md` (ADR-003/005).
Spec: `docs/superpowers/specs/2026-09-28-link-bio-formularios-design.md` · plano: `docs/superpowers/plans/2026-09-28-link-bio-formularios.md`.

## Contexto
O Diogo pediu uma página curta para o link da bio, com um formulário para coletar dificuldades, pedidos de
capacitação e outros, com caminho separado para agentes e para fiéis. Todas as respostas devem ficar num
lugar só, para levantamentos e estatísticas futuras, e não podem ser públicas (o repositório é público).

## Decisões
1. **Endereço:** `https://dizimoarquifln.pages.dev` (Cloudflare Pages, projeto `dizimoarquifln`, conta da
   Pastoral). Grátis, curto e sem "github" no link. Domínio próprio fica como evolução opcional (pago).
2. **Página:** dois botões, "Sou agente da Pastoral" e "Sou fiel" (não "dizimista": o cartão de marca proíbe o
   termo como rótulo de pessoa identificável). Paleta e fontes do `config.yaml`, linguagem simples (ADR-010).
3. **Fonte única:** `content/formularios.yaml` (textos e opções) e `content/paroquias.yaml` (82 entradas do
   site da Arquidiocese, "Cidade - Nome (Bairro)", em ordem alfabética). `python -m pastoral.links` gera a
   página e o `links/lib/campos.js` do servidor: navegador e servidor validam contra as mesmas listas.
   Mudou uma opção? Suba `versao` (gravada em cada resposta) e gere de novo.
4. **Temas** do formulário do agente = orientações do Doc. CNBB 106, Cap. II (números no YAML).
5. **Contato** opcional, exceto nos pedidos de capacitação e de material (sem contato não há como atender).
6. **Consentimento** destacado e obrigatório (LGPD art. 11: vínculo religioso é dado sensível), com a
   finalidade e o e-mail para pedir exclusão.
7. **Dados:** Pages Function `POST /api/resposta` grava no D1 **`pastoral-formularios`** (separado do D1 de
   aprovação), tabela `respostas` append-only, sem IP. Limite de 10 envios por IP por hora (só o HMAC do IP,
   secret `IP_HMAC_SECRET` gerado aleatório e gravado direto no Pages, sem passar pela conversa), campo
   invisível contra robôs e corpo ≤ 16 KB.
8. **Centralização privada:** `python -m pastoral.formularios --exportar [--push]` grava `respostas.jsonl` e
   `respostas.csv` no clone do repositório **privado** `diogokammers/pastoral-dizimo-dados` (pasta irmã,
   `formularios.dados_dir`) e faz o commit lá. Recusa gravar dentro deste repositório; `.gitignore` bloqueia
   `respostas*.jsonl/csv` aqui. No CSV, texto que começa com = + - @ ganha ' (não vira fórmula).

## Consequências
- O link na bio é trocado à mão no app (a API não edita bio — ADR-005).
- A exportação é manual (sob demanda). Painel de estatísticas, aviso por e-mail e captcha ficaram de fora.
- Pedido de exclusão: apagar a linha no D1 e exportar de novo; o histórico git do repositório de dados ainda
  guarda a versão antiga (reescrever o histórico para exclusão completa).
- Implantação: D1 na região ENAM; a 1ª criação do projeto Pages deu erro 500 da API e passou na 2ª tentativa;
  o domínio levou alguns minutos (522) até responder. Envio com acentos conferido pelo navegador; o curl do
  Git Bash no Windows manda acentos fora de UTF-8 (não é defeito do site).
