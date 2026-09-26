# -*- coding: utf-8 -*-
"""Símbolo final — 'Coração do Encontro'.
Quatro quadrantes (as quatro dimensões do dízimo) e, no encontro deles, uma cruz-estrela de luz
formada por mandorlas (vesica piscis). Construção limpa: quadrantes + estrela única por cima."""
import io, math, pathlib
from build_logo3 import heart
OUT = pathlib.Path(__file__).parent
C = dict(q1="#8E1119", q2="#B8161F", star="#C9A24A", prata="#F3F2EE", grafite="#1E1B1B", noite="#140B0C", red="#A3121C")

def prof(t0, tc, t1, s, sharp):
    def f(t):
        if t <= t0 or t >= t1: return 0.0
        u = (t - t0)/(tc - t0) if t < tc else (t1 - t)/(t1 - tc)
        return s * math.sin(math.pi/2*u) ** sharp
    return f

def geometry(cy_off=56, arm_top=25, arm_bot=46, arm_side=24, sv=8.5, sh=8, sharp=1.3, N=240):
    H = heart(w=144, top=36); cx = H["cx"]; cy = H["top"] + cy_off
    bv = prof(cy-arm_top, cy, cy+arm_bot, sv, sharp); bh = prof(cx-arm_side, cx, cx+arm_side, sh, sharp)
    ys = [cy-arm_top + (arm_top+arm_bot)*i/N for i in range(N+1)]
    xs = [cx-arm_side + 2*arm_side*i/N for i in range(N+1)]
    vl = [(cx+bv(y), y) for y in ys] + [(cx-bv(y), y) for y in reversed(ys)]
    hl = [(x, cy+bh(x)) for x in xs] + [(x, cy-bh(x)) for x in reversed(xs)]
    return H, cx, cy, vl, hl

def pts(p): return " ".join(f"{x:.3f},{y:.3f}" for x, y in p)

def symbol(q1=C["q1"], q2=C["q2"], star=C["star"], bg=None, size=200, uid="s", pad=0):
    H, cx, cy, vl, hl = geometry()
    vb = f"{-pad} {-pad} {200+2*pad} {200+2*pad}"
    b = f'<rect x="{-pad}" y="{-pad}" width="{200+2*pad}" height="{200+2*pad}" fill="{bg}"/>' if bg else ""
    quads = (f'<rect x="-10" y="-10" width="{cx+10}" height="{cy+10}" fill="{q1}"/>'
             f'<rect x="{cx}" y="-10" width="{210-cx}" height="{cy+10}" fill="{q2}"/>'
             f'<rect x="-10" y="{cy}" width="{cx+10}" height="{210-cy}" fill="{q2}"/>'
             f'<rect x="{cx}" y="{cy}" width="{210-cx}" height="{210-cy}" fill="{q1}"/>')
    st = f'<polygon points="{pts(vl)}" fill="{star}"/><polygon points="{pts(hl)}" fill="{star}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{size}" height="{size}">'
            f'<defs><clipPath id="h{uid}"><path d="{H["d"]}"/></clipPath></defs>{b}'
            f'<g clip-path="url(#h{uid})">{quads}{st}</g></svg>')

VARIANTS = {
  "principal":   dict(),
  "negativo":    dict(q1="#E9E4DA", q2="#FFFFFF", star="#C9A24A", bg=C["noite"]),
  "sobre-vermelho": dict(q1="#F3F2EE", q2="#FFFFFF", star="#D9B85C", bg="#7E0F17"),
  "mono":        dict(q1=C["grafite"], q2=C["grafite"], star="#FFFFFF"),
  "mono-verm":   dict(q1=C["red"], q2=C["red"], star="#FFFFFF"),
}
if __name__ == "__main__":
    for k, p in VARIANTS.items():
        io.open(OUT/f"final-{k}.svg", "w", encoding="utf-8").write(symbol(uid=k[:3], **p))
    print("ok")
