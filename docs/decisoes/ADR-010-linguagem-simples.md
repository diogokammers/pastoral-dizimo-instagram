# ADR-010 — Linguagem simples e fontes na linha final da legenda

Data: 2026-09-27. Status: aceito (pedido do Diogo).

## Contexto
As legendas estavam formais e cheias de "paradas" no meio da frase, como "(cf. Doc. CNBB 106, n. 6)". O público
são leigos: o texto precisa ser simples e acolhedor para que entendam o dízimo. A regra das 4 fontes continua:
simplificar muda a forma, nunca o conteúdo.

## Decisões
1. **Cartão de marca:** nova seção "Linguagem", a primeira e prioritária. Frases curtas (ideal até 20 palavras),
   palavras do dia a dia, "você", voz ativa, um assunto por parágrafo, perguntas e exemplos concretos; sem jargão
   (termo técnico necessário vem explicado); aspas só para citação literal, que fica como no original.
2. **Fontes na legenda:** nenhuma referência no meio da frase. Todas vão na última linha, depois da assinatura:
   `Fontes: Doc. CNBB 106, n. 6 e 9 · CIC 910 · cân. 222 §1 · 2Cor 9,7`. Única exceção: a referência logo após
   uma citação literal entre aspas, no mesmo parágrafo. Nos slides, a fonte continua na linha pequena "fonte".
3. **Lint** (`src/pastoral/lint.py`, `verificar_linguagem`): referência fora da linha "Fontes:" reprova (salvo a
   exceção); a linha é obrigatória quando o post cita algo, é a última e segue o formato (itens separados por
   " · ", parágrafos do Doc. 106 conferidos); frase da legenda com mais de `linguagem.frase_max_palavras` (30)
   palavras reprova, sem contar citações literais; `linguagem.termos_formais` do `config.yaml`
   ("corresponsavelmente", "outrossim", "destarte", "hodierno", "mister", "sustentação") reprova fora de aspas
   em slides, alt-text e legenda (o texto de slide de citação é literal e não conta). As regras de escopo seguem.
4. **Legado:** os posts 1–3 já publicados não mudam. `lint --legado` (e `linguagem=False`) pula as regras
   deste ADR só para eles. As legendas simples para colar estão em
   `docs/auditoria/2026-09-27-legendas-simples-estreia.md`, validadas por teste com o lint completo.
5. **Geração:** o prompt do `gerar.py` exige as mesmas regras.
6. **Reserva:** posts 4–7 (W40 e W41) reescritos, re-renderizados e com prévias refeitas.

## Consequências
- Legendas mais leves de ler; as fontes continuam visíveis e conferíveis numa linha só.
- Lint mais rígido: o LLM pode precisar de uma tentativa a mais para passar.
- Simplificações que tocam termos técnicos ficam registradas em `a_conferir` (ex.: "Ordinário do lugar" → "o
  bispo", post 5).
