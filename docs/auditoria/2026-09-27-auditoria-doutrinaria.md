# Auditoria doutrinária e editorial — 2026-09-27

Regra do Diogo: os posts só afirmam o que está em **quatro fontes**, sempre com número:
(1) Doc. CNBB 106 (só o conferido em `docs/pesquisa/06-cnbb-doc-106.md`, inclusive a "Segunda leitura");
(2) Catecismo da Igreja Católica (CIC); (3) Código de Direito Canônico (CDC); (4) Bíblia católica.

Escopo auditado: `content/estreia/posts.json` (posts 1–3, **publicados**, arquivo não alterado), `content/estreia/bio.md`,
`content/semanas/2026-W40/posts.json` e `content/semanas/2026-W41/posts.json` (reserva, corrigida), `cartao-marca.md` (corrigido) e o lint.

Vereditos: **OK** (sustentado pela fonte) · **AJUSTAR** (sustentável, mas com atribuição, redação ou classificação imprecisa) · **REMOVER** (fora do escopo das 4 fontes).

---

## 1. Fontes conferidas nesta auditoria

Textos do CIC e do CDC lidos no vatican.va (edição em português de Portugal) em 2026-09-26.

| Fonte | O que diz (paráfrase; trechos literais curtos) | Uso |
|---|---|---|
| CIC 2041 | Os preceitos da Igreja se inserem numa vida moral ligada à vida litúrgica; são cinco | Contexto do 5º preceito |
| CIC 2043 | 5º preceito: "prover às necessidades materiais da Igreja consoante as possibilidades de cada um" | Dever de sustentar a Igreja, sem percentual |
| CIC 1350 | Apresentação das oferendas (pão e vinho) no ofertório | Contexto litúrgico |
| CIC 1351 | Desde o princípio, com o pão e o vinho para a Eucaristia, os cristãos trazem ofertas para a partilha com os necessitados; "costume... da colecta" | **Oferta** (post 5) |
| CIC 1368 | Na Eucaristia a vida dos fiéis (louvor, trabalho, sofrimento) une-se à oblação de Cristo | Não trata de dinheiro; não usar para "oferta" em sentido material |
| CIC 2101–2103 | Promessas e votos a Deus (inclui "uma esmola" como promessa de devoção) | Não trata de dízimo nem de oferta na Missa; não usar |
| CIC 897 | Leigos: batizados que participam, a seu modo, da função sacerdotal, profética e real de Cristo | Quem é o agente |
| **CIC 910** | Os leigos podem ser chamados a "colaborar com os pastores no serviço da comunidade eclesial", exercendo ministérios muito variados | **Termo escolhido para o agente** |
| CIC 911 | Leigos nos conselhos pastorais e nos conselhos para assuntos econômicos | Apoia Doc. 106, n. 63–66 |
| CIC 2039 | "Os ministérios devem exercer-se num espírito de serviço fraterno e de dedicação à Igreja" | Citação do post 4 |
| CIC 1547, 1551 | O sacerdócio ministerial está "ao serviço" do sacerdócio comum; é "um verdadeiro serviço" | Serviço é próprio do ministério ordenado; para o leigo usar CIC 910 |
| CIC 1936–1937 | Diferenças de talentos para a partilha e a caridade mútua | Não necessário |
| cân. 222 §1 | Os fiéis têm a obrigação de prover às necessidades da Igreja: culto divino, obras de apostolado e de caridade, honesta sustentação dos ministros | Posts 3 e 7 |
| cân. 1254 §2 | Fins próprios dos bens da Igreja: culto, sustento do clero e ministros, apostolado e caridade, sobretudo aos necessitados | Base do Doc. 106, n. 34–35 |
| cân. 1260 / 1261 §1 | A Igreja pode pedir aos fiéis o necessário; "os fiéis têm liberdade de contribuir" | Liberdade do gesto |
| cân. 1262 | Os fiéis concorrem segundo normas da Conferência episcopal | Contexto (CNBB) |
| cân. 1266 | O Ordinário do lugar pode mandar fazer coleta especial para obras paroquiais, diocesanas, nacionais ou universais | Post 5 (legenda) |

**Termo para o agente:** *leigo que colabora com os pastores no serviço da comunidade eclesial* (cf. CIC 910), vivendo o ministério "num espírito de serviço fraterno e de dedicação à Igreja" (CIC 2039). Formas curtas: "serve", "presta um serviço à comunidade". "Voluntário" não aparece em nenhuma das 4 fontes para esse papel e passou a ser erro de lint.

