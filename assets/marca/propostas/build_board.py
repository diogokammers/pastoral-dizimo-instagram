# -*- coding: utf-8 -*-
"""Prancha final de identidade (HTML) + exportação dos SVGs para o repositório."""
import io, pathlib, shutil, itertools
import build_logo5 as b5, build_logo6 as b6, build_destaques as d
from build_logo3 import RED, DEEP, PRATA, GRAFITE, GOLD

HERE = pathlib.Path(__file__).parent
REPO = pathlib.Path(r"C:\Users\odnac\OneDrive\Computador antigo\Documentos\dnacx\aaaProjetos\pastoral-dizimo-instagram")
ASSETS = REPO / "assets" / "marca" / "propostas"; ASSETS.mkdir(parents=True, exist_ok=True)
_c = itertools.count()

def uniq(svg):
    k = f"u{next(_c)}"
    for i in ("m", "ic", "hc", "hcq", "hcdz"):
        svg = svg.replace(f'id="{i}"', f'id="{i}{k}"').replace(f'url(#{i})', f'url(#{i}{k})')
    return svg
def sz(svg, px): return uniq(svg.replace('width="200" height="200">', f'width="{px}" height="{px}">', 1))

CANDS = {
  "Q2":  ("Quadrifólio", "Quatro pétalas de cantos amplos em torno de uma cruz; lê como rosácea/janela de igreja. Tons alternados como o escudo esquartelado.", lambda **k: b6.Q(g=6, rc_top=22, rc_bot=14, uid="q2", **k)),
  "Q3":  ("Quadrifólio em metades", "A mesma peça com duas metades, como o símbolo atual: continuidade de leitura.", lambda **k: b6.Q(g=7, rc_top=18, rc_bot=12, uid="q3", **{**dict(mode="halves"), **k})),
  "E1":  ("Pão partido", "Coração inteiro com o miolo circular partido em quatro: hóstia, rosácea, comunidade.", lambda **k: b5.E(R=34, ring=5, g=6, **k)),
  "B1":  ("Cruz pátea", "Cruz cujos braços se alargam para a borda, tradição das cruzes de consagração.", lambda **k: b5.B(g0=5, g1=14, **k)),
}
# exporta SVGs
for key, (name, _, fn) in CANDS.items():
    io.open(ASSETS / f"simbolo-{key}.svg", "w", encoding="utf-8").write(fn())
    io.open(ASSETS / f"simbolo-{key}-negativo.svg", "w", encoding="utf-8").write(fn(mode="prata", bg=DEEP))
    io.open(ASSETS / f"simbolo-{key}-mono.svg", "w", encoding="utf-8").write(fn(mode="mono"))
for n in d.ICONS:
    io.open(ASSETS / f"capa-{n}-escura.svg", "w", encoding="utf-8").write(d.cover_svg(n))
    io.open(ASSETS / f"capa-{n}-clara.svg", "w", encoding="utf-8").write(d.cover_svg(n, bg=PRATA, fg=RED, ringcolor=RED))
for f in ("build_logo3.py", "build_logo5.py", "build_logo6.py", "build_destaques.py", "build_board.py"):
    shutil.copy(HERE / f, ASSETS / f)

def lockup(fn, horizontal=True, dark=False):
    ink = PRATA if dark else RED; sub = "#D9B85C" if dark else "#5F5A57"
    sym = sz(fn(mode="prata") if dark else fn(), 64 if horizontal else 92)
    if horizontal:
        return f'<div class="lk"><span>{sym}</span><span class="lt"><b style="color:{ink}">Pastoral do Dízimo</b><i style="color:{sub}">Arquidiocese de Florianópolis</i></span></div>'
    return f'<div class="lk v"><span>{sym}</span><span class="lt"><b style="color:{ink}">Pastoral do Dízimo</b><i style="color:{sub}">Arquidiocese de Florianópolis</i></span></div>'

def circ_cover(n, px, **kw):
    c = d.cover_svg(n, **kw).replace('width="1080" height="1920">', f'width="{px}" height="{px*1920/1080:.1f}">', 1)
    return f'<div class="hc" style="width:{px}px;height:{px}px"><div style="position:absolute;left:0;top:{-px*420/1080:.1f}px;line-height:0">{uniq(c)}</div></div>'

def cand_card(key):
    name, desc, fn = CANDS[key]
    return f'''<div class="cand" id="{key}">
      <div class="ch"><span class="tag">{key}</span><h3>{name}</h3></div>
      <div class="stage">{sz(fn(), 220)}</div>
      <p>{desc}</p>
      <div class="vars">
        <div class="av">{sz(fn(), 68)}</div>
        <div class="av neg">{sz(fn(mode="prata"), 68)}</div>
        <div class="av mono">{sz(fn(mode="mono"), 68)}</div>
        <div class="av tiny">{sz(fn(), 30)}</div>
      </div>
      {lockup(fn)}
    </div>'''

