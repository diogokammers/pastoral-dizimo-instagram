# -*- coding: utf-8 -*-
"""v5 — coração dividido em quatro sem figuras. Variações de divisão eclesial."""
import io, pathlib
from build_logo3 import heart, RED, DEEP, PRATA, GRAFITE, GOLD
OUT = pathlib.Path(__file__).parent

def frame(H, cx, cy, negatives, fills, extra="", bg=None, size=200):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}">', "<defs>",
         '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="200">',
         f'<path d="{H["d"]}" fill="#fff"/>', negatives, "</mask></defs>"]
    if bg: s.append(f'<rect width="200" height="200" fill="{bg}"/>')
    s.append('<g mask="url(#m)">' + fills + "</g>")
    s.append(extra)
    s.append("</svg>")
    return "\n".join(s)

def quads(cx, cy, ul, ur, ll, lr):
    return (f'<rect x="0" y="0" width="{cx}" height="{cy:.2f}" fill="{ul}"/>'
            f'<rect x="{cx}" y="0" width="{200-cx}" height="{cy:.2f}" fill="{ur}"/>'
            f'<rect x="0" y="{cy:.2f}" width="{cx}" height="{200-cy:.2f}" fill="{ll}"/>'
            f'<rect x="{cx}" y="{cy:.2f}" width="{200-cx}" height="{200-cy:.2f}" fill="{lr}"/>')

def tones(mode):
    if mode == "quartered": return DEEP, RED, RED, DEEP
    if mode == "flat": return RED, RED, RED, RED
    if mode == "halves": return DEEP, RED, DEEP, RED
    if mode == "prata": return PRATA, PRATA, PRATA, PRATA
    if mode == "mono": return GRAFITE, GRAFITE, GRAFITE, GRAFITE

def cross_neg(cx, cy, g):
    return (f'<rect x="{cx-g/2:.2f}" y="0" width="{g}" height="200" fill="#000"/>'
            f'<rect x="0" y="{cy-g/2:.2f}" width="200" height="{g}" fill="#000"/>')

# A — Cruz e Roda: cruz + anel em negativo
def A(mode="quartered", g=6.5, R=30, ring=6.5, dy=26, bg=None, inner_gold=False):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    neg = cross_neg(cx, cy, g) + f'<circle cx="{cx}" cy="{cy:.2f}" r="{R}" fill="none" stroke="#000" stroke-width="{ring}"/>'
    ul, ur, ll, lr = tones(mode)
    fills = quads(cx, cy, ul, ur, ll, lr)
    if inner_gold and mode != "prata":
        fills += f'<circle cx="{cx}" cy="{cy:.2f}" r="{R-ring/2:.2f}" fill="{GOLD}"/>'
    return frame(H, cx, cy, neg, fills, bg=bg)

# B — Cruz pátea: braços que se alargam para a borda
def B(mode="quartered", g0=4, g1=20, dy=26, bg=None):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    arms = [f'<polygon points="{cx-g0/2},{cy} {cx-g1/2},0 {cx+g1/2},0 {cx+g0/2},{cy}" fill="#000"/>',
            f'<polygon points="{cx-g0/2},{cy} {cx-g1/2},200 {cx+g1/2},200 {cx+g0/2},{cy}" fill="#000"/>',
            f'<polygon points="{cx},{cy-g0/2} 0,{cy-g1/2} 0,{cy+g1/2} {cx},{cy+g0/2}" fill="#000"/>',
            f'<polygon points="{cx},{cy-g0/2} 200,{cy-g1/2} 200,{cy+g1/2} {cx},{cy+g0/2}" fill="#000"/>']
    ul, ur, ll, lr = tones(mode)
    return frame(H, cx, cy, "".join(arms), quads(cx, cy, ul, ur, ll, lr), bg=bg)

# C — Quadrifólio: cantos internos arredondados
def C(mode="quartered", g=7, rc=14, dy=26, bg=None):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    neg = cross_neg(cx, cy, g)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0 = cx + sx*g/2; y0 = cy + sy*g/2                      # canto interno do quadrante
            ccx = x0 + sx*rc; ccy = y0 + sy*rc                       # centro do arredondamento
            # quadrado do canto em preto, depois círculo branco restaura o material arredondado
            neg += f'<rect x="{min(x0,ccx):.2f}" y="{min(y0,ccy):.2f}" width="{rc}" height="{rc}" fill="#000"/>'
            neg += f'<circle cx="{ccx:.2f}" cy="{ccy:.2f}" r="{rc}" fill="#fff"/>'
    # a cruz precisa vencer os círculos brancos: redesenha por cima
    neg += cross_neg(cx, cy, g)
    ul, ur, ll, lr = tones(mode)
    return frame(H, cx, cy, neg, quads(cx, cy, ul, ur, ll, lr), bg=bg)