**Bíblia:** 2Cor 9,7 tem redação conferida (citada no Doc. 106, n. 10). Rm 15,26-27 existe e é citado no Doc. 106, n. 22 (coleta para os pobres de Jerusalém); é usado só como referência, sem aspas. Nenhum outro versículo é citado entre aspas.

---

## 2. Publicados (1–3): correções recomendadas para editar a legenda no Instagram

A arte (slides) não pode ser editada depois de publicada; só a legenda e o texto alternativo. Nenhum slide publicado afirma algo **falso**; os problemas são de atribuição ou de classificação, e a legenda nova corrige.

### Post 1 — "Bem-vindos à Pastoral do Dízimo"

| Onde | Afirmação | Fonte (nº) | Veredito | Correção |
|---|---|---|---|---|
| Slide 1 + alt | Capa institucional | — (identificação) | OK | — |
| Slide 2 + alt | Pastoral "a serviço das paróquias, dos agentes e de cada fiel" | CIC 910 (serviço da comunidade eclesial) | OK | — |
| Slide 3 + alt | Missão: evangelizar, formar, comunicar, fiel ao Magistério | Institucional; Doc. 106, n. 6 (pessoas evangelizadas), n. 63–66 (formação) | OK | — |
| Slide 4 + alt | Dízimo: fé, gratidão, corresponsabilidade; gesto livre, "nascido do coração" | n. 29 (gratidão), n. 6 (corresponsabilidade), n. 9 (decisão pessoal), 2Cor 9,7 (coração) | OK (sem citação na arte) | Citar na legenda |
| Slide 5 + alt | O que o perfil vai oferecer | Institucional | OK | — |
| Slide 6 + alt | Em comunhão com o Arcebispo, párocos e equipes | CIC 910; Doc. 106, n. 63–66 | OK | — |
| Slide 7 + alt | CTA "seguir o perfil" | — | OK | — |
| Legenda | "gesto livre, que nasce de um coração agradecido" | "coração agradecido" era a frase atribuída por engano ao n. 9; sem fonte literal | AJUSTAR | Ancorar em n. 6, 9, 29 e 2Cor 9,7 |
| `fontes` (interno) | 2Cor 9,7 "conferir a redação" | Doc. 106, n. 10 | OK (já conferido) | — |

**Legenda nova (colar no Instagram, 933 caracteres, passa no lint):**

```text
Bem-vindos! Este é o perfil da Pastoral do Dízimo da Arquidiocese de Florianópolis.

Aqui vamos partilhar formação bíblica e catequética sobre o dízimo, a vida das paróquias, a agenda da Pastoral e respostas às dúvidas mais comuns.

Nossa missão é evangelizar, formar e comunicar, com fidelidade ao Magistério, em comunhão com o Arcebispo, os párocos e as equipes paroquiais, colaborando com os pastores no serviço da comunidade eclesial (cf. CIC 910).

O dízimo é contribuição sistemática e periódica pela qual a comunidade assume corresponsavelmente sua sustentação e a da Igreja (cf. Doc. CNBB 106, n. 6). Nasce de uma decisão pessoal, como manifestação espontânea da fé (cf. Doc. CNBB 106, n. 9), e expressa gratidão a Deus, de quem provém tudo (cf. Doc. CNBB 106, n. 29).

Nosso lema vem da Palavra: "Deus ama quem dá com alegria" (2Cor 9,7).

Siga o perfil e caminhe conosco.

Pastoral do Dízimo — Arquidiocese de Florianópolis
```

### Post 2 — "O que é o dízimo?"

