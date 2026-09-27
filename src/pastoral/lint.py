"""Lint determinístico dos posts (arquitetura §1.1, rubrica §4.1; regras do cartao-marca.md).

Não usa LLM. Recebe o `posts.json` (já no formato do schema) e devolve uma lista de erros
legíveis; lista vazia = aprovado no automático (a revisão humana continua obrigatória).

Regras:
- termos proibidos do cartão (palavra inteira, sem diferenciar maiúsculas), inclusive em negação;
- nenhum "%" em nenhum texto;
- legenda ≤ 1.500 caracteres (com as hashtags) e com a assinatura institucional;
- ≤ 8 hashtags (hoje nenhuma: `hashtags_fixas: []`);
- slide ≤ 25 palavras visíveis; alt-text preenchido e ≤ 1.000 caracteres por slide;
- CTA da lista permitida do config.yaml;
- carrossel com 2 a 10 slides; imagem única com 1;
- citação bíblica com referência "Livro cap,vers" e edição registrada em `fontes`;
- Doc. CNBB 106 só com parágrafo conferido no exemplar (PARAGRAFOS_DOC106 ou Cap. II);
- CIC sempre com número (1–2865) e cânone do CDC sempre com número (1–1752);
- escopo das 4 fontes (Doc. 106, CIC, CDC, Bíblia): termos fora de escopo reprovam
  (ex.: "Mês Missionário", "voluntário", santo do dia).
Linguagem simples (ADR-010; `--legado` pula, só para posts publicados antes dele):
- na legenda, referência só na última linha "Fontes: Doc. CNBB 106, n. 6 e 9 · CIC 910 · 2Cor 9,7"
  (exceção: logo após citação literal entre aspas, no mesmo parágrafo); a linha é obrigatória se o post cita algo;
- frase da legenda com no máximo `linguagem.frase_max_palavras` palavras (citações literais não contam);
- termos formais de `linguagem.termos_formais` proibidos fora de aspas (slides, alt-text e legenda).

Uso: python -m pastoral.lint content/semanas/2026-W41/posts.json
     python -m pastoral.lint content/estreia/posts.json --legado
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]

# (rótulo exibido, padrão) — cartao-marca.md, seção "Termos"
TERMOS_PROIBIDOS = [
    ("taxa", r"\btaxas?\b"),
    ("mensalidade", r"\bmensalidades?\b"),
    ("cobrança", r"\bcobran[çc]as?\b"),
    ("imposto", r"\bimpostos?\b"),
    ("tributo", r"\btributos?\b"),
    ("prosperidade", r"\bprosperidade\b"),
    ("retorno", r"\bretornos?\b"),
    ("percentual fixo", r"\bpercentua(?:l|is)\s+fixos?\b"),
    ("dez por cento", r"\bdez\s+por\s+cento\b"),
    ("urgente", r"\burgentes?\b"),
    ("última chance", r"\búltima\s+chance\b"),
    ("culpa", r"\bculpa(?:s|do|da|dos|das)?\b"),
    ("pecado", r"\bpecados?\b"),
    ("contribua", r"\bcontribua(?:m)?\b"),
    ("doe", r"\bdoe(?:m)?\b"),
]

# Campos de slide que aparecem na arte (alt_text e template não contam)
CAMPOS_VISIVEIS = ("eyebrow", "titulo", "texto", "referencia", "fonte")

# "2Cor 9,7", "Rm 15,26-27", "At 2,42-47" (livro abreviado + capítulo,versículo[s])
RE_BIBLIA = re.compile(r"\b([1-3]?[A-Z][a-z]{0,3})\s?(\d{1,3}),(\d{1,3}(?:[-–]\d{1,3})?)")

# Doc. CNBB 106: parágrafos verificados em docs/pesquisa/06-cnbb-doc-106.md (cartão de marca)
# Conferidos no exemplar em 2026-09-27 (primeira e segunda leitura)
PARAGRAFOS_DOC106 = {4, 6, 7, 9, 10, 12, 22, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 51, 52, 63, 64, 65, 66}
RE_DOC106 = re.compile(
    r"Doc(?:\.|umento)?\s*(?:da\s+)?(?:CNBB\s*)?106(?:\s+da\s+CNBB)?\s*,?\s*"
    r"(?:(?:n\.|nn\.|n\.º|nº|números?)\s*(\d+)|((?:Cap\.|Capítulo)\s*(?:II|2)\b))?",
    re.IGNORECASE,
)

# Catecismo: "CIC 910", "CIC n. 2043", "CIC §1351"; o número é obrigatório (1–2865)
RE_CIC = re.compile(r"\bCIC\b\.?\s*(?:n\.\s*|§\s*)?(\d+)?")
CIC_MAX = 2865
# Direito Canônico: "cân. 222 §1", "cânon 222", "cânones 1260-1261"; número obrigatório (1–1752)
RE_CANONE = re.compile(r"\bc[âa]n(?:\.|on\b|ones\b)\s*(\d+)?", re.IGNORECASE)
CANONE_MAX = 1752

# Regra do Diogo (2026-09-27): só Doc. 106, CIC, CDC e Bíblia. Estes termos não têm âncora nessas fontes.
TERMOS_FORA_DE_ESCOPO = [
    ("Mês Missionário", r"\bm[êe]s\s+mission[áa]rio\b"),
    ("voluntário (use: serviço à comunidade, CIC 910)", r"\bvolunt[áa]ri(?:o|a|os|as|ado)\b"),
    ("Santa Teresinha", r"\bteresinha\b"),
    ("santo do dia", r"\bsant[oa]\s+do\s+dia\b"),
]


# ---------- linguagem simples (ADR-010) ----------

# Citação literal entre aspas, dentro de um mesmo parágrafo (não atravessa quebra de linha)
RE_ASPAS = re.compile(r"[\"“«][^\"“”«»\n]*[\"”»]")
# Citação literal seguida logo depois da referência entre parênteses: "Deus ama quem dá com alegria" (2Cor 9,7)
RE_CITACAO_COM_REF = re.compile(r"([\"“«][^\"“”«»\n]*[\"”»])[ \t]*\([^()\n]*\)")
# Itens aceitos na linha "Fontes:" (separados por " · ")
_NUMS = r"\d+(?:-\d+)?(?:(?:, | e )\d+(?:-\d+)?)*"
ITENS_FONTES = [
    ("doc106", re.compile(rf"Doc\. CNBB 106, n\. {_NUMS}")),
    ("cic", re.compile(r"CIC \d+(?:(?:, | e )\d+)*")),
    ("canone", re.compile(r"cân\. \d+(?: §\d+)?(?:(?:, | e )\d+(?: §\d+)?)*")),
    ("biblia", re.compile(r"[1-3]?[A-Z][a-z]{0,3} \d{1,3},\d{1,3}(?:-\d{1,3})?")),
]


def sem_aspas(texto: str) -> str:
    """Texto sem as citações literais entre aspas (elas ficam como no original)."""
    return RE_ASPAS.sub(" ", texto)


def separar_fontes(legenda: str) -> tuple[str, list[str], bool]:
    """(corpo da legenda, linhas "Fontes:", se a linha "Fontes:" é a última linha)."""
    linhas = legenda.rstrip().split("\n")
    fontes = [l.strip() for l in linhas if l.strip().startswith("Fontes:")]
    corpo = "\n".join(l for l in linhas if not l.strip().startswith("Fontes:"))
    ultima = bool(linhas) and linhas[-1].strip().startswith("Fontes:")
    return corpo, fontes, ultima


def referencias_no_texto(texto: str) -> list[str]:
    """Referências (Doc. 106, CIC, cân., Bíblia) encontradas no texto."""
    achadas = [m.group(0).strip(" ,") for m in RE_DOC106.finditer(texto)]
    achadas += [m.group(0).strip() for m in RE_CIC.finditer(texto)]
    achadas += [m.group(0).strip() for m in RE_CANONE.finditer(texto)]
    achadas += [m.group(0) for m in RE_BIBLIA.finditer(texto)]
    return achadas


def verificar_linha_fontes(linha: str) -> list[str]:
    """Formato consistente: "Fontes: Doc. CNBB 106, n. 6 e 9 · CIC 910 · 2Cor 9,7"."""
    conteudo = linha.removeprefix("Fontes:").strip()
    if not conteudo:
        return ['legenda: linha "Fontes:" vazia']
    erros = []
    for item in conteudo.split(" · "):
        tipo = next((t for t, rx in ITENS_FONTES if rx.fullmatch(item)), None)
        if tipo is None:
            erros.append(f'legenda: item "{item}" da linha "Fontes:" fora do formato '
                         '(ex.: Doc. CNBB 106, n. 6 e 9 · CIC 910 · cân. 222 §1 · 2Cor 9,7)')
            continue
        if tipo == "doc106":
            numeros = [int(n) for n in re.findall(r"\d+", item.split(",", 1)[1])]
            fora = [n for n in numeros if n not in PARAGRAFOS_DOC106]
            if fora:
                erros.append(f"legenda: Doc. 106, n. {', '.join(map(str, fora))} fora dos parágrafos verificados")
        elif tipo == "cic" and not all(1 <= int(n) <= CIC_MAX for n in re.findall(r"\d+", item)):
            erros.append(f"legenda: \"{item}\" fora do intervalo do CIC (1–{CIC_MAX})")
        elif tipo == "canone" and not all(1 <= int(n) <= CANONE_MAX
                                          for n in re.findall(r"(?:cân\. |, | e )(\d+)", item)):
            erros.append(f"legenda: \"{item}\" fora do intervalo do CDC (1–{CANONE_MAX})")
    return erros


def frases(texto: str) -> list[str]:
    """Frases do texto: quebra em ponto final, exclamação, interrogação e quebra de linha."""
    return [f.strip() for f in re.split(r"(?<=[.!?…])\s+|\n+", texto) if f.strip()]


def contar_palavras(texto: str) -> int:
    return sum(1 for t in texto.split() if re.search(r"\w", t))


def verificar_linguagem(post: dict, config: dict, textos: list[tuple[str, str]]) -> list[str]:
    """Regras de linguagem simples do ADR-010 (fontes no fim, frases curtas, sem termos formais)."""
    ling = config.get("linguagem", {})
    erros: list[str] = []
    legenda = post.get("legenda", "")
    corpo, linhas_fontes, fontes_no_fim = separar_fontes(legenda)

    # (a) referência só na linha "Fontes:" — ou logo após uma citação literal entre aspas
    livre = sem_aspas(RE_CITACAO_COM_REF.sub(r"\1", corpo))
    for ref in referencias_no_texto(livre):
        erros.append(f'legenda: referência "{ref}" no meio do texto; mova para a linha final "Fontes:"')

    # (b) linha "Fontes:" obrigatória se o post cita algo, sempre a última, no formato consistente
    cita = bool(post.get("fontes")) or any(s.get("fonte") or s.get("referencia") for s in post.get("slides", []))
    if linhas_fontes:
        if len(linhas_fontes) > 1:
            erros.append('legenda: mais de uma linha "Fontes:" (junte numa só)')
        if not fontes_no_fim:
            erros.append('legenda: a linha "Fontes:" deve ser a última linha da legenda')
        for linha in linhas_fontes:
            erros.extend(verificar_linha_fontes(linha))
    elif cita:
        erros.append('legenda sem a linha "Fontes:" no fim (o post cita fontes)')

    # (c) frases curtas na legenda (citações literais não contam)
    maximo = ling.get("frase_max_palavras")
    if maximo:
        for frase in frases(sem_aspas(corpo)):
            n = contar_palavras(frase)
            if n > maximo:
                erros.append(f"legenda: frase com {n} palavras (máx. {maximo}): \"{frase[:60]}…\"")

    # (d) termos formais fora de aspas (o texto de um slide de citação é literal)
    for termo in ling.get("termos_formais", []):
        padrao = rf"(?<!\w){re.escape(termo)}(?!\w)"
        for onde, texto in textos:
            if onde.endswith("(texto)") and _slide_citacao(post, onde):
                continue
            if re.search(padrao, sem_aspas(texto), re.IGNORECASE):
                erros.append(f"{onde}: termo formal \"{termo}\" (use palavras do dia a dia; "
                             "só vale dentro de citação literal entre aspas)")
    return erros


def _slide_citacao(post: dict, onde: str) -> bool:
    """O campo `onde` ("slide N (campo)") pertence a um slide de citação?"""
    m = re.match(r"slide (\d+) ", onde)
    slides = post.get("slides", [])
    return bool(m) and slides[int(m.group(1)) - 1].get("template") == "citacao"


def carregar_config(caminho: Path) -> dict:
    return yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))


# ---------- utilitários ----------

def palavras_do_slide(slide: dict) -> int:
    """Palavras visíveis no slide: tokens com pelo menos uma letra ou dígito."""
    texto = " ".join(str(slide.get(c, "")) for c in CAMPOS_VISIVEIS)
    return sum(1 for t in texto.split() if re.search(r"\w", t))


def referencias_biblicas(texto: str) -> list[str]:
    """Referências bíblicas encontradas, normalizadas como 'Livro cap,vers'."""
    return [f"{m.group(1)} {m.group(2)},{m.group(3).replace('–', '-')}" for m in RE_BIBLIA.finditer(texto)]


def referencia_valida(ref: str) -> bool:
    """Citação precisa de referência bíblica completa ou de documento numerado."""
    ref = ref.strip()
    if RE_BIBLIA.fullmatch(ref.removeprefix("cf. ")):
        return True
    return bool(re.match(r"(CIC \d+|cân\. \d+|Doc\. CNBB 106, (n\. \d+|Cap\. II))", ref))


def _textos(post: dict) -> list[tuple[str, str]]:
    """(onde, texto) de tudo que o público lê: slides visíveis, alt-text e legenda."""
    saida = []
    for i, slide in enumerate(post.get("slides", []), start=1):
        for campo in CAMPOS_VISIVEIS + ("alt_text",):
            if slide.get(campo):
                saida.append((f"slide {i} ({campo})", str(slide[campo])))
    saida.append(("legenda", post.get("legenda", "")))
    saida.extend(("hashtags", h) for h in post.get("hashtags", []))
    return saida


# ---------- regras ----------

def verificar_post(post: dict, config: dict, linguagem: bool = True) -> list[str]:
    """Lista de erros de um post (vazia = passou).

    `linguagem=False` é o modo legado: pula as regras do ADR-010 (só para posts já publicados antes dele).
    """
    lim = config["limites"]
    erros: list[str] = []
    textos = _textos(post)

    # termos proibidos e "%"
    for onde, texto in textos:
        for rotulo, padrao in TERMOS_PROIBIDOS:
            if re.search(padrao, texto, re.IGNORECASE):
                erros.append(f"{onde}: termo proibido \"{rotulo}\"")
        if lim.get("proibir_porcentagem") and "%" in texto:
            erros.append(f"{onde}: contém \"%\"")

    # legenda, assinatura e hashtags
    hashtags = set(post.get("hashtags", [])) | set(re.findall(r"#\w+", post.get("legenda", "")))
    legenda_final = post.get("legenda", "")
    if post.get("hashtags"):
        legenda_final += "\n\n" + " ".join(post["hashtags"])
    if len(legenda_final) > lim["legenda_max_caracteres"]:
        erros.append(f"legenda com {len(legenda_final)} caracteres (máx. {lim['legenda_max_caracteres']})")
    assinatura = f"{config['marca']['nome']} — {config['marca']['instituicao']}"
    if assinatura not in post.get("legenda", ""):
        erros.append(f"legenda sem a assinatura \"{assinatura}\"")
    if len(hashtags) > lim["hashtags_max"]:
        erros.append(f"{len(hashtags)} hashtags (máx. {lim['hashtags_max']})")

    # CTA
    permitidos = {c.casefold() for c in config["ctas_permitidos"]}
    if str(post.get("cta", "")).casefold() not in permitidos:
        erros.append(f"CTA \"{post.get('cta')}\" fora da lista permitida")

    # quantidade de slides
    slides = post.get("slides", [])
    if post.get("formato") == "carrossel" and not lim["slides_min"] <= len(slides) <= lim["slides_max"]:
        erros.append(f"carrossel com {len(slides)} slides (de {lim['slides_min']} a {lim['slides_max']})")
    if post.get("formato") == "imagem_unica" and len(slides) != 1:
        erros.append(f"imagem_unica com {len(slides)} slides (deve ter 1)")

    # cada slide: palavras, alt-text, referência de citação
    for i, slide in enumerate(slides, start=1):
        n = palavras_do_slide(slide)
        if n > lim["palavras_por_slide_max"]:
            erros.append(f"slide {i}: {n} palavras (máx. {lim['palavras_por_slide_max']} palavras)")
        alt = slide.get("alt_text", "").strip()
        if not alt or len(alt) > lim["alt_text_max_caracteres"]:
            erros.append(f"slide {i}: alt_text vazio ou com mais de {lim['alt_text_max_caracteres']} caracteres")
        if slide.get("template") == "citacao" and not referencia_valida(slide.get("referencia", "")):
            erros.append(f"slide {i}: citação sem referência válida (ex.: 2Cor 9,7)")

    # citações bíblicas: toda referência lida precisa estar em `fontes` com edição
    biblia = {f["referencia"].removeprefix("cf. "): f for f in post.get("fontes", []) if f.get("tipo") == "biblia"}
    for ref, fonte in biblia.items():
        if not RE_BIBLIA.fullmatch(ref):
            erros.append(f"fonte bíblica \"{ref}\" sem referência válida (Livro cap,vers)")
        if not fonte.get("edicao", "").strip():
            erros.append(f"fonte bíblica \"{ref}\" sem edição")
    citadas = {r for _, t in textos for r in referencias_biblicas(t)}
    for ref in sorted(citadas - set(biblia)):
        erros.append(f"referência bíblica {ref} sem fonte com edição em `fontes`")

    # Doc. CNBB 106
    for onde, texto in textos:
        for m in RE_DOC106.finditer(texto):
            paragrafo, capitulo = m.group(1), m.group(2)
            if capitulo:
                continue
            if paragrafo is None:
                erros.append(f"{onde}: Doc. 106 citado sem parágrafo verificado")
            elif int(paragrafo) not in PARAGRAFOS_DOC106:
                erros.append(f"{onde}: Doc. 106, n. {paragrafo} não está entre os parágrafos verificados")

    # CIC e CDC: sempre com número dentro do intervalo
    for onde, texto in textos:
        for m in RE_CIC.finditer(texto):
            if m.group(1) is None:
                erros.append(f"{onde}: CIC citado sem número de parágrafo")
            elif not 1 <= int(m.group(1)) <= CIC_MAX:
                erros.append(f"{onde}: CIC {m.group(1)} não existe (1–{CIC_MAX})")
        for m in RE_CANONE.finditer(texto):
            if m.group(1) is None:
                erros.append(f"{onde}: cân. citado sem número")
            elif not 1 <= int(m.group(1)) <= CANONE_MAX:
                erros.append(f"{onde}: cân. {m.group(1)} não existe (1–{CANONE_MAX})")

    # escopo das 4 fontes
    for onde, texto in textos:
        for rotulo, padrao in TERMOS_FORA_DE_ESCOPO:
            if re.search(padrao, texto, re.IGNORECASE):
                erros.append(f"{onde}: \"{rotulo}\" fora do escopo das 4 fontes")

    if linguagem:
        erros.extend(verificar_linguagem(post, config, textos))
    return erros


def verificar_lote(dados: dict, config: dict, linguagem: bool = True) -> list[str]:
    """Erros de todos os posts, prefixados com o número do post."""
    return [f"post {p.get('numero')}: {e}" for p in dados.get("posts", [])
            for e in verificar_post(p, config, linguagem)]


def validar_schema(dados: dict, caminho_schema: Path) -> list[str]:
    """Erros de forma segundo schemas/posts.schema.json."""
    from jsonschema import Draft202012Validator

    schema = json.loads(Path(caminho_schema).read_text(encoding="utf-8"))
    validador = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '(raiz)'}: {e.message}"
            for e in sorted(validador.iter_errors(dados), key=lambda e: list(map(str, e.absolute_path)))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint dos posts (schema + regras do cartão de marca)")
    ap.add_argument("posts", type=Path)
    ap.add_argument("--config", type=Path, default=RAIZ / "config.yaml")
    ap.add_argument("--schema", type=Path, default=RAIZ / "schemas" / "posts.schema.json")
    ap.add_argument("--legado", action="store_true",
                    help="sem as regras de linguagem do ADR-010 (só para posts publicados antes dele, ex.: estreia)")
    args = ap.parse_args(argv)

    dados = json.loads(args.posts.read_text(encoding="utf-8"))
    erros = validar_schema(dados, args.schema)
    if not erros:
        erros = verificar_lote(dados, carregar_config(args.config), linguagem=not args.legado)
    for e in erros:
        print(e)
    print("OK" if not erros else f"{len(erros)} erro(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