# D — Cruz que se abre: vãos em curva suave (S)
def D(mode="quartered", g=6.5, k=14, dy=26, bg=None):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    v = f'<path d="M {cx},-10 C {cx},{cy-40} {cx+k},{cy-30} {cx},{cy} C {cx-k},{cy+30} {cx},{cy+40} {cx},210" fill="none" stroke="#000" stroke-width="{g}"/>'
    h = f'<path d="M -10,{cy} C {cx-40},{cy} {cx-30},{cy-k} {cx},{cy} C {cx+30},{cy+k} {cx+40},{cy} 210,{cy}" fill="none" stroke="#000" stroke-width="{g}"/>'
    ul, ur, ll, lr = tones(mode)
    return frame(H, cx, cy, v + h, quads(cx, cy, ul, ur, ll, lr), bg=bg)

# E — Pão partido: miolo circular em 4 partes, coroa externa inteira exceto a cruz fina
def E(mode="quartered", g=6.5, R=36, ring=5, dy=26, bg=None):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    neg = (f'<circle cx="{cx}" cy="{cy:.2f}" r="{R}" fill="none" stroke="#000" stroke-width="{ring}"/>'
           f'<rect x="{cx-g/2:.2f}" y="{cy-R:.2f}" width="{g}" height="{2*R}" fill="#000"/>'
           f'<rect x="{cx-R:.2f}" y="{cy-g/2:.2f}" width="{2*R}" height="{g}" fill="#000"/>')
    ul, ur, ll, lr = tones(mode)
    outer = DEEP if mode == "quartered" else ul
    fills = f'<rect width="200" height="200" fill="{outer}"/>' + f'<g clip-path="url(#ic)">' + quads(cx, cy, RED if mode=="quartered" else ul, DEEP if mode=="quartered" else ur, DEEP if mode=="quartered" else ll, RED if mode=="quartered" else lr) + "</g>"
    s = frame(H, cx, cy, neg, fills, bg=bg)
    return s.replace("<defs>", f'<defs><clipPath id="ic"><circle cx="{cx}" cy="{cy:.2f}" r="{R}"/></clipPath>', 1)

VARIANTS = {"A-cruz-roda": A, "B-cruz-patea": B, "C-quadrifolio": C, "D-cruz-aberta": D, "E-pao-partido": E}
if __name__ == "__main__":
    for n, f in VARIANTS.items():
        io.open(OUT/f"{n}.svg","w",encoding="utf-8").write(f())
        io.open(OUT/f"{n}-flat.svg","w",encoding="utf-8").write(f(mode="flat"))
        io.open(OUT/f"{n}-neg.svg","w",encoding="utf-8").write(f(mode="prata", bg=DEEP))
    io.open(OUT/"A-cruz-roda-gold.svg","w",encoding="utf-8").write(A(inner_gold=True))
    print("ok")

# F — Cruz e Roda nos cantos: quatro arcos (a roda "dividida em quatro partes", nos cantões), sem cruzar a cruz
def F(mode="quartered", g=7, R=34, ring=5.5, span=58, dy=26, bg=None):
    import math
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    neg = cross_neg(cx, cy, g)
    for a0 in (45, 135, 225, 315):   # centro de cada arco nos cantões
        s0, s1 = math.radians(a0 - span/2), math.radians(a0 + span/2)
        x0, y0 = cx + R*math.cos(s0), cy + R*math.sin(s0); x1, y1 = cx + R*math.cos(s1), cy + R*math.sin(s1)
        neg += f'<path d="M {x0:.2f},{y0:.2f} A {R},{R} 0 0 1 {x1:.2f},{y1:.2f}" fill="none" stroke="#000" stroke-width="{ring}" stroke-linecap="round"/>'
    ul, ur, ll, lr = tones(mode)
    return frame(H, cx, cy, neg, quads(cx, cy, ul, ur, ll, lr), bg=bg)

# G — Cruz de braços largos com miolo em losango (cruz de Santa Catarina estilizada): a cruz é o protagonista
def G(mode="quartered", g=12, dy=26, bg=None):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    neg = cross_neg(cx, cy, g)
    ul, ur, ll, lr = tones(mode)
    return frame(H, cx, cy, neg, quads(cx, cy, ul, ur, ll, lr), bg=bg)

VARIANTS.update({"F-cruz-roda-cantoes": F, "G-cruz-larga": G})
if __name__ == "__main__":
    for n in ("F-cruz-roda-cantoes", "G-cruz-larga"):
        f = VARIANTS[n]
        io.open(OUT/f"{n}.svg","w",encoding="utf-8").write(f())
        io.open(OUT/f"{n}-neg.svg","w",encoding="utf-8").write(f(mode="prata", bg=DEEP))