| Onde | Afirmação | Fonte (nº) | Veredito | Correção |
|---|---|---|---|---|
| Slide 1 + alt | "Uma resposta livre ao amor de Deus" | n. 7 (experiência de Deus), n. 9 (decisão pessoal) | OK (síntese) | — |
| Slide 2 + alt | Resposta agradecida de quem reconhece que tudo vem de Deus | n. 29 (Deus, de quem provém tudo; gratidão) | OK (sem citação na arte) | Citar n. 29 na legenda |
| Slide 3 + alt | Decisão pessoal; manifestação espontânea da fé e da pertença | n. 9 | OK | — |
| Slide 4 + alt | Quantia: decisão da consciência, iluminada pela Palavra | n. 10 | OK | — |
| Slide 5 + alt | "Deus ama quem dá com alegria" | 2Cor 9,7 (redação no n. 10) | OK | — |
| Slide 6 + alt | "Não se reduz a manter estruturas: nasce da fé, da partilha e da pertença" (cf. n. 12) | n. 12 diz só "não unicamente captação de recursos"; "fé e pertença" estão no n. 28 (e n. 9); "partilha" no n. 25 | AJUSTAR (atribuição) | Legenda cita n. 12 **e** n. 28 |
| Legenda | "começa no coração, não no bolso" | 2Cor 9,7; n. 25 (significado interior) | AJUSTAR (sem fonte) | Trocar pela citação de 2Cor 9,7 |
| Legenda | "sua riqueza está na fé, na partilha e na pertença (cf. n. 12)" | Não está no n. 12 | AJUSTAR | "ligado à vivência da fé e à pertença a uma comunidade eclesial (n. 28)" |
| Legenda | "sustento da sua vida e da missão da Igreja (n. 6)" | n. 6: "sua sustentação e a da Igreja" | AJUSTAR (redação) | Seguir o n. 6 |

**Legenda nova (916 caracteres, passa no lint):**

```text
O dízimo começa no coração: "Cada um dê conforme tiver decidido em seu coração" (2Cor 9,7).

Ele expressa a gratidão de quem reconhece que tudo provém de Deus (cf. Doc. CNBB 106, n. 29). Por isso é um gesto livre: nasce de uma decisão pessoal e é manifestação espontânea da fé e da pertença (cf. Doc. CNBB 106, n. 9), e a quantia é decisão da consciência de cada um, iluminada pela Palavra (cf. Doc. CNBB 106, n. 10).

A CNBB lembra que o dízimo não pode ser proposto unicamente como forma de captar recursos (cf. Doc. CNBB 106, n. 12): ele está ligado à vivência da fé e à pertença a uma comunidade eclesial (cf. Doc. CNBB 106, n. 28). Pelo dízimo, a comunidade assume corresponsavelmente sua sustentação e a da Igreja (cf. Doc. CNBB 106, n. 6).

"Deus ama quem dá com alegria" (2Cor 9,7).

Salve este post para rever sempre que alguém perguntar o que é o dízimo.

Pastoral do Dízimo — Arquidiocese de Florianópolis
```

### Post 3 — "Para onde vai o dízimo?"

| Onde | Afirmação | Fonte (nº) | Veredito | Correção |
|---|---|---|---|---|
| Slide 1 + alt | "Quatro dimensões de um mesmo gesto de fé" | Doc. 106, seção 3, n. 29–32 | OK | Agora pode ser atribuído ao Doc. 106 |
| Slide 2 + alt | Religiosa: gratidão a Deus **e sustenta o culto e a vida celebrativa** | n. 29 = gratidão, fé, conversão, Deus Senhor dos bens. O **culto** está no n. 30 (eclesial) e no n. 34 / cân. 222 §1 | AJUSTAR (classificação) | Afirmação verdadeira, dimensão errada; a legenda nova segue o n. 29 |
| Slide 3 + alt | Eclesial: vida da comunidade, ministros, necessidades da Arquidiocese | n. 30 (Igreja particular); n. 34–35 e cân. 222 §1 (ministros) | OK | — |
| Slide 4 + alt | Missionária: abre às outras comunidades, "o Evangelho mais longe" | n. 31 (partilha entre paróquias e Igrejas particulares); epígrafe da seção 3 (crescimento do Reino) | OK | — |
| Slide 5 + alt | Caritativa: os pobres, coleta de Paulo (cf. Rm 15,26-27) | n. 22, n. 32–33; Rm 15,26-27 | OK | — |
| Slide 6 + alt | Fiéis proveem às necessidades: culto, apostolado, caridade, ministros | cân. 222 §1 | OK | — |
| Slide 7 + alt | CTA compartilhar | — | OK | — |
| Legenda | "Na caminhada pastoral, costuma-se apresentar o dízimo em quatro dimensões" | Afirmação genérica sem fonte; as dimensões **estão** no Doc. 106 | AJUSTAR | Atribuir ao Doc. 106, n. 29–32 |
| Legenda | Religiosa "sustenta o culto" | ver slide 2 | AJUSTAR | Seguir o n. 29 |
| `a_conferir` (interno) | "síntese pastoral, sem atribuição ao Doc. 106" | Regra revogada | Obsoleto | Só registro: o arquivo publicado não foi alterado |

