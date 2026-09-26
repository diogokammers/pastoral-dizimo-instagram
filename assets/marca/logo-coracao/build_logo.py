# -*- coding: utf-8 -*-
"""Logotipo "coração partido em 4" — estudo para avaliação (não aprovado; ver ADR-002).

Origem: referência do Diogo (rodada 6, assets/marca/propostas/rodada6-referencia/UC-ref.svg,
build_logo18.py) e o ícone aprovado do destaque "Dízimo" (templates/icones/coracao-cheio.svg).

A geometria é gerada como peças reais (4 cantos + cruz central), sem máscara:
  - o coração é o mesmo contorno do ícone aprovado (grade 240);
  - 4 pontos em torno do centro (cantos internos da cruz) emitem 2 retas cada (8 linhas de corte);
  - cada canto é a cunha entre as duas retas, recuada meia largura de corte;
  - a cruz é o que sobra do coração depois de tirar as cunhas alargadas meia largura.

Parâmetros: corte (largura do corte), cruz (escala da cruz central), arred (raio das pontas; 0 = vivo),
angulos (abertura dos braços) e cores por peça (cruz, cantos superiores, cantos inferiores).

Saídas (nesta pasta): svg/, png/ (2048 px; 4096 no principal), lockups, avatares e prancha-logo.png.
Dependências extras (só deste estudo): shapely, fonttools, uharfbuzz, playwright, Pillow.
Uso: python assets/marca/logo-coracao/build_logo.py
"""
import base64
import io
import math
import pathlib
import tempfile

from shapely.geometry import Polygon
from shapely.ops import unary_union

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
FONTES = RAIZ / "assets" / "fonts"
SVG_DIR = AQUI / "svg"
PNG_DIR = AQUI / "png"

# Paleta aprovada (config.yaml / identidade-visual.md §3)
VERMELHO = "#A3121C"
PROFUNDO = "#7E0F17"
PRATA = "#F3F2EE"
CREME = "#F2E8D5"
GRAFITE = "#1E1B1B"
CINZA = "#5F5A57"
DOURADO = "#B08D3B"

# ---------------------------------------------------------------- geometria
# Contorno do coração do ícone aprovado (templates/icones/coracao-cheio.svg), grade 240.
CX = 120.0
FENDA = (120.0, 69.8)     # reentrância de cima
ESQ = (27.6, 96.6)        # fim do lobo esquerdo
C1 = (27.6, 137.3)        # controles da curva lateral
C2 = (75.6, 152.0)
PONTA = (120.0, 201.9)

# Cruz do ícone aprovado: cantos internos em (106.8|133.2, 105.4|137.8)
CRUZ_CENTRO_Y = 121.6
CRUZ_MEIA_L = 13.2        # meia largura (x)
CRUZ_MEIA_A = 16.2        # meia altura (y)

# Ângulos medidos no ícone aprovado (graus)
ANGULOS = dict(
    sup=21.0,          # borda do braço de cima, a partir da vertical
    inf=15.0,          # borda do braço de baixo, a partir da vertical
    lado_sobe=8.5,     # borda de cima dos braços laterais, acima da horizontal
    lado_desce=21.8,   # borda de baixo dos braços laterais, abaixo da horizontal
)


def _arco(p0, p1, n=180):
    """Semicírculo por cima entre p0 e p1 (o 'A' do SVG original tem raio menor que a corda,
    então o navegador o transforma num semicírculo com centro no ponto médio)."""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    r = math.dist(p0, p1) / 2
    a0 = math.atan2(p0[1] - my, p0[0] - mx)
    sinal = 1
    if my + r * math.sin(a0 + math.pi / 2) > my:   # queremos passar por cima (y menor)
        sinal = -1
    return [(mx + r * math.cos(a0 + sinal * math.pi * i / n),
             my + r * math.sin(a0 + sinal * math.pi * i / n)) for i in range(n + 1)]


def _bezier(p0, p1, p2, p3, n=180):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return pts


