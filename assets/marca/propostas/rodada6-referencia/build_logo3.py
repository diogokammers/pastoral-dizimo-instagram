# -*- coding: utf-8 -*-
"""v3 — quatro pessoas cujos corpos são os quartos de um coração; as cabeças pousam
sobre o contorno (topo dos lobos e laterais), meio dentro, meio fora, com folga de
pescoço aberta para fora. A cruz nasce dos vãos entre os corpos. Grade 200x200."""
import io, math, pathlib

OUT = pathlib.Path(__file__).parent
RED = "#A3121C"; DEEP = "#7E0F17"; PRATA = "#F3F2EE"; GRAFITE = "#1E1B1B"; GOLD = "#B08D3B"

def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
            u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])

def heart(w=136, cx=100, top=44, side=0.22, tipk=0.64, pull=0.19, fall=0.24):
    r = w / 4.0
    cl = (cx - r, top + r); cr = (cx + r, top + r)
    tip = (cx, top + r + w * tipk)
    L = (cl[0] - r, cl[1]); R = (cr[0] + r, cr[1])
    c1 = (L[0], L[1] + w*side); c2 = (cx - w*pull, tip[1] - w*fall)
    c3 = (cx + w*pull, tip[1] - w*fall); c4 = (R[0], R[1] + w*side)
    cleft_y = top + r * 0.42
    d = (f"M {cx},{cleft_y:.3f} A {r},{r} 0 0 0 {L[0]:.3f},{L[1]:.3f} "
         f"C {c1[0]:.3f},{c1[1]:.3f} {c2[0]:.3f},{c2[1]:.3f} {tip[0]},{tip[1]:.3f} "
         f"C {c3[0]:.3f},{c3[1]:.3f} {c4[0]:.3f},{c4[1]:.3f} {R[0]:.3f},{R[1]:.3f} "
         f"A {r},{r} 0 0 0 {cx},{cleft_y:.3f} Z")
    return dict(d=d, r=r, cl=cl, cr=cr, tip=tip, L=L, R=R, c1=c1, c2=c2, cleft_y=cleft_y, cx=cx, top=top)

def side_point(H, y):
    """ponto da curva lateral esquerda na altura y (amostragem)."""
    best = None
    for i in range(401):
        t = i / 400
        p = bez(H["L"], H["c1"], H["c2"], H["tip"], t)
        if best is None or abs(p[1] - y) < abs(best[1] - y): best = p
    return best

def svg(P, two_tone=True, mono=None, bg=None, size=200, gold=False):
    H = heart(**P.get("heart", {}))
    cx = H["cx"]; r = H["r"]
    gap = P["gap"]; hr = P["head"]; neck = P["neck"]
    cross_y = H["cl"][1] + P["cross_dy"]
    # cabeças superiores: sobre o arco do lobo, num ângulo a partir do topo (0 = ápice)
    a = math.radians(P["top_angle"])
    hu_l = (H["cl"][0] - r*math.sin(a)*0 - r*math.sin(a), H["cl"][1] - r*math.cos(a))
    hu_l = (H["cl"][0] - r*math.sin(a), H["cl"][1] - r*math.cos(a))
    hu_r = (2*cx - hu_l[0], hu_l[1])
    # empurra levemente para fora (fração do raio da cabeça)
    out = P["out"]
    def push(c, center):
        vx, vy = c[0]-center[0], c[1]-center[1]; n = math.hypot(vx, vy)
        return (c[0] + vx/n*hr*out, c[1] + vy/n*hr*out)
    hu_l = push(hu_l, H["cl"]); hu_r = push(hu_r, H["cr"])
    # cabeças inferiores: sobre a curva lateral, abaixo da cruz
    sp = side_point(H, cross_y + P["low_dy"])
    # normal aproximada: direção para fora (esquerda) e um pouco para baixo
    hl_l = (sp[0] - hr*out*0.9, sp[1] + hr*out*0.35); hl_r = (2*cx - hl_l[0], hl_l[1])
    heads = [hu_l, hu_r, hl_l, hl_r]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}">', "<defs>",
         '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="200">',
         f'<path d="{H["d"]}" fill="#fff"/>',
         f'<rect x="{cx-gap/2:.2f}" y="0" width="{gap}" height="200" fill="#000"/>',
         f'<rect x="0" y="{cross_y-gap/2:.2f}" width="200" height="{gap}" fill="#000"/>']
    for hc in heads:  # folga do pescoço
        s.append(f'<circle cx="{hc[0]:.2f}" cy="{hc[1]:.2f}" r="{hr+neck:.2f}" fill="#000"/>')
    s.append("</mask></defs>")
    ul = lr = DEEP if two_tone else RED; ur = ll = RED
    if mono: ul = lr = ur = ll = mono
    if bg: s.append(f'<rect width="200" height="200" fill="{bg}"/>')
    s.append('<g mask="url(#m)">')
    s.append(f'<rect x="0" y="0" width="{cx}" height="{cross_y:.2f}" fill="{ul}"/>')
    s.append(f'<rect x="{cx}" y="0" width="{200-cx}" height="{cross_y:.2f}" fill="{ur}"/>')
    s.append(f'<rect x="0" y="{cross_y:.2f}" width="{cx}" height="{200-cross_y:.2f}" fill="{ll}"/>')
    s.append(f'<rect x="{cx}" y="{cross_y:.2f}" width="{200-cx}" height="{200-cross_y:.2f}" fill="{lr}"/>')
    s.append("</g>")
    cols = [ul, ur, ll, lr]
    for hc, c in zip(heads, cols):
        s.append(f'<circle cx="{hc[0]:.2f}" cy="{hc[1]:.2f}" r="{hr}" fill="{c}"/>')
    if gold:
        w = 3; l = 8
        s.append(f'<rect x="{cx-w/2}" y="{cross_y-l}" width="{w}" height="{2*l}" fill="{GOLD}"/>')
        s.append(f'<rect x="{cx-l}" y="{cross_y-w/2}" width="{2*l}" height="{w}" fill="{GOLD}"/>')
    s.append("</svg>")
    return "\n".join(s)

PARAMS = {
    "v3a": dict(gap=7, head=12, neck=4, cross_dy=26, top_angle=18, out=0.55, low_dy=14),
    "v3b": dict(gap=7, head=13, neck=4.5, cross_dy=30, top_angle=10, out=0.45, low_dy=10),
    "v3c": dict(gap=6, head=11, neck=3.5, cross_dy=22, top_angle=28, out=0.65, low_dy=18),
}
if __name__ == "__main__":
    for name, P in PARAMS.items():
        io.open(OUT / f"{name}.svg", "w", encoding="utf-8").write(svg(P))
        io.open(OUT / f"{name}-neg.svg", "w", encoding="utf-8").write(svg(P, mono=PRATA, bg=DEEP))
    io.open(OUT / "v3a-flat.svg", "w", encoding="utf-8").write(svg(PARAMS["v3a"], two_tone=False))
    print("ok")