**Legenda nova (964 caracteres, passa no lint):**

```text
Para onde vai o dízimo? Para a vida inteira da Igreja.

O Doc. CNBB 106, n. 29-32, apresenta quatro dimensões do dízimo:

Religiosa: reconhece que Deus é o Senhor de todos os bens e expressa gratidão, fé e conversão (n. 29).
Eclesial: nasce da consciência de ser membro da Igreja, provê o necessário para o culto e a missão e inclui a contribuição das paróquias à Igreja particular, a Arquidiocese (n. 30).
Missionária: partilha entre paróquias e entre Igrejas particulares, para o crescimento do Reino (n. 31).
Caritativa: cuida dos pobres, como a coleta de Paulo em favor de Jerusalém (cf. Rm 15,26-27; Doc. CNBB 106, n. 22 e 32).

O Código de Direito Canônico lembra que os fiéis proveem às necessidades da Igreja: o culto divino, as obras de apostolado e de caridade e a honesta sustentação dos ministros (cf. cân. 222 §1).

Compartilhe com sua paróquia e ajude sua comunidade a conhecer o sentido do dízimo.

Pastoral do Dízimo — Arquidiocese de Florianópolis
```

Observação: o teste `tests/test_estreia.py::test_post3_tem_as_quatro_dimensoes_sem_doc106` descreve o estado publicado do arquivo e continua passando. Se o Diogo editar a legenda no Instagram e quiser espelhar no repositório, esse teste deve ser atualizado junto.

### Bio (`content/estreia/bio.md`, aplicada)

| Afirmação | Fonte | Veredito |
|---|---|---|
| "Evangelizar, formar e fortalecer o dízimo: fé, gratidão e corresponsabilidade." | n. 6 (corresponsabilidade), n. 29 (gratidão), n. 7 (fé) | OK |
| "Deus ama quem dá com alegria" 2Cor 9,7 | Redação no Doc. 106, n. 10 | OK |
| Menções @pe.alexjr, @arquifloripa | Institucional | OK |

As propostas não aplicadas também estão dentro do escopo. Nenhuma correção na bio.

---

## 3. Reserva (W40 posts 4–5, W41 posts 6–7): o que estava errado e o que foi corrigido

| Post | Onde | Antes | Fonte / problema | Veredito | Depois |
|---|---|---|---|---|---|
| 4 | Slide 2, alt, legenda | "Dedica seu tempo, como voluntário" / "de forma voluntária" | "Voluntário" não está nas 4 fontes | REMOVER | "Leigo que colabora com os pastores no serviço da comunidade eclesial" (cf. CIC 910) |
| 4 | Slide 3, legenda | "nunca como instância paralela" | Vem da estratégia, não das 4 fontes | REMOVER | "Trabalha em equipe, inserido na Pastoral de Conjunto, participando dos Conselhos Pastoral e Econômico" (cf. Doc. 106, n. 63-66) |
| 4 | Slide 4 | "Ajuda a comunidade a entender o dízimo como partilha…" | Sem fonte específica | AJUSTAR | "A formação espiritual, humana e técnico-organizativa do agente é indispensável" (n. 63-66) |
| 4 | Slide 5, legenda | 2Cor 9,7 aplicado a "quem oferece seu tempo" | Extrapolação: o versículo trata da coleta | AJUSTAR | Citação trocada por CIC 2039 (serviço fraterno) |
| 4 | `a_conferir` | "confirmar se atuam de forma voluntária" | — | REMOVER | Pendência nova: redação do CIC (português de Portugal) |
| 5 | Slide 4, legenda | "O dízimo é distinto das ofertas" (Cap. II) | "Cap. II" vinha de slides de terceiros; o conferido é o n. 51 | AJUSTAR | Recolhido na Missa ou na Celebração da Palavra, "é preciso evitar confundi-lo com as ofertas" (n. 51) |
| 5 | **Slide novo 5** | — | Pedido do Diogo: explicar a oferta sem inventar | Novo | "E a oferta? Desde o princípio, os cristãos levam ofertas, com o pão e o vinho, para partilhar com os necessitados" (cf. CIC 1351) |
| 5 | Legenda | — | Coleta especial | Novo | cf. cân. 1266 (opcional, em `a_conferir`) |
| 6 | Legenda | "Neste Mês Missionário…" | Data comemorativa fora do escopo | REMOVER | Retirado |
| 6 | Legenda | Três passos genéricos ("sem pressa", "o que Deus fez nesta semana?") | Sem fonte | AJUSTAR | Passos ancorados em n. 29, 2Cor 9,7 e n. 6; significado interior (n. 25) |
| 7 | Legenda | "Neste Mês Missionário…" | Fora do escopo | REMOVER | Retirado |
| 7 | Slide 2 | "Partilha periódica" (n. 6) | O n. 6 diz "contribuição sistemática e periódica" | AJUSTAR | Redação do n. 6 |
| 7 | Slide 3 | "Quanto oferecer?" | Confunde com "oferta", justo no post que distingue os dois | AJUSTAR | "Quanto dar?" |
| 7 | Slide 5 | "São realidades distintas" (Cap. II) | Ver post 5 | AJUSTAR | n. 51 |
| 7 | Slide 6 | "Abre-se às outras comunidades e à Igreja Particular" (Cap. II) | Não conferido no exemplar | AJUSTAR | Finalidades: culto, clero e ministros, apostolado, caridade (n. 34-35; cân. 222 §1) |
| 7 | Slide 7, legenda | "nasce da fé e serve à missão" (n. 12) | Não está no n. 12 | AJUSTAR | n. 12 + n. 28 (vivência da fé e pertença eclesial) |