def coracao():
    """Polígono do coração (metade esquerda amostrada e espelhada)."""
    esquerda = _arco(FENDA, ESQ) + _bezier(ESQ, C1, C2, PONTA)[1:]
    direita = [(2 * CX - x, y) for x, y in reversed(esquerda)]
    return Polygon(esquerda + direita[1:-1]).buffer(0)


def geometria(corte=10.0, cruz=1.0, arred=0.0, angulos=None):
    """Devolve as peças: {'cruz': Polygon, 'sup': [esq, dir], 'inf': [esq, dir], 'coracao': Polygon}."""
    ang = {**ANGULOS, **(angulos or {})}
    H = coracao()
    a, b = CRUZ_MEIA_L * cruz, CRUZ_MEIA_A * cruz
    cy = CRUZ_CENTRO_Y
    L = 600.0
    s, i_, ls, ld = (math.radians(ang[k]) for k in ("sup", "inf", "lado_sobe", "lado_desce"))
    cunhas = {}
    for lado, sx in (("e", -1), ("d", 1)):
        p = (CX + sx * a, cy - b)   # canto superior
        cunhas["sup_" + lado] = Polygon([p, (p[0] + sx * L * math.sin(s), p[1] - L * math.cos(s)),
                                         (p[0] + sx * L * math.cos(ls), p[1] - L * math.sin(ls))])
        p = (CX + sx * a, cy + b)   # canto inferior
        cunhas["inf_" + lado] = Polygon([p, (p[0] + sx * L * math.sin(i_), p[1] + L * math.cos(i_)),
                                         (p[0] + sx * L * math.cos(ld), p[1] + L * math.sin(ld))])
    g = corte / 2
    pecas = {k: H.intersection(w.buffer(-g, join_style="mitre", mitre_limit=20)) for k, w in cunhas.items()}
    alargadas = unary_union([w.buffer(g, join_style="mitre", mitre_limit=20) for w in cunhas.values()])
    cruz_poly = H.difference(alargadas)
    if arred > 0:   # abertura morfológica: arredonda as pontas (cantos convexos) sem mudar o resto
        def arredonda(p):
            return p.buffer(-arred, join_style="round", quad_segs=24).buffer(arred, join_style="round", quad_segs=24)
        pecas = {k: arredonda(v) for k, v in pecas.items()}
        cruz_poly = arredonda(cruz_poly)
    return dict(cruz=cruz_poly, sup=[pecas["sup_e"], pecas["sup_d"]],
                inf=[pecas["inf_e"], pecas["inf_d"]], coracao=H)


