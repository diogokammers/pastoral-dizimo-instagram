# -*- coding: utf-8 -*-
import io, pathlib
from marca_final import symbol, C, VARIANTS
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).parent

def S(px, uid, **k):
    return symbol(size=px, uid=uid, **k)

NEG = {k: v for k, v in VARIANTS["negativo"].items() if k != "bg"}
SOBRE = {k: v for k, v in VARIANTS["sobre-vermelho"].items() if k != "bg"}

def lock(uid, dark=False):
    ink = "#F3F2EE" if dark else "#A3121C"
    sub = "#D9B85C" if dark else "#5F5A57"
    sym = S(72, uid, **(NEG if dark else {}))
    bg = "#140B0C" if dark else "#FBFAF7"
    return (f'<div class="lock" style="background:{bg}">{sym}<div>'
            f'<div class="ln1" style="color:{ink}">Pastoral do Dízimo</div>'
            f'<div class="ln2" style="color:{sub}">Arquidiocese de Florianópolis</div></div></div>')

DIMS = [("Religiosa", "gratidão a Deus, de quem tudo recebemos", C["q1"]),
        ("Eclesial", "sustento da comunidade que celebra", C["q2"]),
        ("Missionária", "a Igreja que sai ao encontro", C["q2"]),
        ("Caritativa", "cuidado com quem mais precisa", C["q1"])]
dim_html = "".join(f'<div class="dim"><span style="background:{c}"></span><div><b>{n}</b><i>{t}</i></div></div>' for n, t, c in DIMS)

def post(title, eyebrow, bgc, fg, uid, kw):
    return (f'<div class="post" style="background:{bgc};color:{fg}"><div class="pe">{eyebrow}</div>'
            f'<div class="pt">{title}</div><div class="pf">{S(40, uid, **kw)}<span>@pastoraldodizimo.arquifln</span></div></div>')

def sz(px_box, px_sym, uid, bg, label, border=True, **kw):
    b = "border:1px solid #DDD8CF;" if border else ""
    return (f'<div class="sz"><div style="width:{px_box}px;height:{px_box}px;background:{bg};{b}">'
            f'{S(px_sym, uid, **kw)}</div>{label}</div>')

CSS = """
body{margin:0;background:#F3F2EE;color:#1E1B1B;font-family:"Source Sans 3","Segoe UI",sans-serif;width:1280px}
.hero{display:grid;grid-template-columns:1fr 1fr;height:620px}
.hl{background:#FBFAF7;display:flex;align-items:center;justify-content:center}
.hr{background:#140B0C;display:flex;align-items:center;justify-content:center}
.wrap{padding:60px 72px}
.eb{font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:#A3121C;font-weight:600}
h1{font-family:"Cormorant Garamond",Georgia,serif;font-weight:600;font-size:64px;line-height:1;margin:12px 0 16px}
h2{font-family:"Cormorant Garamond",Georgia,serif;font-weight:600;font-size:40px;margin:6px 0 10px}
p{font-size:19px;line-height:1.55;max-width:780px;color:#3A3533;margin:0 0 14px}
.quote{font-family:"Cormorant Garamond",serif;font-style:italic;font-size:30px;color:#7E0F17;margin:18px 0 0}
.grid2{display:grid;grid-template-columns:420px 1fr;gap:56px;align-items:center}
.dim{display:flex;gap:14px;align-items:flex-start;margin:14px 0}
.dim span{width:26px;height:26px;border-radius:4px;flex:none;margin-top:3px}
.dim b{display:block;font-size:19px}.dim i{font-style:normal;color:#5F5A57}
.star{display:flex;gap:14px;align-items:flex-start;margin-top:22px;padding-top:18px;border-top:1px solid #DDD8CF}
.star span{width:26px;height:26px;border-radius:50%;background:#C9A24A;flex:none;margin-top:3px}
.locks{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.lock{display:flex;align-items:center;gap:22px;padding:34px 38px;border-radius:10px}
.ln1{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:40px;line-height:1}
.ln2{font-size:13px;letter-spacing:.22em;text-transform:uppercase;margin-top:8px}
.sizes{display:flex;gap:34px;align-items:flex-end;flex-wrap:wrap}
.sz{text-align:center;font-size:13px;color:#5F5A57}
.sz>div{margin:0 auto 8px;border-radius:50%;display:flex;align-items:center;justify-content:center;overflow:hidden}
.posts{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.post{aspect-ratio:4/5;border-radius:6px;padding:34px 30px;display:flex;flex-direction:column;box-sizing:border-box}
.pe{font-size:12px;letter-spacing:.2em;text-transform:uppercase;opacity:.8;font-weight:600}
.pt{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:42px;line-height:1.02;margin-top:16px}
.pf{margin-top:auto;display:flex;align-items:center;gap:12px;font-size:13px;opacity:.9}
.ig{background:#000;color:#f2f2f2;border-radius:18px;padding:26px;display:flex;gap:22px;align-items:center;width:600px}
.igav{width:120px;height:120px;border-radius:50%;background:#FBFAF7;display:flex;align-items:center;justify-content:center;flex:none}
.igt b{font-size:18px;display:block}.igt span{color:#ccc;font-size:14px;display:block;margin-top:4px}
.igt small{color:#aaa;display:block;margin-top:8px;font-size:13px;line-height:1.4}
section{border-top:1px solid #DDD8CF}
"""