Resultado: `python -m pastoral.lint` = OK nos dois lotes; `pastoral.render` = 14 + 9 imagens, nenhuma reprovada no QA; prévias em `site/semanas/2026-W40/` e `site/semanas/2026-W41/`. Maior slide: 25 palavras (limite).

---

## 4. Cartão de marca e lint

- `cartao-marca.md`: nova seção **"Escopo de fontes"**; regra "dimensões = síntese pastoral" **revogada** e n. 25–35, 51, 52, 63–66 registrados; termos "Agente" (CIC 910, 2039; nunca "voluntário") e "Oferta" (n. 51 + CIC 1351 + cân. 1266); CIC e CDC conferidos no vatican.va; "Cap. II" genérico substituído por números; DGAE retiradas (fora do escopo).
- `src/pastoral/lint.py`: `PARAGRAFOS_DOC106` ampliado; regra "dimensões + 106" removida; CIC exige número 1–2865; cân./cânon exige número 1–1752; `TERMOS_FORA_DE_ESCOPO` ("Mês Missionário", "voluntário/a/os/as/ado", "Teresinha", "santo do dia") reprova; "números" por extenso aceito no alt-text.
- `src/pastoral/gerar.py`: o prompt explicita o escopo das 4 fontes e o termo do agente.
- `content/temas.yaml` e o briefing da W40: o resumo do tema do agente não diz mais "serviço voluntário".

## 5. Pendências e recomendações

1. **Diogo:** colar as três legendas novas nos posts 1–3 (seção 2).
2. **Diogo:** o CIC do vatican.va está em português de Portugal ("exercer-se", "num", "colecta"). A citação literal de CIC 2039 (post 4) segue esse texto; se preferir a edição brasileira da CNBB, conferir antes de aprovar.
3. `src/pastoral/calendario.py` ainda coloca no briefing "Mês Missionário" (outubro) e santos do dia (ex.: Santa Teresinha). O lint agora barra o uso no post, mas o ideal é o briefing parar de sugerir esses ganchos.
4. O lint ainda aceita "Doc. CNBB 106, Cap. II"; o cartão orienta citar só por número. Pode virar erro numa próxima rodada.

---

## 6. Semanas 3 e 4 (posts 8–11)

Escopo: `content/semanas/2026-W42/posts.json` (posts 8–9) e `content/semanas/2026-W43/posts.json` (posts 10–11), reserva gerada pelo `gerar.py`. Mesmo método e mesmos vereditos das seções 1–3, mais a linguagem do ADR-010.

