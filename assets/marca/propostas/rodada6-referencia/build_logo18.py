# -*- coding: utf-8 -*-
"""v18 — fiel à referência: coração com cruz pátea central (braços que se alargam até a borda)
e quatro peças de canto, separadas por frestas retas que partem dos cantos internos da cruz.
Ângulos medidos na referência (graus a partir do eixo):
  braço superior: ±21° da vertical · braço inferior: ±15° da vertical
  braço lateral: borda de cima 8.5° acima da horizontal, borda de baixo 17° abaixo."""
import io, math, pathlib
from build_logo3 import heart, RED, DEEP, PRATA, GRAFITE, GOLD
OUT = pathlib.Path(__file__).parent
VIVO = "#EE2F2C"

def R(heart_kw=None, cyk=0.47, a=11, b=13.5, gap=3.4, top=21, bot=15, side_up=8.5, side_dn=17,
      col=VIVO, cross_col=None, bg=None, size=200, uid="r", round_=0.0):
    H = heart(**(heart_kw or dict(w=150, top=40)))
    cx = H["cx"]; y0, y1 = H["top"], H["tip"][1]; cy = y0 + (y1 - y0)*cyk
    L = 300
    def ray(p, deg_from_up, sign_x):
        a_ = math.radians(deg_from_up); return (p[0] + sign_x*L*math.sin(a_), p[1] - L*math.cos(a_))
    corners = {"ul": (cx-a, cy-b), "ur": (cx+a, cy-b), "ll": (cx-a, cy+b), "lr": (cx+a, cy+b)}
    lines = []
    for k, p in corners.items():
        sx = -1 if k[1] == "l" else 1
        if k[0] == "u":
            lines.append((p, ray(p, top, sx)))                                   # borda do braço superior
            ang = math.radians(side_up); lines.append((p, (p[0] + sx*L*math.cos(ang), p[1] - L*math.sin(ang))))   # lateral, sobe
        else:
            a_ = math.radians(bot); lines.append((p, (p[0] + sx*L*math.sin(a_), p[1] + L*math.cos(a_))))          # braço inferior
            ang = math.radians(side_dn); lines.append((p, (p[0] + sx*L*math.cos(ang), p[1] + L*math.sin(ang))))  # lateral, desce
    cuts = "".join(f'<line x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" y2="{q[1]:.2f}" stroke="#000" stroke-width="{gap}" stroke-linecap="butt"/>' for p, q in lines)
    defs = (f'<mask id="m{uid}" maskUnits="userSpaceOnUse" x="-100" y="-100" width="400" height="400"><path d="{H["d"]}" fill="#fff"/>{cuts}</mask>'
            f'<clipPath id="h{uid}"><path d="{H["d"]}"/></clipPath>')
    body = f'<g mask="url(#m{uid})"><path d="{H["d"]}" fill="{col}"/>'
    if cross_col:   # cruz em outra cor: polígono da cruz pátea
        ul, ur, ll, lr = corners["ul"], corners["ur"], corners["ll"], corners["lr"]
        def far(p, deg, sx, up=True):
            a_ = math.radians(deg); return (p[0] + sx*L*math.sin(a_), p[1] + (-1 if up else 1)*L*math.cos(a_))
        def side(p, deg, sx, up):
            a_ = math.radians(deg); return (p[0] + sx*L*math.cos(a_), p[1] + (-1 if up else 1)*L*math.sin(a_))
        poly = [ul, far(ul, top, -1), far(ur, top, 1), ur, side(ur, side_up, 1, True), side(lr, side_dn, 1, False), lr,
                far(lr, bot, 1, False), far(ll, bot, -1, False), ll, side(ll, side_dn, -1, False), side(ul, side_up, -1, True)]
        body += f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in poly)}" fill="{cross_col}"/>'
    body += "</g>"
    b_ = f'<rect width="200" height="200" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}"><defs>{defs}</defs>{b_}{body}</svg>'

V = {
 "R1-referencia":   dict(),
 "R2-vermelho":     dict(col=RED),
 "R3-cruz-clara":   dict(col=DEEP, cross_col=RED),
 "R4-cruz-ouro":    dict(col=RED, cross_col="#C9A24A"),
 "R5-cruz-vivo":    dict(col="#B8161F", cross_col=VIVO),
 "R6-fresta-fina":  dict(col=RED, gap=2.6),
 "R7-cruz-reta":    dict(col=RED, top=12, bot=10, side_up=5, side_dn=10),
 "R8-aberta":       dict(col=RED, top=26, bot=19, side_up=11, side_dn=21),
}
if __name__ == "__main__":
    for k, p in V.items():
        u = k.split('-')[0]
        io.open(OUT/f"{k}.svg","w",encoding="utf-8").write(R(uid=u, **p))
        io.open(OUT/f"{k}-neg.svg","w",encoding="utf-8").write(R(uid=u+"n", **{**p, "col": PRATA, "cross_col": None, "bg": "#7E0F17"}))
    print("ok")