def d_path(geom, tol=0.01):
    """Polígono(s) shapely → atributo d de <path> (retas, 2 casas; use fill-rule evenodd)."""
    geom = geom.simplify(tol, preserve_topology=True)
    polys = geom.geoms if hasattr(geom, "geoms") else [geom]
    partes = []
    for p in polys:
        if p.is_empty or p.area < 0.5:
            continue
        for anel in [p.exterior, *p.interiors]:
            pts = list(anel.coords)[:-1]
            partes.append("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "Z")
    return "".join(partes)


# ---------------------------------------------------------------- variações
# Cada variação: parâmetros da geometria + cores por peça + fundo de exibição.
V = {
    "L1-principal":        dict(desc="Como o ícone aprovado: vermelho, corte médio (10/240)",
                                geo=dict(), cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA),
    "L2-corte-fino":       dict(desc="Corte fino (6/240): mais massa, cortes somem cedo",
                                geo=dict(corte=6), cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA),
    "L3-corte-largo":      dict(desc="Corte largo (15/240): cortes resistem em 32 px",
                                geo=dict(corte=15), cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA),
    "L4-pontas-redondas":  dict(desc="Corte médio, pontas levemente arredondadas (r 2,5)",
                                geo=dict(arred=2.5), cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA),
    "L5-cruz-marcada":     dict(desc="Cruz central maior e pátea mais aberta, como na referência",
                                geo=dict(cruz=1.22, angulos=dict(sup=25, inf=18, lado_sobe=11, lado_desce=23)),
                                cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA),
    "L6-dois-tons":        dict(desc="Cantos de cima em vermelho profundo; cruz e cantos de baixo em vermelho",
                                geo=dict(), cores=dict(cruz=VERMELHO, sup=PROFUNDO, inf=VERMELHO), fundo=PRATA),
    "L7-negativo":         dict(desc="Negativo: prata sobre vermelho profundo",
                                geo=dict(), cores=dict(cruz=PRATA, sup=PRATA, inf=PRATA), fundo=PROFUNDO),
    "L8-grafite":          dict(desc="Monocromático grafite (documentos, carimbo, 1 cor)",
                                geo=dict(), cores=dict(cruz=GRAFITE, sup=GRAFITE, inf=GRAFITE), fundo=PRATA),
    "L9-filete-dourado":   dict(desc="L1 com filete dourado discreto em volta (uso grande, não avatar)",
                                geo=dict(), cores=dict(cruz=VERMELHO, sup=VERMELHO, inf=VERMELHO), fundo=PRATA,
                                filete=dict(cor=DOURADO, distancia=6.0, espessura=2.2)),
}

# Moldura comum (quadrada) em volta do coração + filete, para todas as variações terem o mesmo tamanho
_bx = coracao().buffer(6.0 + 2.2).bounds
_lado = max(_bx[2] - _bx[0], _bx[3] - _bx[1]) * 1.04
VB = ((_bx[0] + _bx[2]) / 2 - _lado / 2, (_bx[1] + _bx[3]) / 2 - _lado / 2, _lado, _lado)


def simbolo_paths(var):
    """<path> das peças de uma variação (coordenadas na grade 240)."""
    P = geometria(**var["geo"])
    c = var["cores"]
    out = []
    f = var.get("filete")
    if f:
        H = P["coracao"]
        anel = H.buffer(f["distancia"] + f["espessura"] / 2, quad_segs=32).difference(
            H.buffer(f["distancia"] - f["espessura"] / 2, quad_segs=32))
        out.append(f'<path fill="{f["cor"]}" fill-rule="evenodd" d="{d_path(anel)}"/>')
    out.append(f'<path fill="{c["cruz"]}" fill-rule="evenodd" d="{d_path(P["cruz"])}"/>')
    for k in ("sup", "inf"):
        d = "".join(d_path(p) for p in P[k])
        out.append(f'<path fill="{c[k]}" fill-rule="evenodd" d="{d}"/>')
    return "".join(out)


def simbolo_svg(var, tamanho=None, fundo=None):
    vb = " ".join(f"{v:.2f}" for v in VB)
    wh = f' width="{tamanho}" height="{tamanho}"' if tamanho else ""
    bg = f'<rect x="{VB[0]:.2f}" y="{VB[1]:.2f}" width="{VB[2]:.2f}" height="{VB[3]:.2f}" fill="{fundo}"/>' if fundo else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"{wh}>{bg}{simbolo_paths(var)}</svg>'


# ---------------------------------------------------------------- texto em curvas
class Fonte:
    """Fonte variável instanciada num peso; texto → path (shaping com HarfBuzz, com kerning)."""

    def __init__(self, arquivo, peso):
        import uharfbuzz as hb
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        self.hb = hb
        self.tt = instantiateVariableFont(TTFont(str(arquivo)), {"wght": peso})
        self.upem = self.tt["head"].unitsPerEm
        self.cap = self.tt["OS/2"].sCapHeight
        self.gs = self.tt.getGlyphSet()
        self.ordem = self.tt.getGlyphOrder()
        self.hbf = hb.Font(hb.Face(hb.Blob.from_file_path(str(arquivo))))
        self.hbf.set_variations({"wght": peso})

    def largura(self, texto, tam, track=0.0):
        return self.texto(texto, tam, 0, 0, track)[1]

    def texto(self, texto, tam, x, y, track=0.0):
        """Devolve (d, largura, caixa) com a linha de base em y e início em x; track em em."""
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.transformPen import TransformPen
        buf = self.hb.Buffer()
        buf.add_str(texto)
        buf.guess_segment_properties()
        self.hb.shape(self.hbf, buf, {"kern": True, "liga": True})
        k = tam / self.upem
        cur = 0.0
        pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.2f}")
        bp = BoundsPen(self.gs)
        n = len(buf.glyph_infos)
        for j, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
            nome = self.ordem[info.codepoint]
            t = (k, 0, 0, -k, x + (cur + pos.x_offset) * k, y - pos.y_offset * k)
            self.gs[nome].draw(TransformPen(pen, t))
            self.gs[nome].draw(TransformPen(bp, t))
            cur += pos.x_advance + (track * self.upem if j < n - 1 else 0)
        return pen.getCommands(), cur * k, bp.bounds


