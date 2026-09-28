# Link na bio + formulários de escuta — especificação

Data: 2026-09-28 · Aprovado em conversa pelo Diogo · Decisão formal: ADR-013 (a escrever na implementação).

## Objetivo
Uma página curta de links para a bio do @pastoraldodizimo.arquifln, com dois caminhos:
**"Sou agente da Pastoral"** (dificuldades, pedidos de capacitação e de material, sugestões) e
**"Sou fiel"** (dúvidas, sugestões, desejo de participar). Todas as respostas ficam num único lugar
privado, prontas para levantamentos e estatísticas futuras.

## Fora do escopo (por agora)
Painel de estatísticas, aviso por e-mail a cada resposta, captcha, outros links na página
(o espaço existe, mas fica vazio até o Diogo confirmar cada link — nada é inventado).

## 1. Endereço
- Cloudflare Pages, projeto `pastoraldodizimo` → `https://pastoraldodizimo.pages.dev`
  (se o nome estiver ocupado: `dizimoarquifln`, depois `pastoraldizimo`; registrar o escolhido na ADR-013).
- Conta Cloudflare da Pastoral (mesmo login do Worker; `XDG_CONFIG_HOME="C:/Users/odnac/.config-pastoral-dizimo"`).
- Sem GitHub no endereço. Domínio próprio `.com.br` fica como evolução opcional (pago).

## 2. Página (`links/public/index.html`)
- HTML + CSS + JS puro, um arquivo; mobile-first; sem dependência externa além das fontes (Google Fonts:
  Cormorant Garamond 600, Source Sans 3 400/600).
- Paleta do `config.yaml` (`visual.paleta`): fundo creme `#F2E8D5`, títulos vermelho `#A3121C`, texto grafite
  `#1E1B1B`, apoio cinza `#5F5A57`, filetes dourado `#B08D3B` (nunca texto dourado).
- Topo: nome "Pastoral do Dízimo", linha "Arquidiocese de Florianópolis", lema "Deus ama quem dá com alegria" (2Cor 9,7).
- Dois botões grandes; cada um abre o seu formulário na mesma página (sem recarregar).
- Textos em linguagem simples (ADR-010) e sem termos proibidos do cartão de marca (teste automático).
- Após enviar: mensagem de agradecimento; em erro: mensagem clara e o texto digitado preservado.

## 3. Formulários

### 3.1 Agente da Pastoral (`tipo = "agente"`)
| Campo | Tipo | Obrigatório |
|---|---|---|
| paroquia | lista (`content/paroquias.yaml`) + "Outra" | sim |
| paroquia_outra | texto (≤ 120) | se paroquia = "Outra" |
| funcao | coordenador(a) · membro da equipe · pároco ou vigário · diácono · outra | sim |
| pedido | dificuldade na pastoral · pedido de capacitação · pedido de material · sugestão · outro | sim |
| temas | múltipla escolha (lista 3.3) | ao menos 1 |
| descricao | texto (≤ 2000) | sim |
| nome, contato | texto (≤ 120 cada; e-mail ou WhatsApp) | **só se pedido = capacitação ou material** |
| consentimento | caixa | sim |

### 3.2 Fiel (`tipo = "fiel"`)
| Campo | Tipo | Obrigatório |
|---|---|---|
| paroquia | lista + "Outra" + "Prefiro não dizer" | não |
| assunto | dúvida sobre o dízimo · sugestão · quero servir na Pastoral · outro | sim |
| mensagem | texto (≤ 2000) | sim |
| nome, contato | texto (≤ 120 cada) | não |
| consentimento | caixa | sim |

"dizimista" não aparece como rótulo de pessoa (cartão de marca, LGPD). "Quero servir", nunca "voluntário".

### 3.3 Temas (Doc. CNBB 106, Cap. II — fichamento docs/pesquisa/07)
Sentido do dízimo e motivação da comunidade (n. 37, 75, 83) · Implantação ou retomada do dízimo na paróquia
(n. 37–45) · Organização e funcionamento da equipe (n. 46–50) · Formação dos agentes: espiritual, humana e
técnico-organizativa (n. 64) · Acolhida e visitas missionárias (n. 76) · Cadastro e comunicação com os fiéis
(n. 76) · Registro, recibo e aspectos legais (n. 52, 54) · Prestação de contas e transparência (n. 55, 79) ·
Relação com os Conselhos Econômico e Pastoral (n. 58–59) · Participação do clero (n. 46, 62) · Dízimo na
catequese e na preparação dos noivos (n. 71) · Linguagem sobre o dízimo (n. 56–57) · Outro.
A página mostra só o nome do tema (sem o número); os números ficam no código-fonte como comentário.

