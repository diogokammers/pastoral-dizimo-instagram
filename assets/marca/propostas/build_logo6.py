# -*- coding: utf-8 -*-
"""v6 — Quadrifólio construído positivamente: quatro peças com canto interno arredondado,
recortadas pelo coração. Sem máscara."""
import io, pathlib
from build_logo3 import heart, RED, DEEP, PRATA, GRAFITE, GOLD
from build_logo5 import tones
OUT = pathlib.Path(__file__).parent

def piece(x0, y0, x1, y1, corner, rc):
    """retângulo (x0,y0)-(x1,y1) com um canto arredondado: corner in br,bl,tr,tl."""
    if corner == "br": return f"M {x0},{y0} H {x1} V {y1-rc} A {rc},{rc} 0 0 1 {x1-rc},{y1} H {x0} Z"
    if corner == "bl": return f"M {x0},{y0} H {x1} V {y1} H {x0+rc} A {rc},{rc} 0 0 1 {x0},{y1-rc} Z"
    if corner == "tr": return f"M {x0},{y0} H {x1-rc} A {rc},{rc} 0 0 1 {x1},{y0+rc} V {y1} H {x0} Z"
    if corner == "tl": return f"M {x0+rc},{y0} H {x1} V {y1} H {x0} V {y0+rc} A {rc},{rc} 0 0 1 {x0+rc},{y0} Z"

def Q(mode="quartered", g=7, rc_top=16, rc_bot=11, dy=26, bg=None, size=200, uid="q"):
    H = heart(); cx = H["cx"]; cy = H["cl"][1] + dy
    ul, ur, ll, lr = tones(mode)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}">',
         f'<defs><clipPath id="hc{uid}"><path d="{H["d"]}"/></clipPath></defs>']
    if bg: s.append(f'<rect width="200" height="200" fill="{bg}"/>')
    s.append(f'<g clip-path="url(#hc{uid})">')
    s.append(f'<path d="{piece(-20,-20,cx-g/2,cy-g/2,"br",rc_top)}" fill="{ul}"/>')
    s.append(f'<path d="{piece(cx+g/2,-20,220,cy-g/2,"bl",rc_top)}" fill="{ur}"/>')
    s.append(f'<path d="{piece(-20,cy+g/2,cx-g/2,220,"tr",rc_bot)}" fill="{ll}"/>')
    s.append(f'<path d="{piece(cx+g/2,cy+g/2,220,220,"tl",rc_bot)}" fill="{lr}"/>')
    s.append("</g></svg>")
    return "\n".join(s)

if __name__ == "__main__":
    io.open(OUT/"Q1.svg","w",encoding="utf-8").write(Q())
    io.open(OUT/"Q2.svg","w",encoding="utf-8").write(Q(g=6, rc_top=22, rc_bot=14))
    io.open(OUT/"Q3-halves.svg","w",encoding="utf-8").write(Q(mode="halves", g=7, rc_top=18, rc_bot=12))
    io.open(OUT/"Q4-flat.svg","w",encoding="utf-8").write(Q(mode="flat", g=7, rc_top=18, rc_bot=12))
    io.open(OUT/"Q1-neg.svg","w",encoding="utf-8").write(Q(mode="prata", bg=DEEP))
    import build_logo5 as b
    io.open(OUT/"E1.svg","w",encoding="utf-8").write(b.E(R=34,ring=5,g=6))
    io.open(OUT/"E1-neg.svg","w",encoding="utf-8").write(b.E(mode="prata",bg=DEEP,R=34,ring=5,g=6))
    io.open(OUT/"B1.svg","w",encoding="utf-8").write(b.B(g0=5,g1=14))
    io.open(OUT/"B1-neg.svg","w",encoding="utf-8").write(b.B(mode="prata",bg=DEEP,g0=5,g1=14))
    print("ok")