NOME = "Pastoral do Dízimo"
SUB = "ARQUIDIOCESE DE FLORIANÓPOLIS"


def _fontes():
    return (Fonte(FONTES / "cormorant-garamond" / "CormorantGaramond-wght.ttf", 600),
            Fonte(FONTES / "source-sans-3" / "SourceSans3-wght.ttf", 600))


def _simbolo_em(var, x, y, altura):
    """Grupo do símbolo com o topo do coração em (x, y) e a altura do coração dada."""
    b = coracao().bounds
    s = altura / (b[3] - b[1])
    return (f'<g transform="translate({x - b[0] * s:.2f} {y - b[1] * s:.2f}) scale({s:.5f})">'
            f'{simbolo_paths(var)}</g>'), (b[2] - b[0]) * s


def _track_para(fonte, texto, tam, alvo, lo=0.08, hi=0.34):
    """Espaçamento (em) para o texto em caixa alta ocupar a largura alvo."""
    w0 = fonte.largura(texto, tam)
    t = (alvo - w0) / ((len(texto) - 1) * tam)
    return max(lo, min(hi, t))


def lockup_horizontal(var):
    fn, fs = _fontes()
    M = 40
    alt = 200                                   # altura do coração
    g, larg_s = _simbolo_em(var, M, M, alt)
    N, T = 96, 26
    capN, capT = fn.cap * N / fn.upem, fs.cap * T / fs.upem
    entre = 30                                  # da base do nome ao topo da linha de apoio
    bloco = capN + entre + capT
    centro = M + alt * 0.50                     # centro da altura do coração
    base1 = centro - bloco / 2 + capN
    base2 = base1 + entre + capT
    tx = M + larg_s + alt * 0.22
    d1, w1, _ = fn.texto(NOME, N, tx, base1, track=-0.01)
    tr = _track_para(fs, SUB, T, w1)
    d2, w2, _ = fs.texto(SUB, T, tx + 2, base2, track=tr)
    W = tx + max(w1, w2 + 2) + M
    Hh = alt + 2 * M
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {Hh:.1f}">{g}'
            f'<path fill="{GRAFITE}" d="{d1}"/><path fill="{CINZA}" d="{d2}"/></svg>'), W, Hh


def lockup_vertical(var):
    fn, fs = _fontes()
    M = 40
    alt = 240
    N, T = 80, 21
    capN, capT = fn.cap * N / fn.upem, fs.cap * T / fs.upem
    w1 = fn.largura(NOME, N, track=-0.01)
    tr = _track_para(fs, SUB, T, w1)
    w2 = fs.largura(SUB, T, track=tr)
    b = coracao().bounds
    larg_s = (b[2] - b[0]) * alt / (b[3] - b[1])
    W = max(w1, w2, larg_s) + 2 * M
    g, _ = _simbolo_em(var, (W - larg_s) / 2, M, alt)
    base1 = M + alt + 44 + capN
    base2 = base1 + 26 + capT
    d1, _, _ = fn.texto(NOME, N, (W - w1) / 2, base1, track=-0.01)
    d2, _, _ = fs.texto(SUB, T, (W - w2) / 2, base2, track=tr)
    Hh = base2 + M
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {Hh:.1f}">{g}'
            f'<path fill="{GRAFITE}" d="{d1}"/><path fill="{CINZA}" d="{d2}"/></svg>'), W, Hh