### 3.4 Consentimento (texto, destacado acima do botão Enviar)
"Autorizo a Pastoral do Dízimo da Arquidiocese de Florianópolis a guardar estas respostas para planejar
formações e responder ao meu pedido. Os dados não são publicados nem repassados. Para pedir a exclusão,
escreva para pastoraldodizimo.arquifln@gmail.com." (Dados que revelam vínculo religioso são sensíveis — LGPD art. 11:
consentimento específico e destacado.)

### 3.5 Paróquias (`content/paroquias.yaml`)
Lista pública copiada de https://arquifln.org.br/paroquias em 2026-09-28, formato `Nome — Cidade (Bairro)`,
com `fonte` e `consultado_em` no arquivo. Conferida linha a linha contra o site na implementação
(a leitura automática divergiu na contagem; o site cita 76 paróquias). A página recebe a lista embutida
no build (script gera o trecho JS a partir do YAML; teste garante que estão iguais).

## 4. Dados
- Função do Pages `links/functions/api/resposta.js` (mesma origem, sem CORS), binding `DB` para o D1 novo
  **`pastoral-formularios`** (separado de `pastoral-aprovacoes`).
- Tabela `respostas` (append-only): `id` (UUID), `criado_em` (ISO UTC), `tipo`, `dados` (JSON dos campos),
  `versao_form` (inteiro, começa em 1). Nada de IP guardado junto da resposta.
- Tabela `envios_ip`: `ip_hash` (HMAC-SHA256 do IP com o secret `IP_HMAC_SECRET` do Pages), `criado_em`.
  Limite: 10 envios por IP por hora → HTTP 429; registros com mais de 1 dia apagados a cada envio.
- Anti-spam: campo invisível `site` (honeypot) preenchido → responde 200 e descarta; corpo ≤ 16 KB.
- Validação no servidor espelha a do navegador (campos, listas fechadas, tamanhos, obrigatório condicional);
  inválido → 400 com lista de campos.
- Migrations em `links/migrations/`.

## 5. Exportação para o repositório privado
- Repositório **privado** `diogokammers/pastoral-dizimo-dados`, clonado **fora** do repositório público
  (padrão: pasta irmã `../pastoral-dizimo-dados`; caminho configurável em `config.yaml` → `formularios.dados_dir`).
- `python -m pastoral.formularios --exportar [--dados-dir CAMINHO]`:
  1. lê `SELECT * FROM respostas ORDER BY criado_em` via `wrangler d1 execute pastoral-formularios --remote --json`
     (login da Pastoral);
  2. regrava `respostas.jsonl` (histórico completo, uma linha por resposta) e `respostas.csv`
     (UTF-8 com BOM, para Excel; temas em uma coluna separados por " | ");
  3. faz `git add` + `git commit` no repositório de dados (não faz push sozinho; `--push` opcional).
- Recusa rodar se `dados_dir` estiver dentro do repositório público (proteção contra vazamento).
- `.gitignore` do repositório público inclui `respostas*.jsonl` e `respostas*.csv`.

## 6. Instagram
- ADR-013 revoga "Link na bio: nenhum por enquanto" (`content/estreia/bio.md`, ADR-003) e registra endereço,
  D1 e repositório de dados. A troca do link no app é manual (a API não edita bio — ADR-005).

## 7. Testes
- `links/test/` (node:test + node:sqlite, como `worker/`): validação por tipo, obrigatório condicional,
  honeypot, limite por IP (429), corpo grande, gravação.
- `tests/test_formularios.py` (pytest): exportador (JSONL/CSV, recusa de pasta dentro do repo, sem push por padrão),
  paróquias YAML == lista embutida na página, textos da página sem termos proibidos nem "%".
- `tests/test_links_navegador.py` (Playwright, Chromium + WebKit celular): abre cada formulário, valida,
  envia com a API simulada.

## 8. Credenciais
Só nomes: secret `IP_HMAC_SECRET` no projeto Pages (`wrangler pages secret put IP_HMAC_SECRET`), cadastrado
pelo Diogo. Nenhum valor no repositório nem na conversa.
