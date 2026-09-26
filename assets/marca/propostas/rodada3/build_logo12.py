# -*- coding: utf-8 -*-
"""v12 — 'Pedra de quatro faces': coração poligonal suave (amostrado da curva real), quatro faces planas
que se encontram num foco; as juntas formam uma cruz. Tons por luz (fonte no alto à direita)."""
import io, math, pathlib, json
from build_logo3 import heart, bez, RED, DEEP, PRATA, GOLD
OUT = pathlib.Path(__file__).parent
TONES = {"ul": "#6A0D14", "ur": "#B8161F", "ll": "#8E1119", "lr": "#D3242E"}   # sombra → luz
def P(x, y): return f"{x:.2f},{y:.2f}"
def wrap(body, size=200, bg=None, defs=""):
    b = f'<rect width="200" height="200" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}"><defs>{defs}</defs>{b}{body}</svg>'

def outline_pts(H, n_lobe=5, n_side=4):
    """amostra o coração: fenda → lobo direito → lateral direita → ponta → lateral esquerda → lobo esquerdo."""
    cx = H["cx"]; r = H["r"]; cl, cr, tip = H["cl"], H["cr"], H["tip"]
    pts = [(cx, H["cleft_y"])]
    # lobo direito: de ~226° (fenda) a 360°/0° (lateral), amostrado
    for i in range(1, n_lobe+1):
        a = math.radians(226 + (360-226)*i/n_lobe); pts.append((cr[0]+r*math.cos(a), cr[1]+r*math.sin(a)))
    c3 = (2*cx-H["c2"][0], H["c2"][1]); c4 = (2*cx-H["c1"][0], H["c1"][1])
    for i in range(1, n_side+1):
        t = i/n_side; pts.append(bez(H["R"], c4, c3, tip, t))
    left = [(2*cx-x, y) for (x, y) in pts[1:-1]][::-1]
    return pts + left

def F(size=200, bg=None, seam=None, seam_w=1.6, focus_dy=8, mono=None, tones=TONES, n_lobe=5, n_side=4):
    H = heart(w=138, top=44); cx = H["cx"]; cy = H["cl"][1] + focus_dy + 22
    pts = outline_pts(H, n_lobe, n_side)
    foc = (cx, cy)
    # índices: 0 = fenda; lateral direita = ponto do lobo em 0° ; ponta = índice n_lobe+n_side
    i_r = n_lobe; i_tip = n_lobe + n_side; i_l = len(pts) - n_lobe
    def poly(idx):
        return [pts[i] for i in idx]
    ur = poly(list(range(0, i_r+1))) + [foc]
    lr = poly(list(range(i_r, i_tip+1))) + [foc]
    ll = poly(list(range(i_tip, i_l+1))) + [foc]
    ul = poly(list(range(i_l, len(pts))) + [0]) + [foc]
    s = []
    for key, face in (("ul", ul), ("ur", ur), ("ll", ll), ("lr", lr)):
        s.append(f'<polygon points="{" ".join(P(*p) for p in face)}" fill="{mono or tones[key]}" stroke="{mono or tones[key]}" stroke-width="0.6" stroke-linejoin="round"/>')
    if seam:
        for i in (0, i_r, i_tip, i_l):
            s.append(f'<line x1="{foc[0]:.2f}" y1="{foc[1]:.2f}" x2="{pts[i][0]:.2f}" y2="{pts[i][1]:.2f}" stroke="{seam}" stroke-width="{seam_w}" stroke-linecap="round"/>')
    return wrap("".join(s), size=size, bg=bg), pts, foc

if __name__ == "__main__":
    io.open(OUT/"F1.svg","w",encoding="utf-8").write(F()[0])
    io.open(OUT/"F2-seam.svg","w",encoding="utf-8").write(F(seam=PRATA, seam_w=1.8)[0])
    io.open(OUT/"F3-gold.svg","w",encoding="utf-8").write(F(seam=GOLD, seam_w=1.6)[0])
    io.open(OUT/"F4-lowpoly.svg","w",encoding="utf-8").write(F(n_lobe=3, n_side=2)[0])
    io.open(OUT/"F5-dark.svg","w",encoding="utf-8").write(F(bg="#120A0B", seam="#E9C97A", seam_w=1.4)[0])
    svg, pts, foc = F()
    json.dump({"pts": pts, "foc": foc}, io.open(OUT/"F-geom.json","w",encoding="utf-8"))
    print("ok")