def avatar(var, fundo):
    """Avatar circular 1080: coração com ~60% do diâmetro, centrado opticamente."""
    H = coracao()
    b = H.bounds
    larg = 1080 * 0.60
    s = larg / (b[2] - b[0])
    cy_caixa = (b[1] + b[3]) / 2
    cy_optico = (cy_caixa + H.centroid.y) / 2   # entre o centro da caixa e o centro de massa
    tx = 540 - (b[0] + b[2]) / 2 * s
    ty = 540 - cy_optico * s
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080">'
            f'<circle cx="540" cy="540" r="540" fill="{fundo}"/>'
            f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.5f})">{simbolo_paths(var)}</g></svg>')


# ---------------------------------------------------------------- render (Playwright)
class Render:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        return self

    def __exit__(self, *a):
        self.browser.close()
        self._pw.stop()

    def svg_png(self, svg, largura, altura, destino):
        """Renderiza o SVG em largura×altura px com fundo transparente."""
        pg = self.browser.new_page(viewport={"width": int(largura), "height": int(altura)}, device_scale_factor=1)
        svg = svg.replace("<svg ", f'<svg width="{int(largura)}" height="{int(altura)}" preserveAspectRatio="xMidYMid meet" ', 1)
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.screenshot(path=str(destino), omit_background=True, clip=dict(x=0, y=0, width=int(largura), height=int(altura)))
        pg.close()

    def pagina_png(self, html, largura, destino):
        tmp = pathlib.Path(tempfile.mkdtemp()) / "prancha.html"
        tmp.write_text(html, encoding="utf-8")
        pg = self.browser.new_page(viewport={"width": largura, "height": 1000}, device_scale_factor=1)
        pg.goto(tmp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(destino), full_page=True)
        pg.close()


def _reduz(png, px):
    """PNG → data URI reduzido com Lanczos (simula o Instagram reduzindo o arquivo)."""
    from PIL import Image
    im = Image.open(png).convert("RGBA").resize((px, px), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def _uri(png, largura=None):
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    if largura:
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), im.width, im.height