html = f"""<meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Source+Sans+3:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="hero"><div class="hl">{S(460, "h1")}</div><div class="hr">{S(460, "h2", **NEG)}</div></div>
<section class="wrap"><div class="eb">Pastoral do Dízimo · Arquidiocese de Florianópolis</div><h1>Coração do Encontro</h1>
<p>Quatro partes formam um só coração: as quatro dimensões do dízimo. Elas não se separam, se encontram. E no ponto exato do encontro nasce, em luz, a cruz.</p>
<p>A cruz não foi desenhada por cima. Ela é o que acontece quando as dimensões religiosa, eclesial, missionária e caritativa se tocam. Cada braço tem o formato da mandorla, a moldura com que a arte cristã envolve o Cristo em glória. O ouro vem das insígnias do brasão da Arquidiocese; os dois vermelhos, do escudo.</p>
<div class="quote">“Deus ama quem dá com alegria.” (2Cor 9,7)</div></section>
<section class="wrap"><div class="grid2"><div>{S(420, "d1")}</div><div><div class="eb">Anatomia</div><h2>Quatro dimensões, uma cruz</h2>{dim_html}
<div class="star"><span></span><div><b style="font-size:19px">A cruz de luz</b><i style="font-style:normal;color:#5F5A57;display:block">nasce do encontro das quatro; proporção de cruz latina, braços em mandorla</i></div></div></div></div></section>
<section class="wrap"><div class="eb">Assinaturas</div><h2 style="margin-bottom:22px">Com o nome</h2><div class="locks">{lock("l1")}{lock("l2", dark=True)}</div></section>
<section class="wrap"><div class="eb">Tamanhos e fundos</div><h2 style="margin-bottom:22px">Legível do perfil ao ícone mínimo</h2><div class="sizes">
{sz(150, 118, "z1", "#FBFAF7", "avatar 150")}{sz(110, 86, "z2", "#FBFAF7", "110")}{sz(56, 44, "z3", "#FBFAF7", "56")}{sz(32, 26, "z4", "#FBFAF7", "32")}
{sz(110, 86, "z5", "#140B0C", "negativo", False, **NEG)}{sz(110, 86, "z6", "#7E0F17", "sobre vermelho", False, **SOBRE)}{sz(110, 86, "z7", "#FFFFFF", "uma cor", True, **VARIANTS["mono"])}
</div></section>
<section class="wrap"><div class="eb">Em uso</div><h2 style="margin-bottom:22px">No perfil e no feed</h2>
<div class="ig"><div class="igav">{S(96, "i1")}</div><div class="igt"><b>pastoraldodizimo.arquifln</b><span>Pastoral do Dízimo | Arquidiocese Florianópolis</span><small>Evangelizar, formar e fortalecer o dízimo como expressão de fé, gratidão e corresponsabilidade na missão da Igreja.</small></div></div>
<div class="posts" style="margin-top:22px">{post("O que é o dízimo?", "Formação", "#7E0F17", "#F3F2EE", "p1", NEG)}{post("Quatro dimensões, um só coração", "Formação", "#FBFAF7", "#A3121C", "p2", {})}{post("Deus ama quem dá com alegria", "Reflexão dominical", "#140B0C", "#F3F2EE", "p3", NEG)}</div></section>
"""
io.open(HERE / "marca-final.html", "w", encoding="utf-8").write(html)
if __name__ == "__main__":
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto((HERE / "marca-final.html").resolve().as_uri()); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(HERE / "marca-final.png"), full_page=True); b.close()
    print("ok")
