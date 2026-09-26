"""Prévias para aprovação: pacote de estreia (ADR-005) e semanas (fatia 5, ADR-009).

Estreia: página HTML única, autocontida, estilo perfil do Instagram.

Mostra bio, fileira de destaques, grade com os 3 posts fixados e, para cada post, o carrossel
navegável com legenda, alt-text e itens a conferir. Abre com um texto de apoio para o Padre
("O que estamos pedindo para aprovar"). As imagens vão embutidas (data URI): o arquivo pode ser
enviado por e-mail ou aberto direto do disco, sem internet.

Semana (`--semana 2026-W41`): lê content/semanas/<semana>/{posts,briefing}.json e render/, grava
content/semanas/<semana>/agenda.json (data agendada + artes de cada post, lida pelo Worker), copia as
artes para site/midia/<semana>/ (as URLs públicas que publicar.py usa e cujo sha256 vai na aprovação)
e gera site/semanas/<semana>/index.html, que aponta para essas mesmas imagens.

Uso: python -m pastoral.preview  (lê content/estreia/, grava site/estreia/index.html)
     python -m pastoral.preview --semana 2026-W41
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import yaml

from pastoral import aprovacao
from pastoral.render import DESTAQUES

RAIZ = Path(__file__).resolve().parents[2]
ESTREIA = RAIZ / "content" / "estreia"


def e(texto) -> str:
    return escape(str(texto), quote=True)


def ler_bio(caminho: Path) -> dict:
    """Nome proposto e bios (blocos ```text) de content/estreia/bio.md; a 1ª é a principal."""
    md = Path(caminho).read_text(encoding="utf-8")
    nome = re.search(r"Proposta: \*\*(.+?)\*\*", md).group(1)
    blocos = re.findall(r"```text\n(.*?)\n```", md, re.DOTALL)
    return {"nome": nome, "principal": blocos[0], "alternativas": blocos[1:]}


def _destaques(imagens: dict) -> str:
    itens = "".join(
        f'<li><img class="destaque-capa" src="{e(imagens[f"destaque-{d["arquivo"]}.jpg"])}" alt="Capa do destaque {e(d["nome"])}">'
        f'<span>{e(d["nome"])}</span></li>' for d in DESTAQUES)
    return f'<ul class="destaques">{itens}</ul>'


def _grade(posts: list[dict], imagens: dict) -> str:
    pino = ('<svg class="pino" viewBox="0 0 24 24" aria-label="Fixado"><path d="M15 3l6 6-3 1-4 4 1 5-2 2-4-4-5 5-1-1 '
            '5-5-4-4 2-2 5 1 4-4z" fill="#fff" stroke="#0005" stroke-width=".8"/></svg>')
    itens = "".join(
        f'<a class="grade-item" href="#post-{p["numero"]}"><img src="{e(imagens[f"post-{p["numero"]}-01.jpg"])}" '
        f'alt="Post fixado {p["numero"]}: {e(p["titulo"])}">{pino}'
        f'{"<span class=multi>❐</span>" if len(p["slides"]) > 1 else ""}</a>' for p in posts)
    return f'<div class="grade">{itens}</div>'


def _post(post: dict, imagens: dict, usuario: str, qa: dict, rotulo: str | None = None) -> str:
    n = post["numero"]
    rotulo = rotulo or f"Fixado · post {n}"
    total = len(post["slides"])
    slides = "".join(
        f'<img class="slide" src="{e(imagens[f"post-{n}-{i:02d}.jpg"])}" alt="{e(s["alt_text"])}" '
        f'data-alt="{e(s["alt_text"])}" loading="lazy">' for i, s in enumerate(post["slides"], start=1))
    pontos = "".join(f'<button class="ponto" aria-label="Imagem {i}"></button>' for i in range(1, total + 1))
    fontes = "".join(f"<li>{e(f['referencia'])}{' — ' + e(f['edicao']) if f.get('edicao') else ''}</li>"
                     for f in post.get("fontes", []))
    conferir = "".join(f"<li>{e(item)}</li>" for item in post.get("a_conferir", []))
    reprovadas = [q["arquivo"] for q in qa.get("posts", []) if q.get("post") == n and not q["ok"]]
    selo_qa = ("QA automático: todas as imagens aprovadas" if qa and not reprovadas
               else f"QA automático: revisar {', '.join(reprovadas)}" if reprovadas else "")
    return f"""
<article class="post" id="post-{n}" data-total="{total}">
  <header class="post-topo"><span class="mini-avatar"></span><b>{e(usuario.lstrip('@'))}</b>
    <span class="fixado">{e(rotulo)}</span></header>
  <div class="carrossel" tabindex="0" aria-roledescription="carrossel" aria-label="{e(post['titulo'])}">
    <div class="trilho">{slides}</div>
    <button class="anterior" aria-label="Imagem anterior">‹</button>
    <button class="proximo" aria-label="Próxima imagem">›</button>
    <span class="contador">1/{total}</span>
  </div>
  <div class="pontos">{pontos}</div>
  <div class="post-corpo">
    <p class="legenda"><b>{e(usuario.lstrip('@'))}</b> {e(post['legenda'])}</p>
    <details open><summary>Texto alternativo da imagem atual</summary><p class="alt-atual">{e(post['slides'][0]['alt_text'])}</p></details>
    <details><summary>Fontes citadas</summary><ul>{fontes}</ul></details>
    {f'<details open><summary>A conferir antes de publicar</summary><ul>{conferir}</ul></details>' if conferir else ''}
    <p class="meta">{e(post['titulo'])} · {e(post['pilar'])} · CTA: {e(post['cta'])} · {total} imagens{' · ' + e(selo_qa) if selo_qa else ''}</p>
  </div>
</article>"""


def _apoio(dados: dict, bio: dict) -> str:
    alternativas = "".join(f'<li><pre>{e(b)}</pre><small>{len(b)} caracteres</small></li>' for b in bio["alternativas"])
    return f"""
<section class="apoio">
  <h1>Pacote de estreia · Pastoral do Dízimo</h1>
  <p class="aviso">Prévia para aprovação. <b>Nada foi publicado.</b></p>
  <h2>O que estamos pedindo para aprovar</h2>
  <p>Padre, esta página mostra como o perfil ficará na estreia. Pedimos sua aprovação, ou seus ajustes, para três coisas:</p>
  <ol>
    <li><b>Nome e bio do perfil</b> — a proposta aparece no topo do perfil abaixo; há duas alternativas no fim desta seção.</li>
    <li><b>Capas dos 5 destaques</b> — Dízimo, Formação, Agenda, Perguntas e Arquifln. Só ícones, nas cores da Arquidiocese; o nome do destaque aparece no próprio Instagram.</li>
    <li><b>Os 3 posts fixados</b> — (1) apresentação da Pastoral, (2) "O que é o dízimo?" e (3) "Para onde vai o dízimo?". Em cada um: as imagens (use as setas), a legenda e o texto alternativo, que descreve a imagem para quem usa leitor de tela.</li>
  </ol>
  <h3>Pontos que pedem o seu olhar</h3>
  <ul>
    <li>O post 3 apresenta as <b>quatro dimensões</b> (religiosa, eclesial, missionária e caritativa) como síntese pastoral. Elas não são atribuídas ao Documento 106 da CNBB, porque não aparecem juntas no texto do documento.</li>
    <li>O post 2 resume o <b>Documento 106 da CNBB</b> (n. 6, 9, 10 e 12) em palavras nossas; os trechos precisam ser conferidos no exemplar impresso.</li>
    <li>A redação de <b>2Cor 9,7</b> ("Deus ama quem dá com alegria") e a referência a Rm 15,26-27 devem ser conferidas na Bíblia Sagrada — Tradução Oficial da CNBB.</li>
    <li>Nenhum nome de pessoa, valor, número de paróquias ou evento foi usado. Nenhum texto fala em percentual ou pede dinheiro.</li>
  </ul>
  <h3>O que não está neste pacote</h3>
  <ul>
    <li>Foto de perfil: continua a atual. Logotipo novo: adiado.</li>
    <li>Hashtags: nenhuma por enquanto. Data de estreia: ainda não definida.</li>
  </ul>
  <h3>Como responder</h3>
  <p>Basta dizer ao Diogo "aprovado" ou indicar o ajuste pelo número do post e da imagem (por exemplo: "post 2, imagem 4: trocar ...").</p>
  <details><summary>Alternativas de bio</summary><ol class="bios">{alternativas}</ol></details>
</section>"""


CSS = """
:root { --fundo: #fafafa; --cartao: #fff; --texto: #262626; --suave: #737373; --linha: #dbdbdb;
        --vermelho: #A3121C; --prata: #F3F2EE; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--fundo); color: var(--texto);
       font: 15px/1.45 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 16px; }
.apoio { background: var(--cartao); border: 1px solid var(--linha); border-left: 4px solid var(--vermelho);
         border-radius: 8px; padding: 20px 22px; margin-bottom: 28px; }
.apoio h1 { font-size: 22px; margin: 0 0 4px; } .apoio h2 { font-size: 18px; margin: 20px 0 6px; color: var(--vermelho); }
.apoio h3 { font-size: 15px; margin: 18px 0 4px; } .aviso { color: var(--suave); margin: 0; }
.apoio li { margin: 4px 0; } .bios pre { white-space: pre-wrap; font: inherit; background: var(--prata); padding: 8px 10px; border-radius: 6px; margin: 6px 0 0; }
.perfil { background: var(--cartao); border: 1px solid var(--linha); border-radius: 8px; padding: 20px 16px 8px; }
.perfil-topo { display: flex; gap: 22px; align-items: center; }
.avatar { width: 86px; height: 86px; border-radius: 50%; flex: none; background: var(--prata); border: 1px solid var(--linha);
          display: flex; align-items: center; justify-content: center; text-align: center; font-size: 11px; color: var(--suave); padding: 8px; }
.usuario { font-size: 20px; margin: 0 0 4px; } .nome { font-weight: 600; margin: 0; }
.bio { white-space: pre-wrap; margin: 10px 0 0; } .contagem { color: var(--suave); font-size: 12px; }
.destaques { display: flex; gap: 14px; list-style: none; padding: 16px 0 8px; margin: 0; overflow-x: auto; }
.destaques li { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 12px; flex: none; width: 72px; }
.destaque-capa { width: 66px; height: 66px; border-radius: 50%; object-fit: cover; border: 1px solid var(--linha); padding: 2px; background: #fff; }
.grade { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; margin-top: 10px; }
.grade-item { position: relative; aspect-ratio: 3 / 4; overflow: hidden; background: #eee; }
.grade-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pino { position: absolute; top: 6px; right: 6px; width: 18px; height: 18px; }
.multi { position: absolute; top: 4px; left: 6px; color: #fff; font-size: 16px; text-shadow: 0 0 2px #0008; }
.post { background: var(--cartao); border: 1px solid var(--linha); border-radius: 8px; margin: 28px 0; overflow: hidden; scroll-margin-top: 12px; }
.post-topo { display: flex; align-items: center; gap: 10px; padding: 10px 14px; }
.mini-avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--prata); border: 1px solid var(--linha); }
.fixado { margin-left: auto; color: var(--suave); font-size: 13px; }
.carrossel { position: relative; overflow: hidden; background: #000; outline: none; }
.trilho { display: flex; transition: transform .3s ease; }
.slide { width: 100%; flex: none; aspect-ratio: 4 / 5; display: block; }
.carrossel button { position: absolute; top: 50%; transform: translateY(-50%); width: 34px; height: 34px; border-radius: 50%;
                    border: 0; background: #fffe; color: #262626; font-size: 24px; line-height: 1; cursor: pointer; box-shadow: 0 1px 4px #0004; }
.carrossel button:disabled { display: none; } .anterior { left: 10px; } .proximo { right: 10px; }
.contador { position: absolute; top: 12px; right: 12px; background: #000a; color: #fff; font-size: 12px; padding: 3px 9px; border-radius: 12px; }
.pontos { display: flex; justify-content: center; gap: 5px; padding: 10px 0 0; }
.ponto { width: 7px; height: 7px; border-radius: 50%; border: 0; padding: 0; background: #c7c7c7; cursor: pointer; }
.ponto.ativo { background: #0095f6; }
.post-corpo { padding: 6px 14px 14px; } .legenda { white-space: pre-wrap; }
details { margin: 8px 0; } summary { cursor: pointer; color: var(--suave); } .alt-atual { background: var(--prata); padding: 8px 10px; border-radius: 6px; margin: 6px 0; }
.meta { color: var(--suave); font-size: 12px; border-top: 1px solid var(--linha); padding-top: 8px; }
h2.secao { font-size: 16px; margin: 32px 0 0; }
@media (max-width: 520px) { main { padding: 10px; } .perfil-topo { gap: 14px; } .avatar { width: 72px; height: 72px; } }
"""

JS = """
document.querySelectorAll('.post').forEach(post => {
  const total = +post.dataset.total, trilho = post.querySelector('.trilho');
  const slides = post.querySelectorAll('.slide'), pontos = post.querySelectorAll('.ponto');
  const ant = post.querySelector('.anterior'), prox = post.querySelector('.proximo');
  let i = 0;
  const ir = n => {
    i = Math.max(0, Math.min(total - 1, n));
    trilho.style.transform = `translateX(${-100 * i}%)`;
    post.querySelector('.contador').textContent = `${i + 1}/${total}`;
    post.querySelector('.alt-atual').textContent = slides[i].dataset.alt;
    pontos.forEach((p, k) => p.classList.toggle('ativo', k === i));
    ant.disabled = i === 0; prox.disabled = i === total - 1;
  };
  ant.onclick = () => ir(i - 1); prox.onclick = () => ir(i + 1);
  pontos.forEach((p, k) => p.onclick = () => ir(k));
  post.querySelector('.carrossel').addEventListener('keydown', ev => {
    if (ev.key === 'ArrowRight') ir(i + 1); if (ev.key === 'ArrowLeft') ir(i - 1);
  });
  let x0 = null;
  trilho.addEventListener('touchstart', ev => x0 = ev.touches[0].clientX, {passive: true});
  trilho.addEventListener('touchend', ev => {
    if (x0 === null) return; const dx = ev.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) ir(i + (dx < 0 ? 1 : -1));
  });
  ir(0);
});
"""


def montar_pagina(dados: dict, bio: dict, imagens: dict, qa: dict | None = None,
                  usuario: str = "@pastoraldodizimo.arquifln") -> str:
    """HTML completo. `imagens` mapeia nome do arquivo → src (data URI ou caminho)."""
    qa = qa or {}
    posts = "".join(_post(p, imagens, usuario, qa) for p in dados["posts"])
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prévia da estreia</title>
<style>{CSS}</style></head>
<body><main>
{_apoio(dados, bio)}
<section class="perfil" aria-label="Perfil simulado">
  <div class="perfil-topo">
    <div class="avatar">foto atual (mantida)</div>
    <div><p class="usuario">{e(usuario.lstrip('@'))}</p><p class="nome">{e(bio['nome'])}</p></div>
  </div>
  <p class="bio">{e(bio['principal'])}</p>
  <p class="contagem">Bio: {len(bio['principal'])}/150 caracteres</p>
  {_destaques(imagens)}
  {_grade(dados['posts'], imagens)}
</section>
<h2 class="secao">Os 3 posts fixados</h2>
{posts}
</main>
<script>{JS}</script>
</body></html>
"""


DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")


def data_por_extenso(iso: str) -> str:
    """'2026-10-06T19:00:00-03:00' → 'terça-feira, 06/10/2026, 19:00' (hora local do agendamento)."""
    d = datetime.fromisoformat(iso)
    return f"{DIAS[d.weekday()]}, {d:%d/%m/%Y, %H:%M}"


def montar_pagina_semana(semana: str, dados: dict, agenda: dict, imagens: dict, qa: dict | None = None,
                         usuario: str = "@pastoraldodizimo.arquifln") -> str:
    """Prévia da semana: aviso, grade e cada post com carrossel, legenda, alt-text e data agendada."""
    qa = qa or {}
    quando = {p["numero"]: data_por_extenso(p["agendado_para"]) for p in agenda["posts"]}
    ordenados = sorted(dados["posts"], key=lambda p: p["numero"])
    grade = "".join(
        f'<a class="grade-item" href="#post-{p["numero"]}"><img src="{e(imagens[f"post-{p["numero"]}-01.jpg"])}" '
        f'alt="Post {p["numero"]}: {e(p["titulo"])}">'
        f'{"<span class=multi>❐</span>" if len(p["slides"]) > 1 else ""}</a>' for p in ordenados)
    posts = "".join(_post(p, imagens, usuario, qa, f"Post {p['numero']} · {quando[p['numero']]}") for p in ordenados)
    resumo = "".join(f"<li><b>Post {p['numero']}</b> — {e(p['titulo'])} ({e(p['pilar'])}) · {e(quando[p['numero']])}</li>"
                     for p in ordenados)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Prévia da semana {e(semana)}</title>
<style>{CSS}</style></head>
<body><main>
<section class="apoio">
  <h1>Semana {e(semana)} · Pastoral do Dízimo</h1>
  <p class="aviso">Prévia para aprovação. <b>Nada foi publicado.</b></p>
  <ul>{resumo}</ul>
  <p>Para aprovar ou pedir ajuste, use os botões do e-mail desta semana. Só o que aparece aqui
  (textos e imagens exatamente como estão) pode ser publicado, e só depois da aprovação.</p>
</section>
<section class="perfil" aria-label="Posts da semana">{f'<div class="grade">{grade}</div>'}</section>
{posts}
</main>
<script>{JS}</script>
</body></html>
"""


def gerar_semana(raiz: Path, semana: str, usuario: str = "@pastoraldodizimo.arquifln") -> Path:
    """Grava agenda.json, copia as artes para site/midia/<semana>/ e gera site/semanas/<semana>/index.html."""
    raiz = Path(raiz)
    pasta = raiz / "content" / "semanas" / semana
    dados = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
    briefing = json.loads((pasta / "briefing.json").read_text(encoding="utf-8"))
    render = pasta / "render"
    qa_arq = render / "qa.json"
    qa = json.loads(qa_arq.read_text(encoding="utf-8")) if qa_arq.exists() else {}

    agenda = aprovacao.montar_agenda(semana, dados, briefing)
    artes = [a for p in agenda["posts"] for a in p["artes"]]
    faltando = [a for a in artes if not (render / a).is_file()]
    if faltando:
        raise FileNotFoundError(f"artes não renderizadas em {render}: {', '.join(faltando)}")

    midia = raiz / "site" / "midia" / semana
    midia.mkdir(parents=True, exist_ok=True)
    for velho in midia.glob("*.jpg"):          # arte de versão anterior (ex.: post refeito com menos slides)
        if velho.name not in artes:
            velho.unlink()
    for a in artes:
        shutil.copyfile(render / a, midia / a)
    (pasta / "agenda.json").write_text(json.dumps(agenda, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")

    imagens = {a: f"../../midia/{semana}/{a}" for a in artes}
    saida = raiz / "site" / "semanas" / semana / "index.html"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(montar_pagina_semana(semana, dados, agenda, imagens, qa, usuario), encoding="utf-8")
    return saida


def _data_uri(caminho: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(caminho.read_bytes()).decode("ascii")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gera a prévia do pacote de estreia ou de uma semana")
    ap.add_argument("--semana", help="AAAA-Www: prévia semanal em site/semanas/ (em vez da estreia)")
    ap.add_argument("--raiz", type=Path, default=RAIZ, help="raiz do repositório (testes)")
    ap.add_argument("--posts", type=Path, default=ESTREIA / "posts.json")
    ap.add_argument("--render", type=Path, default=ESTREIA / "render")
    ap.add_argument("--bio", type=Path, default=ESTREIA / "bio.md")
    ap.add_argument("--saida", type=Path, default=RAIZ / "site" / "estreia" / "index.html")
    args = ap.parse_args(argv)

    usuario = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))["marca"]["usuario"]
    if args.semana:
        saida = gerar_semana(args.raiz, args.semana, usuario)
        print(f"{saida} + site/midia/{args.semana}/ + agenda.json")
        return 0

    dados = json.loads(args.posts.read_text(encoding="utf-8"))
    qa_arq = args.render / "qa.json"
    qa = json.loads(qa_arq.read_text(encoding="utf-8")) if qa_arq.exists() else {}
    imagens = {f.name: _data_uri(f) for f in sorted(args.render.glob("*.jpg"))}
    pagina = montar_pagina(dados, ler_bio(args.bio), imagens, qa, usuario)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(pagina, encoding="utf-8")
    print(f"{args.saida} ({args.saida.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