# ---------------------------------------------------------------- prancha
def prancha(r):
    fonte_uri = lambda p: pathlib.Path(p).as_uri()
    css = f"""
    @font-face{{font-family:'Cormorant';src:url('{fonte_uri(FONTES/'cormorant-garamond'/'CormorantGaramond-wght.ttf')}');font-weight:300 700}}
    @font-face{{font-family:'SS3';src:url('{fonte_uri(FONTES/'source-sans-3'/'SourceSans3-wght.ttf')}');font-weight:200 900}}
    *{{box-sizing:border-box;margin:0}}
    body{{width:2400px;background:#FBFAF7;color:{GRAFITE};font-family:'SS3';padding:72px 80px 96px}}
    h1{{font-family:'Cormorant';font-weight:600;font-size:72px;color:{VERMELHO};letter-spacing:-.01em}}
    .sub{{font-size:24px;color:{CINZA};margin-top:8px}}
    h2{{font-family:'Cormorant';font-weight:600;font-size:48px;margin:72px 0 8px;color:{GRAFITE}}}
    h2 small{{font-family:'SS3';font-size:22px;font-weight:400;color:{CINZA};margin-left:16px}}
    .rule{{height:2px;background:{DOURADO};width:120px;margin:0 0 28px}}
    .grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:24px}}
    .card{{background:#fff;border:1px solid #E6E2DA;border-radius:14px;overflow:hidden}}
    .card .arte{{height:380px;display:flex;align-items:center;justify-content:center}}
    .card .rot{{padding:16px 20px 20px}}
    .rot b{{font-size:24px;font-weight:600;display:block}}
    .rot span{{font-size:18px;color:{CINZA};line-height:1.3;display:block;margin-top:4px}}
    .red{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
    .linha{{background:#fff;border:1px solid #E6E2DA;border-radius:14px;padding:20px 20px;display:flex;gap:20px;align-items:flex-end;min-width:0}}
    .linha .nome{{width:120px;flex:none;align-self:center;font-size:22px;font-weight:600}}
    .linha figure{{display:flex;flex-direction:column;align-items:center;gap:8px}}
    .linha figcaption{{font-size:16px;color:{CINZA}}}
    .caixa{{display:flex;align-items:center;justify-content:center;border-radius:8px}}
    .pix{{image-rendering:pixelated}}
    table.fundos{{border-collapse:separate;border-spacing:8px 8px}}
    table.fundos th{{font-size:20px;font-weight:600;text-align:left;padding-right:12px;white-space:nowrap}}
    table.fundos td{{width:196px;height:200px;border-radius:10px;text-align:center;vertical-align:middle}}
    .lk{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
    .lk>div{{border-radius:14px;display:flex;align-items:center;justify-content:center;padding:56px;border:1px solid #E6E2DA}}
    .av{{display:flex;gap:48px;align-items:center;flex-wrap:wrap}}
    .av figure{{display:flex;flex-direction:column;align-items:center;gap:10px}}
    .av figcaption{{font-size:18px;color:{CINZA}}}
    .nota{{font-size:20px;color:{CINZA};margin-top:14px;max-width:1900px;line-height:1.4}}
    """
    h = [f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>",
         "<h1>Coração partido em 4 — estudo de logotipo</h1>",
         "<div class='sub'>Pastoral do Dízimo · Arquidiocese de Florianópolis · a partir da referência do Diogo (rodada 6) "
         "e do ícone aprovado do destaque “Dízimo” · 26/09/2026 · proposta, não aprovada (ADR-002)</div>"]
    # 1. variações
    h.append("<h2>Variações<small>peças reais (4 cantos + cruz), sem máscara</small></h2><div class='rule'></div><div class='grid'>")
    for k, v in V.items():
        h.append(f"<div class='card'><div class='arte' style='background:{v['fundo']}'>{simbolo_svg(v, 320)}</div>"
                 f"<div class='rot'><b>{k.replace('-', ' ', 1)}</b><span>{v['desc']}</span></div></div>")
    # célula 10: parâmetros
    h.append("<div class='card'><div class='rot' style='padding:28px'><b>Parâmetros</b><span>corte (largura, grade 240) · "
             "cruz (escala dos 4 pontos) · arred (raio das pontas, 0 = vivo) · ângulos dos braços · cor por peça."
             "<br><br>L1 = ícone aprovado: corte 10, cruz 1,0, ângulos 21° / 15° / 8,5° / 21,8°.</span></div></div>")
    h.append("</div>")
    # 2. redução
    h.append("<h2>Teste de redução<small>PNG 2048 reduzido com Lanczos para 512, 110 (avatar do Instagram) e 32 px; "
             "o 32 ampliado 4× mostra os pixels</small></h2><div class='rule'></div><div class='red'>")
    for k, v in V.items():
        png = PNG_DIR / f"{k}-2048.png"
        fig = []
        for px in (512, 110, 32):
            box = px + (24 if px > 32 else 16)
            fig.append(f"<figure><div class='caixa' style='background:{v['fundo']};width:{box}px;height:{box}px'>"
                       f"<img src='{_reduz(png, px)}' width='{px}' height='{px}'></div><figcaption>{px} px</figcaption></figure>")
        fig.append(f"<figure><div class='caixa' style='background:{v['fundo']};width:152px;height:152px'>"
                   f"<img class='pix' src='{_reduz(png, 32)}' width='128' height='128'></div><figcaption>32 px ×4</figcaption></figure>")
        h.append(f"<div class='linha'><div class='nome'>{k.split('-')[0]}<br><span style='font-weight:400;color:{CINZA};font-size:18px'>"
                 f"{k.split('-', 1)[1].replace('-', ' ')}</span></div>{''.join(fig)}</div>")
    h.append("</div>")
    # 3. fundos
    fundos = [("prata", PRATA), ("creme", CREME), ("branco", "#FFFFFF"), ("grafite", GRAFITE), ("vermelho profundo", PROFUNDO)]
    h.append("<h2>Fundos<small>símbolo a 160 px e 48 px sobre os fundos da paleta</small></h2><div class='rule'></div>"
             "<table class='fundos'><tr><th></th>" + "".join(f"<th style='text-align:center'>{k.split('-')[0]}</th>" for k in V) + "</tr>")
    for nome, cor in fundos:
        h.append(f"<tr><th>{nome}</th>")
        for k, v in V.items():
            h.append(f"<td style='background:{cor};border:1px solid #E6E2DA'>{simbolo_svg(v, 160)}"
                     f"<div style='height:4px'></div>{simbolo_svg(v, 48)}</td>")
        h.append("</tr>")
    h.append("</table><div class='nota'>Leitura: vermelho (L1–L6, L9) funciona sobre prata, creme e branco; sobre vermelho profundo "
             "usa-se o L7 (prata); sobre grafite, L7 ou vermelho. O grafite (L8) é para 1 cor em fundo claro.</div>")
    # 4. lockups
    h.append("<h2>Lockups com L1<small>texto convertido em curvas (Cormorant Garamond 600 · Source Sans 3 600, caixa alta espaçada)</small></h2>"
             "<div class='rule'></div><div class='lk'>")
    uh, wh, hh = _uri(AQUI / "png" / "lockup-horizontal-2048.png", 1000)
    uv, wv, hv = _uri(AQUI / "png" / "lockup-vertical-2048.png", 560)
    for cor in (PRATA, CREME):
        h.append(f"<div style='background:{cor}'><img src='{uh}' width='{wh}' height='{hh}'></div>")
    for cor in (PRATA, CREME):
        h.append(f"<div style='background:{cor}'><img src='{uv}' width='{wv}' height='{hv}'></div>")
    h.append("</div>")
    # 5. avatares
    h.append("<h2>Avatar circular (1080)<small>como o Instagram mostra: 360, 110 e 56 px</small></h2><div class='rule'></div><div class='av'>")
    for nome in ("prata", "creme"):
        png = PNG_DIR / f"avatar-{nome}-1080.png"
        for px in (360, 110, 56):
            u, w, hh2 = _uri(png, px)
            h.append(f"<figure><img src='{u}' width='{w}' height='{hh2}' style='border-radius:50%;box-shadow:0 0 0 1px #E0DBD2'>"
                     f"<figcaption>{nome} · {px} px</figcaption></figure>")
    h.append("</div><div class='nota'>Risco de originalidade: o “coração de quatro partes” também é usado por outras dioceses "
             "(identidade-visual.md §1). Ver LEIA-ME.md.</div></body></html>")
    r.pagina_png("".join(h), 2400, AQUI / "prancha-logo.png")