def profile_mock(key):
    fn = CANDS[key][2]
    hl = "".join(f'<div class="hi">{circ_cover(n, 62)}<span>{d.LABELS[n]}</span></div>' for n in d.ICONS)
    posts = ""
    for i, (bg, fg, t) in enumerate([(DEEP, PRATA, "O que é o dízimo?"), (PRATA, RED, "Para onde vai o dízimo?"), (DEEP, PRATA, "Bem-vindos")]):
        posts += f'<div class="pst" style="background:{bg};color:{fg}"><div class="pt">{t}</div><div class="pm">{sz(fn(mode="prata") if bg == DEEP else fn(), 22)}</div></div>'
    return f'''<div class="ig">
      <div class="igh"><div class="igav">{sz(fn(), 74)}</div>
        <div class="igt"><b>pastoraldodizimo.arquifln</b><span>Pastoral do Dízimo | Arquidiocese Florianópolis</span><small>Evangelizar, formar e fortalecer o dízimo como expressão de fé, gratidão e corresponsabilidade na missão da Igreja.</small></div></div>
      <div class="igr">{hl}</div>
      <div class="igg">{posts}</div>
    </div>'''

covers_dark = "".join(f'<div class="cv">{circ_cover(n, 120)}<span>{d.LABELS[n]}</span></div>' for n in d.ICONS)
covers_light = "".join(f'<div class="cv">{circ_cover(n, 120, bg=PRATA, fg=RED, ringcolor=RED)}<span>{d.LABELS[n]}</span></div>' for n in d.ICONS)
icons_row = "".join(f'<div class="ic">{uniq(d.icon_svg(n, 64, RED))}</div>' for n in d.ICONS)

