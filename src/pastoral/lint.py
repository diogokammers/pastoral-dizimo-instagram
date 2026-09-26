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
- Doc. CNBB 106 só com parágrafo verificado (n. 6, 9, 10, 12, 22 ou Cap. II) e nunca junto das
  "quatro dimensões" (síntese pastoral, não citação do documento).

Uso: python -m pastoral.lint content/estreia/posts.json
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
PARAGRAFOS_DOC106 = {6, 9, 10, 12, 22}
RE_DOC106 = re.compile(
    r"Doc(?:\.|umento)?\s*(?:da\s+)?(?:CNBB\s*)?106(?:\s+da\s+CNBB)?\s*,?\s*"
    r"(?:(?:n\.|nn\.|n\.º|número)\s*(\d+)|(Cap\.\s*II\b))?",
    re.IGNORECASE,
)


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


def _unidades(post: dict) -> list[str]:
    """Blocos em que 'mesma frase' faz sentido: cada slide inteiro e cada linha da legenda."""
    blocos = [" ".join(str(s.get(c, "")) for c in CAMPOS_VISIVEIS) for s in post.get("slides", [])]
    blocos += [linha for linha in post.get("legenda", "").splitlines() if linha.strip()]
    return blocos


# ---------- regras ----------

def verificar_post(post: dict, config: dict) -> list[str]:
    """Lista de erros de um post (vazia = passou)."""
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
    for bloco in _unidades(post):
        if "106" in bloco and re.search(r"dimens", bloco, re.IGNORECASE):
            erros.append("\"dimensões\" no mesmo bloco que o Doc. 106 (a síntese não é do documento)")

    return erros


def verificar_lote(dados: dict, config: dict) -> list[str]:
    """Erros de todos os posts, prefixados com o número do post."""
    return [f"post {p.get('numero')}: {e}" for p in dados.get("posts", []) for e in verificar_post(p, config)]


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
    args = ap.parse_args(argv)

    dados = json.loads(args.posts.read_text(encoding="utf-8"))
    erros = validar_schema(dados, args.schema)
    if not erros:
        erros = verificar_lote(dados, carregar_config(args.config))
    for e in erros:
        print(e)
    print("OK" if not erros else f"{len(erros)} erro(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
