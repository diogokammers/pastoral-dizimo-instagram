# -*- coding: utf-8 -*-
"""v19 — UC-verm com presença: coração maior no quadro, cruz pátea mais aberta, peças que se expandem."""
import io, math, pathlib
from build_logo3 import heart, RED, DEEP, PRATA
OUT = pathlib.Path(__file__).parent

def P(p): return f"{p[0]:.2f},{p[1]:.2f}"

def V(heart_kw=None, cyk=0.47, a=12.5, b=15, gap=3.4, top=24, bot=18, side_up=10, side_dn=20,
      explode=0.0, col="#B8161F", cross_col=None, bg=None, size=200, uid="v", dy_shift=9.0):
    H = heart(**(heart_kw or dict(w=176, top=26, side=0.22, tipk=0.57, pull=0.24, fall=0.27)))
    cx = H["cx"]; y0, y1 = H["top"], H["tip"][1]; cy = y0 + (y1 - y0)*cyk
    Lr = 400
    def up(p, deg, sx):   a_ = math.radians(deg); return (p[0] + sx*Lr*math.sin(a_), p[1] - Lr*math.cos(a_))
    def dn(p, deg, sx):   a_ = math.radians(deg); return (p[0] + sx*Lr*math.sin(a_), p[1] + Lr*math.cos(a_))
    def sd(p, deg, sx, upw): a_ = math.radians(deg); return (p[0] + sx*Lr*math.cos(a_), p[1] + (-1 if upw else 1)*Lr*math.sin(a_))
    ul, ur, ll, lr = (cx-a, cy-b), (cx+a, cy-b), (cx-a, cy+b), (cx+a, cy+b)
    # cruz pátea (polígono)
    cross = [ul, up(ul, top, -1), up(ur, top, 1), ur, sd(ur, side_up, 1, True), sd(lr, side_dn, 1, False), lr,
             dn(lr, bot, 1), dn(ll, bot, -1), ll, sd(ll, side_dn, -1, False), sd(ul, side_up, -1, True)]
    # peças (wedges entre as bordas dos braços), recuadas pela fresta via stroke da cruz
    pieces = {
      "ul": ([ul, up(ul, top, -1), (-400, -400), sd(ul, side_up, -1, True)], (-1, -1)),
      "ur": ([ur, up(ur, top, 1), (600, -400), sd(ur, side_up, 1, True)], (1, -1)),
      "ll": ([ll, dn(ll, bot, -1), (-400, 600), sd(ll, side_dn, -1, False)], (-1, 1)),
      "lr": ([lr, dn(lr, bot, 1), (600, 600), sd(lr, side_dn, 1, False)], (1, 1)),
    }
    cc = cross_col or col
    d = [f'<clipPath id="h{uid}"><path d="{H["d"]}"/></clipPath>',
         f'<mask id="g{uid}" maskUnits="userSpaceOnUse" x="-400" y="-400" width="1000" height="1000"><rect x="-400" y="-400" width="1000" height="1000" fill="#fff"/>'
         f'<polygon points="{" ".join(P(p) for p in cross)}" fill="#000" stroke="#000" stroke-width="{2*gap}" stroke-linejoin="miter"/></mask>']
    body = []
    for k, (poly, (sx, sy)) in pieces.items():
        d.append(f'<clipPath id="{k}{uid}"><polygon points="{" ".join(P(p) for p in poly)}"/></clipPath>')
        e = explode
        body.append(f'<g transform="translate({sx*e:.2f},{sy*e*0.8:.2f})"><g clip-path="url(#{k}{uid})"><g mask="url(#g{uid})"><path d="{H["d"]}" fill="{col}"/></g></g></g>')
    body.append(f'<g clip-path="url(#h{uid})"><polygon points="{" ".join(P(p) for p in cross)}" fill="{cc}"/></g>')
    b_ = f'<rect width="200" height="200" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}"><defs>{"".join(d)}</defs>{b_}<g transform="translate(0,{dy_shift})">{"".join(body)}</g></svg>'

VAR = {
 "W1-maior":          dict(),
 "W2-expande":        dict(explode=2.6),
 "W3-cruz-luz":       dict(explode=2.6, col="#A3121C", cross_col="#D0202A"),
 "W4-vivo":           dict(explode=2.6, col="#D3202A"),
 "W5-cruz-aberta":    dict(explode=2.6, top=28, bot=21, side_up=12, side_dn=23, a=13, b=16),
 "W6-aberta-luz":     dict(explode=2.6, top=28, bot=21, side_up=12, side_dn=23, a=13, b=16, col="#A3121C", cross_col="#D0202A"),
 "W7-expande-forte":  dict(explode=4.2, top=26, bot=19, side_up=11, side_dn=21, col="#C0161F"),
 "W8-aberta-vivo":    dict(explode=3.2, top=28, bot=21, side_up=12, side_dn=23, a=13, b=16, col="#C8181F", cross_col="#E0262C"),
}
if __name__ == "__main__":
    for k, p in VAR.items():
        u = k.split('-')[0]
        io.open(OUT/f"{k}.svg","w",encoding="utf-8").write(V(uid=u, **p))
        io.open(OUT/f"{k}-neg.svg","w",encoding="utf-8").write(V(uid=u+"n", **{**p, "col": PRATA, "cross_col": "#FFFFFF", "bg": "#7E0F17"}))
    print("ok")