**Fontes conferidas nesta rodada (2026-09-27):**
- CIC 1351 (vatican.va): as ofertas vêm "com o pão e o vinho para a Eucaristia", para a partilha com os necessitados; o costume da colecta é "sempre actual" e se inspira em Cristo, que Se fez pobre para nos enriquecer.
- CIC 833 (vatican.va): a Igreja particular é, "em primeiro lugar, a diocese". Base para traduzir "Igrejas particulares" (n. 31) por "dioceses".
- Bíblia, na Nova Vulgata (vatican.va; o site não tem tradução portuguesa): Gn 14,18-20 (Abrão dá a Melquisedec a décima parte de tudo); Gn 28,20-22 (voto de Jacó; o v. 22 é a décima parte "de tudo o que me deres"); Lv 27,30 (o dízimo da terra pertence ao Senhor); Dt 14,22-29 (dízimo anual comido diante do Senhor; no terceiro ano, para o levita, o estrangeiro, o órfão e a viúva); Ml 3,8-10 (defraudar a Deus, maldição, "provai-me" e bênção em abundância); At 4,34-35; 1Cor 12,12 e 27. A redação da Tradução Oficial da CNBB **não** foi lida: tudo parafraseado, sem aspas.

### Post 8 — "Comunhão entre paróquias" (W42)

| Afirmação | Fonte | Veredito | Correção |
|---|---|---|---|
| "Um só corpo" / somos o corpo de Cristo, cada um é membro | 1Cor 12,27 (citado no n. 28). "Um só corpo" é do v. 12, não do 27 | AJUSTAR | Título "Somos o corpo de Cristo" |
| "Nenhuma paróquia sozinha" (slide) / "Nenhuma paróquia caminha sozinha" | Frase pastoral genérica; o conteúdo está no n. 30–31 | AJUSTAR | Slide "Parte de algo maior"; legenda "Sua paróquia não caminha sozinha", seguida do n. 30 e 31 |
| Paróquias contribuem com a Igreja particular, a Arquidiocese | n. 30 | OK | — |
| Partilha entre paróquias e dioceses | n. 31 ("Igrejas particulares"); diocese = CIC 833 | OK | CIC 833 na linha "Fontes:"; `a_conferir` resolvido |
| — (faltava) | n. 31: paróquias-irmãs, fundo de comunhão e partilha | Novo | Slide "Exemplos da CNBB", sem atribuir projeto à Arquidiocese |
| Paulo e a coleta para a Judeia | n. 22 | OK | — |
| "inspira a partilha entre as Igrejas **até hoje**" | O n. 22 não diz "até hoje" | AJUSTAR | "até hoje" retirado |
| CTA "Marque aqui a paróquia vizinha nos comentários" | — | AJUSTAR (redação) | "Marque a paróquia nos comentários" |

### Post 9 — "O dízimo na Bíblia" (W42)

| Afirmação | Fonte | Veredito | Correção |
|---|---|---|---|
| Título "de Abraão a Malaquias" | Ml 3,10 é o texto preferido da leitura que o n. 27 declara inaceitável | REMOVER | "O dízimo na Bíblia: da décima parte à partilha" |
| "Malaquias chamou o povo a trazer o dízimo inteiro ao Templo" | Ml 3,10 diz isso, mas o mesmo versículo promete bênção em troca ("provai-me") e os v. 8-9 falam em defraudar a Deus e em maldição. Citar só a metade é seletivo; citar inteiro contraria o n. 27 e o cartão (culpa associada a não dizimar) | REMOVER | Parágrafo e referência retirados |
| — (faltava) | n. 27: inaceitável propor o dízimo como negociação com Deus | Novo | "O dízimo não é uma troca com Deus…" (sem a palavra "prosperidade", proibida no perfil) |
| Abraão deu a Melquisedec a décima parte de tudo | Gn 14,18-20 | OK | — |
| Jacó prometeu a décima parte de tudo o que recebesse | Gn 28,22 | OK | — |
| Na Lei, o dízimo "pertence ao Senhor" e "servia também" ao levita, estrangeiro, órfão e viúva | Lv 27,30; Dt 14,28-29 fala do dízimo **do terceiro ano** | AJUSTAR | "a décima parte do que a terra produz"; "A cada três anos, ela servia…" |
| A primeira comunidade partilhava; ninguém passava necessidade | At 4,34-35 (n. 32) | OK | — |
| Décima parte e partilha: formas da mesma atitude de fé | n. 25 | OK | Ligado ao significado interior (2Cor 9,7, literal conferida) |
| O valor é decisão da consciência | n. 10 | OK | — |

