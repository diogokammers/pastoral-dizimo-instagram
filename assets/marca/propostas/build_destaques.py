# -*- coding: utf-8 -*-
"""Capas de destaque: ícones numa grade 48x48, traço 3.25, cantos redondos.
Saída: SVG 1080x1920 (Story) com círculo central de 1080 e prévia."""
import io, pathlib, math
from build_logo3 import RED, DEEP, PRATA, GOLD
from build_logo6 import Q
OUT = pathlib.Path(__file__).parent
SW = 3.25
A = f'fill="none" stroke="currentColor" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"'

ICONS = {
 # Dízimo: o próprio símbolo (versão em um tom), inserido por <use>
 "dizimo": None,
 # Formação: livro aberto — duas páginas com canto externo arredondado (eco do quadrifólio), lombada = vão
 "formacao": f'''<g {A}>
   <path d="M 22.5,13 H 11 A 3,3 0 0 0 8,16 V 35 A 3,3 0 0 0 11,38 H 22.5 Z"/>
   <path d="M 25.5,13 H 37 A 3,3 0 0 1 40,16 V 35 A 3,3 0 0 1 37,38 H 25.5 Z"/>
   <path d="M 13,20 H 18 M 13,25 H 18 M 30,20 H 35 M 30,25 H 35"/>
 </g>''',
 # Agenda: calendário com quatro células (a cruz divide)
 "agenda": f'''<g {A}>
   <rect x="8" y="11" width="32" height="29" rx="4"/>
   <path d="M 16,7 V 14 M 32,7 V 14 M 8,19 H 40"/>
   <path d="M 24,19 V 40 M 8,29.5 H 40"/>
 </g>''',
 # Paróquias: igreja — nave com empena, torre com cruz, porta em arco
 "paroquias": f'''<g {A}>
   <path d="M 9,41 V 26 L 24,15 L 39,26 V 41 Z"/>
   <path d="M 20,41 V 33 A 4,4 0 0 1 28,33 V 41"/>
   <path d="M 24,15 V 6 M 20.5,9.5 H 27.5"/>
   <path d="M 4,41 H 44"/>
 </g>''',
 # Perguntas: balão arredondado com ponto de interrogação
 "perguntas": f'''<g {A}>
   <path d="M 24,8 C 14.6,8 8,14.2 8,22.2 C 8,26.9 10.4,31 14.3,33.6 L 13,41 L 20.6,36.9 C 21.7,37.1 22.8,37.2 24,37.2 C 33.4,37.2 40,31 40,22.2 C 40,14.2 33.4,8 24,8 Z"/>
   <path d="M 19.5,19.2 A 4.5,4.5 0 1 1 26,23.1 C 24.6,23.9 24,24.9 24,26.6"/>
   <circle cx="24" cy="31" r="0.6" fill="currentColor"/>
 </g>''',
 # Arquifln: roda de Santa Catarina em quatro arcos e cruz — a carga do brasão
 "arquifln": f'''<g {A}>
   {"".join(f'<path d="M {24+15*math.cos(math.radians(a-27)):.2f},{24+15*math.sin(math.radians(a-27)):.2f} A 15,15 0 0 1 {24+15*math.cos(math.radians(a+27)):.2f},{24+15*math.sin(math.radians(a+27)):.2f}"/>' for a in (45,135,225,315))}
   <path d="M 24,10 V 38 M 10,24 H 38"/>
 </g>''',
}
LABELS = {"dizimo":"Dízimo","formacao":"Formação","agenda":"Agenda","paroquias":"Paróquias","perguntas":"Perguntas","arquifln":"Arquifln"}

def icon_svg(name, size=48, color=PRATA):
    if name == "dizimo":
        mode = "prata" if color.upper() == PRATA.upper() else "flat"
        return Q(mode=mode, size=size, uid="dz"+str(size)).replace('viewBox="0 0 200 200"', 'viewBox="-10 -6 220 220"')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="{size}" height="{size}" style="color:{color}">{ICONS[name]}</svg>'

def cover_svg(name, bg=DEEP, fg=PRATA, ring=True, ringcolor=None):
    """1080x1920; círculo útil de 1080 centrado em y=960; ícone ocupa ~40% do diâmetro."""
    inner = icon_svg(name, size=440, color=fg).replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg')
    ringel = f'<circle cx="540" cy="960" r="470" fill="none" stroke="{ringcolor or GOLD}" stroke-width="3" opacity=".9"/>' if ring else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">'
            f'<rect x="0" y="0" width="100%" height="100%" fill="{bg}"/>{ringel}'
            f'<g transform="translate({540-220},{960-220})">{inner}</g></svg>')

if __name__ == "__main__":
    for n in ICONS:
        io.open(OUT/f"capa-{n}.svg","w",encoding="utf-8").write(cover_svg(n))
    print("ok")