html = f'''<title>Identidade Pastoral do Dízimo</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Source+Sans+3:wght@400;600&display=swap">
<style>
:root{{--bg:#F3F2EE;--bg2:#FFFFFF;--ink:#1E1B1B;--ink2:#5F5A57;--line:#DDD8CF;--red:#A3121C;--serif:"Cormorant Garamond",Georgia,serif;--sans:"Source Sans 3","Segoe UI",Arial,sans-serif}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#171414;--bg2:#201C1C;--ink:#F1EEE8;--ink2:#B7AFA8;--line:#3A3332;--red:#E2555D}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#171414;--bg2:#201C1C;--ink:#F1EEE8;--ink2:#B7AFA8;--line:#3A3332;--red:#E2555D}}
body{{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:17px;line-height:1.5;margin:0;padding-block:0 64px;padding-inline:16px}}
.wrap{{max-width:1080px;margin:0 auto}}
header{{padding-block:52px 28px;border-bottom:1px solid var(--line)}}
.eyebrow{{font-weight:600;text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--red)}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(36px,6vw,60px);line-height:1.02;margin:10px 0 12px;text-wrap:balance}}
h2{{font-family:var(--serif);font-weight:600;font-size:32px;line-height:1.1;margin:0 0 8px;text-wrap:balance}}
h3{{font-family:var(--serif);font-weight:600;font-size:24px;margin:0}}
p{{max-width:66ch;margin:0 0 10px}} .lead{{font-size:19px;color:var(--ink2)}}
section{{padding-block:40px;border-bottom:1px solid var(--line)}}
.cands{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-top:16px}}
.cand{{background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:16px;display:flex;flex-direction:column;gap:12px}}
.cand#Q2{{outline:2px solid var(--red);outline-offset:-2px}}
.ch{{display:flex;align-items:center;gap:10px}}
.tag{{font-size:11px;font-weight:600;letter-spacing:.1em;padding:3px 7px;border-radius:3px;background:var(--red);color:#fff}}
.stage{{background:#F3F2EE;border-radius:4px;display:flex;justify-content:center;padding:18px}}
.cand p{{font-size:14px;color:var(--ink2)}}
.vars{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.av{{width:84px;height:84px;border-radius:50%;background:#F3F2EE;border:1px solid #DDD8CF;display:flex;align-items:center;justify-content:center;line-height:0}}
.av.neg{{background:#7E0F17;border-color:#7E0F17}} .av.mono{{background:#fff}} .av.tiny{{width:40px;height:40px}}
.lk{{display:flex;align-items:center;gap:12px;line-height:0}} .lk.v{{flex-direction:column;text-align:center;gap:10px}}
.lt{{display:flex;flex-direction:column;line-height:1}} .lt b{{font-family:var(--serif);font-weight:600;font-size:22px;white-space:nowrap}} .lt i{{font-style:normal;font-size:10px;letter-spacing:.18em;text-transform:uppercase;margin-top:5px}}
.lkrow{{display:flex;gap:28px;flex-wrap:wrap;align-items:center;margin-top:14px}}
.dark{{background:#7E0F17;padding:22px 26px;border-radius:6px}}
.light{{background:#F3F2EE;padding:22px 26px;border-radius:6px;border:1px solid #DDD8CF}}
/* perfil simulado */
.ig{{background:#000;color:#f5f5f5;border-radius:14px;padding:22px 18px;max-width:420px;font-size:13px}}
.igh{{display:flex;gap:16px;align-items:flex-start}} .igav{{width:86px;height:86px;border-radius:50%;background:#F3F2EE;display:flex;align-items:center;justify-content:center;line-height:0;flex:none}}
.igt{{display:flex;flex-direction:column;gap:3px}} .igt b{{font-size:15px}} .igt span{{color:#ddd}} .igt small{{color:#bbb;font-size:12px;line-height:1.35}}
.igr{{display:flex;gap:12px;margin-top:18px;overflow-x:auto;padding-bottom:4px}} .hi{{display:flex;flex-direction:column;align-items:center;gap:5px;font-size:11px;color:#eee;flex:none}}
.hc{{border-radius:50%;overflow:hidden;position:relative;background:#222;border:2px solid #262626}}
.igg{{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin-top:16px}}
.pst{{aspect-ratio:4/5;padding:10px 9px;display:flex;flex-direction:column;justify-content:space-between}} .pt{{font-family:var(--serif);font-weight:600;font-size:15px;line-height:1.05}} .pm{{line-height:0}}
.mocks{{display:flex;gap:22px;flex-wrap:wrap;margin-top:14px}}
.cvs{{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}} .cv{{display:flex;flex-direction:column;align-items:center;gap:6px;font-size:13px;color:var(--ink2)}} .cv .hc{{border:0;background:transparent}}
.icons{{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px}} .ic{{line-height:0;background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:12px}}
table{{border-collapse:collapse;width:100%;font-size:15px}} th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}} th{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink2)}}
.decide{{background:var(--bg2);border:1px solid var(--line);border-left:4px solid var(--red);padding:18px 22px;border-radius:4px}} .decide ol{{margin:8px 0 0;padding-left:20px}}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">Identidade visual · rodada 2 · símbolo e destaques</div>
  <h1>Coração partido em quatro</h1>
  <p class="lead">O símbolo atual é um coração formado por quatro pessoas. Esta rodada mantém o coração, as quatro partes e os dois vermelhos, e troca as figuras por uma divisão eclesial: uma cruz. Quatro finalistas construídos por geometria, mostrados no tamanho real do perfil.</p>
</header>

<section>
  <div class="eyebrow">1 · Finalistas</div>
  <h2>Quatro divisões, uma cruz</h2>
  <div class="cands">{"".join(cand_card(k) for k in CANDS)}</div>
  <p style="margin-top:14px;font-size:14px;color:var(--ink2)">Em cada cartão: símbolo, avatar 110 px em prata, negativo, monocromático, 40 px e a assinatura horizontal. Todos são vetores, construídos por círculos, curvas e retângulos com parâmetros ajustáveis.</p>
</section>

<section>
  <div class="eyebrow">2 · No perfil</div>
  <h2>Como fica na fileira do Instagram</h2>
  <p class="lead">Avatar em prata, destaques em vermelho profundo, três posts fixados. Recomendação Q2 à esquerda, Q3 à direita.</p>
  <div class="mocks">{profile_mock("Q2")}{profile_mock("Q3")}</div>
</section>

<section>
  <div class="eyebrow">3 · Destaques</div>
  <h2>Seis capas, um traço</h2>
  <p>Ícones desenhados numa grade única de 48 unidades, traço 3,25, cantos e terminações redondos. A Agenda tem quatro células, o livro tem cantos do quadrifólio, "Arquifln" traz a roda de Santa Catarina em quatro arcos com a cruz: a carga do brasão. O filete dourado fino é a única concessão ornamental.</p>
  <div class="light"><div class="cvs">{covers_dark}</div></div>
  <div class="cvs" style="margin-top:18px">{covers_light}</div>
  <p style="font-size:14px;color:var(--ink2);margin-top:8px">Família escura (recomendada) e família clara, para comparação. Arquivos 1080×1920 prontos para subir como capa de destaque.</p>
  <div class="icons">{icons_row}</div>
</section>

<section>
  <div class="eyebrow">4 · Assinaturas</div>
  <h2>Sobre claro e sobre vermelho</h2>
  <div class="lkrow light">{lockup(CANDS["Q2"][2])}{lockup(CANDS["Q2"][2], horizontal=False)}</div>
  <div class="lkrow dark" style="margin-top:14px">{lockup(CANDS["Q2"][2], dark=True)}{lockup(CANDS["Q2"][2], horizontal=False, dark=True)}</div>
</section>

<section style="border-bottom:0">
  <div class="eyebrow">5 · Decisão</div>
  <h2>O que preciso de você</h2>
  <div class="decide"><ol>
    <li><b>Símbolo:</b> Q2, Q3, E1 ou B1? (Recomendo Q2; Q3 se quiser a leitura de metades do símbolo atual.)</li>
    <li><b>Tons:</b> alternados como o escudo (Q2), metades (Q3) ou um vermelho só?</li>
    <li><b>Capas de destaque:</b> família escura ou clara?</li>
    <li>Algum ajuste fino (espessura da cruz, tamanho dos cantos, posição da cruz)? Tudo é paramétrico.</li>
  </ol></div>
</section>
</div>'''
io.open(HERE / "identidade-pastoral-dizimo.html", "w", encoding="utf-8").write(html)
io.open(REPO / "docs" / "marca" / "prancha-identidade.html", "w", encoding="utf-8").write(html)
print("ok", len(html))