### Post 10 — "O que ensina a CNBB" (W43)

| Afirmação | Fonte | Veredito | Correção |
|---|---|---|---|
| Documento aprovado pelo Conselho Permanente | Apresentação (conferida) | OK | Nenhum outro documento da CNBB citado |
| Partilha regular; a comunidade assume o próprio sustento e o da Igreja | n. 6 | OK | — |
| Decisão pessoal, sinal da fé e da pertença | n. 9 | OK | — |
| O valor é decisão da consciência | n. 10 | OK | Acrescentado "A Igreja não fixa porcentagem" (n. 10) |
| Não se reduz a juntar dinheiro | n. 12 | OK | — |
| "O dízimo **é** gratidão, fé e conversão" | n. 29: **expressa** | AJUSTAR | "expressa" |
| Quatro dimensões | n. 29–32 | OK | Uma linha por dimensão; "sua paróquia partilha" (quem partilha é a comunidade, não o fiel isolado) |
| Finalidades: culto, clero, missão, caridade "com os pobres" (fonte n. 34) | n. 34–35 (bloco conferido): clero **e demais ministros**; "em favor dos pobres" | AJUSTAR | Fonte "n. 34-35" e redação do bloco |
| Agentes em equipe, nos conselhos (fonte n. 63) | n. 63–66 conferidos em bloco | AJUSTAR | Fonte "n. 63-66"; "conselhos pastoral e econômico"; formação necessária |

### Post 11 — "Dízimo e Eucaristia" (W43)

| Afirmação | Fonte | Veredito | Correção |
|---|---|---|---|
| Título "Dízimo e Eucaristia: sinais de doação"; capa "Sinais de gratidão e partilha" | Nenhuma das 4 fontes conferidas liga o dízimo à oferenda eucarística como "sinal"; "doação" é termo com cuidado | REMOVER | "Dízimo e oferta na Missa: qual a diferença?" |
| Com o pão e o vinho, os cristãos levam ofertas para os necessitados; a coleta continua atual | CIC 1351 | OK | Completado: "para a Eucaristia" e o exemplo de Cristo, que se fez pobre (CIC 1351) |
| — (faltava) | n. 6 e 10: o que é o dízimo | Novo | Slide "E o dízimo?", para a diferença ficar clara |
| Não confundir dízimo e ofertas quando recolhido na Missa | n. 51 | OK | — |
| "O que une os dois? O dízimo também serve ao culto" | Serve ao culto: n. 30 e 34–35. "O que une os dois" sugere ligação doutrinária sem fonte | AJUSTAR | Título "Também para o culto"; fonte n. 30 |
| Tudo vem de Deus; gratidão | n. 29 | OK | "expressa" |
| "Deus ama quem dá com alegria" | 2Cor 9,7 | OK | — |

**Linguagem (ADR-010):** as quatro legendas foram relidas em voz alta; frases encurtadas, "você" nas perguntas, termos técnicos explicados ("Igreja particular, isto é, a nossa Arquidiocese"; "culto, isto é, as celebrações"); nenhuma referência no meio da frase, fora a de 2Cor 9,7 logo após a citação literal.

**Resultado:** `pastoral.lint` OK nas duas semanas; `pastoral.render` = 8 (W42) + 19 (W43) imagens, nenhuma reprovada no QA; prévias refeitas em `site/semanas/2026-W42/` e `site/semanas/2026-W43/`; `pytest` 330 passando. Conferidos visualmente: post 8 slide 5, post 9 (capa), post 11 slide 4.

**Pendências:**
1. **Diogo:** confirmar a retirada de Malaquias do post 9 (recomendação desta auditoria: não usar Ml 3,10 em nenhum post, pelo n. 27).
2. Paráfrases bíblicas conferidas na Nova Vulgata; se o Diogo quiser aspas em algum versículo além de 2Cor 9,7, conferir antes na Tradução Oficial da CNBB.
3. Template `capa` em post de imagem única (post 9): a linha "fonte" não aparece e a seta "→" sugere carrossel. Questão de template, não de conteúdo.
4. `gerar.py` e briefing: o tema do post 9 veio com "Malaquias" no título e o do post 11 com "sinais de doação". Vale acrescentar ao prompt: não usar Ml 3,10 e não afirmar ligação doutrinária sem fonte conferida.