# ---------------------------------------------------------------- principal
def main():
    SVG_DIR.mkdir(exist_ok=True)
    PNG_DIR.mkdir(exist_ok=True)
    with Render() as r:
        for k, v in V.items():
            svg = simbolo_svg(v)
            (SVG_DIR / f"{k}.svg").write_text(svg, encoding="utf-8")
            r.svg_png(svg, 2048, 2048, PNG_DIR / f"{k}-2048.png")
            if k == "L1-principal":
                r.svg_png(svg, 4096, 4096, PNG_DIR / f"{k}-4096.png")
            if k == "L7-negativo":   # também com o fundo, para não parecer "vazio" ao abrir
                svgf = simbolo_svg(v, fundo=PROFUNDO)
                (SVG_DIR / f"{k}-com-fundo.svg").write_text(svgf, encoding="utf-8")
                r.svg_png(svgf, 2048, 2048, PNG_DIR / f"{k}-com-fundo-2048.png")
        L1 = V["L1-principal"]
        for nome, (svg, W, Hh) in (("lockup-horizontal", lockup_horizontal(L1)), ("lockup-vertical", lockup_vertical(L1))):
            (SVG_DIR / f"{nome}.svg").write_text(svg, encoding="utf-8")
            r.svg_png(svg, 2048, round(2048 * Hh / W), PNG_DIR / f"{nome}-2048.png")
        for nome, cor in (("prata", PRATA), ("creme", CREME)):
            svg = avatar(L1, cor)
            (SVG_DIR / f"avatar-{nome}.svg").write_text(svg, encoding="utf-8")
            r.svg_png(svg, 1080, 1080, PNG_DIR / f"avatar-{nome}-1080.png")
        prancha(r)
    print("ok:", AQUI)


if __name__ == "__main__":
    main()
