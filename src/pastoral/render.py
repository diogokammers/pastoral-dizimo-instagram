"""Render das artes: templates HTML/CSS → Playwright (Chromium) → JPEG sRGB + QA (arquitetura §1.1, §4.2).

- Posts: 1080×1350 (4:5); capas de destaques: 1080×1920.
- Tokens de cor vêm do config.yaml; fontes .ttf locais (assets/fonts); espera `document.fonts.ready`.
- Tema de fundo (ADR-007): post `fixado` ou `importante` → "vermelho" (capa/CTA vermelho profundo,
  conteúdo/citação prata); qualquer outro post → "creme" (todos os slides em fundo creme).
- `marca.simbolo: null` (ADR-002) → assinatura tipográfica, nenhum símbolo.
- JPEG: screenshot PNG sem perdas → Pillow → JPEG qualidade 90, 4:4:4, perfil sRGB embutido.
- QA por imagem: overflow das caixas, contraste AA (≥ 4,5:1) de todo texto, área segura
  (72 px laterais; texto essencial fora dos 180 px inferiores), dimensões exatas e < 8 MB.

Uso: python -m pastoral.render content/estreia/posts.json --saida content/estreia/render --destaques
"""
from __future__ import annotations

import argparse
import html
import io
import json
import sys
import tempfile
from pathlib import Path
from string import Template

import yaml

RAIZ = Path(__file__).resolve().parents[2]
TEMPLATES = RAIZ / "templates"
LIMITE_BYTES = 8 * 1024 * 1024
CONTRASTE_MIN = 4.5

# Destaques da estratégia (cap. 8) e ícone de linha de cada um (templates/icones/*.svg).
# ADR-007: "Paróquias" removido; ficam 5.
DESTAQUES = [
    {"nome": "Dízimo", "arquivo": "dizimo", "icone": "maos"},
    {"nome": "Formação", "arquivo": "formacao", "icone": "livro"},
    {"nome": "Agenda", "arquivo": "agenda", "icone": "calendario"},
    {"nome": "Perguntas", "arquivo": "perguntas", "icone": "pergunta"},
    {"nome": "Arquifln", "arquivo": "arquifln", "icone": "cruz"},
]


# ---------- montagem do HTML (puro, testável sem navegador) ----------

def tokens_css(config: dict) -> str:
    """:root com as cores do config (vermelho_profundo → --vermelho-profundo)."""
    linhas = [f"  --{nome.replace('_', '-')}: {cor};" for nome, cor in config["marca"]["paleta"].items()]
    return ":root {\n" + "\n".join(linhas) + "\n}"


def _preencher(nome_template: str, campos: dict, config: dict) -> str:
    modelo = Template((TEMPLATES / f"{nome_template}.html").read_text(encoding="utf-8"))
    marca = config["marca"]
    base = {
        "base": TEMPLATES.as_uri() + "/",
        "tokens": tokens_css(config),
        "marca_nome": html.escape(marca["nome"]),
        "instituicao": html.escape(marca["instituicao"]),
        "usuario": html.escape(marca["usuario"]),
    }
    return modelo.substitute({**base, **campos})


# ---------- tema de fundo (ADR-007) ----------

def tema_do_post(post: dict) -> str:
    """"vermelho" para post fixado ou importante; "creme" para os posts comuns da semana."""
    return "vermelho" if post.get("fixado") or post.get("importante") else "creme"


def classe_fundo(template: str, tema: str) -> str:
    """Classe CSS do fundo do slide: `escuro` (vermelho profundo), `claro` (prata) ou `creme`."""
    if tema == "creme":
        return "creme"
    return "escuro" if template in ("capa", "cta") else "claro"


def montar_html(slide: dict, config: dict, indice: int, total: int, tema: str = "vermelho") -> str:
    """HTML de um slide de post a partir do template indicado em `slide['template']`."""
    campos = {c: html.escape(str(slide.get(c, ""))) for c in ("eyebrow", "titulo", "texto", "referencia", "fonte")}
    campos["numero"] = f"{indice}/{total}"
    campos["fundo"] = classe_fundo(slide["template"], tema)
    return _preencher(slide["template"], campos, config)


