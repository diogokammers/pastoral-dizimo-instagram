# -*- coding: utf-8 -*-
"""v15 — cortes únicos: N frestas partindo de um anel sólido central até a borda.
cuts: ângulos (0 = para cima, horário). solid: raio do miolo. skew: inclinação do corte em relação ao raio (efeito obturador).
taper: fresta mais larga na borda que no início."""
import io, math, pathlib
from build_logo3 import heart, RED, DEEP, PRATA, GRAFITE, GOLD
OUT = pathlib.Path(__file__).parent
VIVO = "#E8262B"
def pol(c, r, deg):
    a = math.radians(deg - 90); return (c[0] + r*math.cos(a), c[1] + r*math.sin(a))

def C(cuts, solid=16, gap=4.5, taper=1.0, skew=0, dy=22, col=RED, cols=None, bg=None, size=200, uid="c", heart_kw=None):
    H = heart(**(heart_kw or dict(w=142, top=40))); cx = H["cx"]; c = (cx, H["cl"][1] + dy)
    black = ""
    for a in cuts:
        p0 = pol(c, solid, a)
        d = a + skew                           # direção do corte
        p1 = pol(p0, 220, d)
        # fresta como trapézio (largura gap no início, gap*taper no fim)
        n0 = math.radians(d); nx, ny = math.cos(n0), math.sin(n0)   # perpendicular (em coords 0=cima)
        w0, w1 = gap/2, gap*taper/2
        pts = [(p0[0]-nx*w0, p0[1]-ny*w0), (p0[0]+nx*w0, p0[1]+ny*w0), (p1[0]+nx*w1, p1[1]+ny*w1), (p1[0]-nx*w1, p1[1]-ny*w1)]
        black += f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in pts)}" fill="#000"/>'
    defs = (f'<mask id="m{uid}" maskUnits="userSpaceOnUse" x="-80" y="-80" width="360" height="360">'
            f'<path d="{H["d"]}" fill="#fff"/>{black}</mask>')
    if cols:   # setores alternados
        secs = ""; cs = sorted(cuts); n = len(cs)
        for i in range(n):
            a0 = cs[i]; a1 = cs[(i+1) % n] + (360 if i == n-1 else 0)
            p1, p2, pm = pol(c, 300, a0), pol(c, 300, a1), pol(c, 300, (a0+a1)/2)
            secs += f'<polygon points="{c[0]:.1f},{c[1]:.1f} {p1[0]:.1f},{p1[1]:.1f} {pm[0]:.1f},{pm[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{cols[i % len(cols)]}"/>'
        body = f'<g mask="url(#m{uid})"><path d="{H["d"]}" fill="{col}"/>{secs}<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="{solid+0.5}" fill="{col}"/></g>'
    else:
        body = f'<g mask="url(#m{uid})"><path d="{H["d"]}" fill="{col}"/></g>'
    b = f'<rect width="200" height="200" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}"><defs>{defs}</defs>{b}{body}</svg>'

R8 = (-160, -122, -78, -38, 38, 78, 122, 160)          # simétrico, eixo vertical sólido (cruz implícita)
R8b = (-157.5, -112.5, -67.5, -22.5, 22.5, 67.5, 112.5, 157.5)
R6 = (-150, -95, -35, 35, 95, 150)
R4 = (-135, -45, 45, 135)                               # quatro fatias: as quatro dimensões
V = {
 "C1-ref":      dict(cuts=R8, solid=15, gap=4.6, taper=1.35, skew=-9, col=VIVO),
 "C2-8-skew":   dict(cuts=R8, solid=15, gap=4.6, taper=1.35, skew=-9),
 "C3-8-reto":   dict(cuts=R8, solid=15, gap=4.6, taper=1.35, skew=0),
 "C4-8-reg":    dict(cuts=R8b, solid=14, gap=4.4, taper=1.3, skew=0),
 "C5-6":        dict(cuts=R6, solid=14, gap=5, taper=1.3, skew=0),
 "C6-4":        dict(cuts=R4, solid=12, gap=5.5, taper=1.4, skew=0),
 "C7-8-2t":     dict(cuts=R8, solid=15, gap=4.6, taper=1.35, skew=-9, cols=(RED, DEEP)),
 "C8-4-2t":     dict(cuts=R4, solid=12, gap=5.5, taper=1.4, skew=0, cols=(DEEP, RED)),
}
if __name__ == "__main__":
    for k, p in V.items():
        u = k.split('-')[0]
        io.open(OUT/f"{k}.svg","w",encoding="utf-8").write(C(uid=u, **p))
        io.open(OUT/f"{k}-neg.svg","w",encoding="utf-8").write(C(uid=u+"n", **{**p, "col": PRATA, "cols": None, "bg": DEEP}))
    print("ok")