def montar_html_destaque(icone: str, config: dict) -> str:
    svg = (TEMPLATES / "icones" / f"{icone}.svg").read_text(encoding="utf-8")
    return _preencher("destaque", {"icone": svg}, config)


# ---------- contraste (WCAG 2.x) ----------

def _luminancia(hex_cor: str) -> float:
    r, g, b = (int(hex_cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(cor1: str, cor2: str) -> float:
    l1, l2 = sorted((_luminancia(cor1), _luminancia(cor2)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


JS_FONTES = """
async () => {
  await Promise.all(['600 64px "Cormorant Garamond"', 'italic 500 72px "Cormorant Garamond"',
                     '400 42px "Source Sans 3"', '600 28px "Source Sans 3"'].map(f => document.fonts.load(f)));
  await document.fonts.ready;
  return true;
}
"""

# QA executado dentro da página. Devolve overflow, contraste e área segura de cada texto.
JS_QA = r"""
({margem, rodapeLivre, minimo}) => {
  const W = window.innerWidth, H = window.innerHeight;
  const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => {
    const f = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const razao = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const fundo = el => {
    for (let e = el; e; e = e.parentElement) {
      const c = rgb(getComputedStyle(e).backgroundColor);
      if (c.length >= 3 && (c.length < 4 || c[3] > 0)) return c.slice(0, 3);
    }
    return [255, 255, 255];
  };
  const resumo = el => (el.textContent || '').trim().slice(0, 50);
  const saida = {overflow: [], contraste: [], area_segura: []};

  document.querySelectorAll('[data-caixa]').forEach(el => {
    if (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)
      saida.overflow.push({texto: resumo(el), scrollHeight: el.scrollHeight, clientHeight: el.clientHeight});
  });

  const comTexto = [...document.body.querySelectorAll('*')].filter(el =>
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  for (const el of comTexto) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = razao(rgb(cs.color), fundo(el));
    if (r < minimo) saida.contraste.push({texto: resumo(el), razao: Math.round(r * 100) / 100, cor: cs.color});
    const faixa = document.createRange(); faixa.selectNodeContents(el);
    const caixa = faixa.getBoundingClientRect();
    if (!caixa.width) continue;
    const essencial = !el.closest('[data-rodape]');
    const problemas = [];
    if (caixa.left < margem - 0.5 || caixa.right > W - margem + 0.5) problemas.push('lateral');
    if (caixa.top < 0 || caixa.bottom > H) problemas.push('fora da arte');
    else if (essencial && caixa.bottom > H - rodapeLivre + 0.5) problemas.push('faixa inferior');
    if (problemas.length) saida.area_segura.push({texto: resumo(el), problemas,
      caixa: [caixa.left, caixa.top, caixa.right, caixa.bottom].map(Math.round)});
  }
  saida.fontes_ok = document.fonts.check('600 64px "Cormorant Garamond"') &&
                    document.fonts.check('400 42px "Source Sans 3"');
  return saida;
}
"""


def _jpeg_srgb(png: bytes) -> bytes:
    """PNG da tela → JPEG q90, sem subamostragem de cor, com perfil sRGB embutido."""
    from PIL import Image, ImageCms

    img = Image.open(io.BytesIO(png)).convert("RGB")
    perfil = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90, subsampling=0, optimize=True, icc_profile=perfil)
    return buf.getvalue()


class Renderizador:
    """Um Chromium aberto para várias artes. Uso: `with Renderizador() as r: r.renderizar_html(...)`."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        try:
            self._navegador = self._pw.chromium.launch()
        except Exception:
            self._pw.stop()
            raise
        self._tmp = tempfile.TemporaryDirectory()
        return self

    def __exit__(self, *exc):
        self._navegador.close()
        self._pw.stop()
        self._tmp.cleanup()

    def renderizar_html(self, html_pagina: str, destino: Path, largura: int, altura: int,
                        esperado: tuple[int, int] | None = None, margem: int = 72, rodape_livre: int = 180) -> dict:
        """Renderiza um HTML em JPEG e devolve o resultado do QA."""
        from PIL import Image

        arquivo = Path(self._tmp.name) / "pagina.html"
        arquivo.write_text(html_pagina, encoding="utf-8")
        pagina = self._navegador.new_page(viewport={"width": largura, "height": altura}, device_scale_factor=1)
        try:
            pagina.goto(arquivo.as_uri(), wait_until="load")
            # carrega as fontes explicitamente (a capa de destaque não tem texto) e espera todas
            pagina.evaluate(JS_FONTES)
            qa = pagina.evaluate(JS_QA, {"margem": margem, "rodapeLivre": rodape_livre, "minimo": CONTRASTE_MIN})
            png = pagina.screenshot(type="png", full_page=False)
        finally:
            pagina.close()

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(_jpeg_srgb(png))
        with Image.open(destino) as img:
            dimensoes = list(img.size)
        esperado = list(esperado or (largura, altura))
        qa.update(arquivo=destino.name, dimensoes=dimensoes, bytes=destino.stat().st_size)
        qa["ok"] = (not qa["overflow"] and not qa["contraste"] and not qa["area_segura"] and qa["fontes_ok"]
                    and dimensoes == esperado and qa["bytes"] < LIMITE_BYTES)
        return qa

    def renderizar_post(self, post: dict, pasta: Path, config: dict, prefixo: str | None = None) -> list[dict]:
        """post-{n}-01.jpg, post-{n}-02.jpg, ... (ou {prefixo}-01.jpg ...) com o QA de cada slide."""
        arte = config["marca"]["arte"]
        total = len(post["slides"])
        tema = tema_do_post(post)
        prefixo = prefixo or f"post-{post['numero']}"
        resultados = []
        for i, slide in enumerate(post["slides"], start=1):
            qa = self.renderizar_html(montar_html(slide, config, i, total, tema),
                                      Path(pasta) / f"{prefixo}-{i:02d}.jpg",
                                      arte["largura"], arte["altura"],
                                      margem=arte["margem_segura_px"], rodape_livre=arte["rodape_livre_px"])
            resultados.append({"post": post["numero"], "slide": i, "template": slide["template"], "tema": tema, **qa})
        return resultados

    def renderizar_destaques(self, pasta: Path, config: dict) -> list[dict]:
        """destaque-<nome>.jpg (1080×1920) para os 5 destaques."""
        resultados = []
        for d in DESTAQUES:
            qa = self.renderizar_html(montar_html_destaque(d["icone"], config),
                                      Path(pasta) / f"destaque-{d['arquivo']}.jpg", 1080, 1920)
            resultados.append({"destaque": d["nome"], **qa})
        return resultados


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Renderiza posts (e capas de destaques) com QA")
    ap.add_argument("posts", type=Path)
    ap.add_argument("--saida", type=Path, help="padrão: render/ ao lado do posts.json")
    ap.add_argument("--destaques", action="store_true", help="também gera as 5 capas de destaques")
    args = ap.parse_args(argv)

    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    dados = json.loads(args.posts.read_text(encoding="utf-8"))
    saida = args.saida or args.posts.with_name("render")
    relatorio = {"posts": [], "destaques": []}
    with Renderizador() as r:
        for post in dados["posts"]:
            relatorio["posts"] += r.renderizar_post(post, saida, config)
        if args.destaques:
            relatorio["destaques"] = r.renderizar_destaques(saida, config)
    todos = relatorio["posts"] + relatorio["destaques"]
    relatorio["resumo"] = {"imagens": len(todos), "reprovadas": [q["arquivo"] for q in todos if not q["ok"]]}
    (saida / "qa.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(todos)} imagens em {saida}; reprovadas: {relatorio['resumo']['reprovadas'] or 'nenhuma'}")
    return 1 if relatorio["resumo"]["reprovadas"] else 0


if __name__ == "__main__":
    sys.exit(main())
