"""Simulador do perfil no Instagram para o Padre ver e aprovar tudo de uma vez.

Gera site/aprovacao/index.html: uma página que imita o app do Instagram (celular, tema claro) com o
perfil @pastoraldodizimo.arquifln, os destaques e TODAS as publicações — as 3 da estreia (já
publicadas e fixadas, com a legenda simples proposta em docs/auditoria/) e as da reserva
(content/semanas/*/, datas provisórias de agenda.json). Tocar num post abre o feed, com carrossel
deslizável. No "Modo aprovação", cada post ganha "Aprovar" / "Pedir ajuste"; as respostas ficam no
aparelho (localStorage) e o botão "Enviar minhas respostas" monta um resumo para WhatsApp, e-mail
ou copiar. Nenhum servidor: é uma página estática no GitHub Pages.

As imagens são arquivos relativos em site/midia/ (não base64), para carregar rápido no celular:
a estreia e os destaques são copiados para site/midia/estreia/ e site/midia/destaques/; as artes
das semanas já estão em site/midia/<semana>/ (copiadas por preview.py --semana).

Uso: python -m pastoral.simulador   (com PYTHONPATH=src)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

from pastoral.preview import data_por_extenso
from pastoral.publicar import texto_legenda
from pastoral.render import DESTAQUES

RAIZ = Path(__file__).resolve().parents[2]
LEGENDAS_SIMPLES = "docs/auditoria/2026-09-27-legendas-simples-estreia.md"
SEGUIDORES = 73
SEGUINDO = 2
LIMITE_LEGENDA = 90          # caracteres visíveis antes do "… mais", como no app
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro")


def e(texto) -> str:
    return escape(str(texto), quote=True)


# ---------------------------------------------------------------- dados

def ler_bio_aplicada(caminho: Path) -> str:
    """Bloco ```text aplicada de content/estreia/bio.md (a bio que está no ar)."""
    md = Path(caminho).read_text(encoding="utf-8")
    return re.search(r"```text aplicada\n(.*?)\n```", md, re.DOTALL).group(1)


def ler_nome(caminho: Path) -> str:
    md = Path(caminho).read_text(encoding="utf-8")
    return re.search(r"Nome do perfil aplicado: \*\*(.+?)\*\*", md).group(1)


def ler_legendas_simples(caminho: Path) -> dict[int, str]:
    """{número do post: legenda simples proposta} a partir das seções "## Post N"."""
    md = Path(caminho).read_text(encoding="utf-8")
    return {int(n): t for n, t in re.findall(r"^## Post (\d+).*?```text\n(.*?)\n```", md, re.DOTALL | re.MULTILINE)}


def _slides(post: dict, srcs: list[str]) -> list[dict]:
    if len(srcs) != len(post["slides"]):
        raise ValueError(f"post {post['numero']}: {len(srcs)} artes para {len(post['slides'])} slides")
    return [{"src": s, "alt": sl["alt_text"]} for s, sl in zip(srcs, post["slides"])]


def coletar(raiz: Path) -> dict:
    """Junta perfil, destaques e posts (já na ordem da grade) a partir do repositório."""
    raiz = Path(raiz)
    estreia = raiz / "content" / "estreia"
    bio_md = estreia / "bio.md"
    publicado = json.loads((estreia / "publicado.json").read_text(encoding="utf-8"))
    data_estreia = publicado.get("republicado_em") or publicado["publicado_em"]
    simples = ler_legendas_simples(raiz / LEGENDAS_SIMPLES)

    posts = []
    for p in json.loads((estreia / "posts.json").read_text(encoding="utf-8"))["posts"]:
        n = p["numero"]
        srcs = [f"../midia/estreia/post-{n}-{i:02d}.jpg" for i in range(1, len(p["slides"]) + 1)]
        posts.append({"numero": n, "titulo": p["titulo"], "pilar": p["pilar"], "semana": "estreia",
                      "data": data_estreia, "publicado": True, "fixado": True,
                      "legenda": simples.get(n, texto_legenda(p)), "legenda_proposta": n in simples,
                      "imagens": _slides(p, srcs)})

    for agenda_arq in sorted((raiz / "content" / "semanas").glob("*/agenda.json")):
        semana = agenda_arq.parent.name
        agenda = json.loads(agenda_arq.read_text(encoding="utf-8"))
        lote = json.loads((agenda_arq.parent / "posts.json").read_text(encoding="utf-8"))
        por_numero = {p["numero"]: p for p in lote["posts"]}
        for a in agenda["posts"]:
            p = por_numero[a["numero"]]
            srcs = [f"../midia/{semana}/{arte}" for arte in a["artes"]]
            posts.append({"numero": p["numero"], "titulo": p["titulo"], "pilar": p["pilar"], "semana": semana,
                          "data": a["agendado_para"], "publicado": False, "fixado": False,
                          "legenda": texto_legenda(p), "legenda_proposta": False,
                          "imagens": _slides(p, srcs)})

    # grade: fixados na ordem 1|2|3; depois do mais recente para o mais antigo
    fixados = sorted((p for p in posts if p["fixado"]), key=lambda p: p["numero"])
    outros = sorted((p for p in posts if not p["fixado"]), key=lambda p: (p["data"], p["numero"]), reverse=True)
    return {
        "perfil": {"usuario": "pastoraldodizimo.arquifln", "nome": ler_nome(bio_md),
                   "bio": ler_bio_aplicada(bio_md), "avatar": "../midia/perfil/avatar.jpg",
                   "seguidores": SEGUIDORES, "seguindo": SEGUINDO},
        "destaques": [{"nome": d["nome"], "capa": f"../midia/destaques/destaque-{d['arquivo']}.jpg"}
                      for d in DESTAQUES],
        "posts": fixados + outros,
    }


# ---------------------------------------------------------------- texto

def resumir_legenda(texto: str, limite: int = LIMITE_LEGENDA) -> tuple[str, str]:
    """(parte visível, resto) — o app corta na 1ª quebra de linha ou em ~2 linhas, num espaço."""
    texto = texto.strip()
    primeira = texto.split("\n", 1)[0].strip()
    if len(primeira) > limite:
        corte = primeira.rfind(" ", 0, limite)
        primeira = primeira[:corte if corte > 0 else limite]
    primeira = primeira.rstrip(" ,;:.…") if primeira != texto else primeira
    if primeira == texto:
        return texto, ""
    return primeira, texto


def marcar(texto: str) -> str:
    """Escapa e pinta @menções e #hashtags de azul, como no app."""
    return re.sub(r"([@#][\w.]*\w)", r'<span class="mencao">\1</span>', e(texto))


def data_curta(iso: str) -> str:
    """'2026-10-16T19:00:00-03:00' → '16 de outubro' (como o app mostra sob o post)."""
    d = datetime.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]}"


# ---------------------------------------------------------------- ícones (traço, como no app)

def _svg(corpo: str, rotulo: str | None = None, classe: str = "ico", preenchido: bool = False) -> str:
    aria = f'role="img" aria-label="{e(rotulo)}"' if rotulo else 'aria-hidden="true"'
    estilo = 'fill="currentColor" stroke="none"' if preenchido else \
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    return f'<svg class="{classe}" viewBox="0 0 24 24" {aria} {estilo}>{corpo}</svg>'


ICO = {
    "voltar": '<path d="M15 5l-7 7 7 7"/>',
    "sino": '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "mais": '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    "curtir": '<path d="M12 20s-7.5-4.6-9.2-9.3C1.7 7.4 3.9 4.5 7 4.5c2 0 3.4 1.1 5 3 1.6-1.9 3-3 5-3 3.1 0 5.3 2.9 4.2 6.2C19.5 15.4 12 20 12 20z"/>',
    "comentar": '<path d="M20.5 12a8.5 8.5 0 1 1-4-7.2 8.5 8.5 0 0 1 3 11.4L21 21l-4.8-1.4"/>',
    "compartilhar": '<path d="M22 3L9.2 10.2"/><path d="M22 3l-7 18-4-8.6L3 9z"/>',
    "salvar": '<path d="M19 21l-7-5-7 5V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1z"/>',
    "grade": '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>',
    "reels": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M3 8h18M8.5 3l3 5M14 3l3 5"/><path d="M10 11.5v5l4.5-2.5z"/>',
    "marcados": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="12" cy="10" r="3"/><path d="M6.5 21a6 6 0 0 1 11 0"/>',
    "add_pessoa": '<circle cx="10" cy="8" r="4"/><path d="M3 20a7 7 0 0 1 14 0M19 8v6M16 11h6"/>',
    "seta_d": '<path d="M9 5l7 7-7 7"/>',
    "seta_e": '<path d="M15 5l-7 7 7 7"/>',
}
# ícones cheios, em branco sobre a miniatura (carrossel e alfinete de fixado)
CARROSSEL = ('<svg class="ico-carrossel" viewBox="0 0 24 24" role="img" aria-label="Várias imagens">'
             '<path d="M7 3h11a3 3 0 0 1 3 3v11h-2V6a1 1 0 0 0-1-1H7z" fill="#fff"/>'
             '<rect x="3" y="7" width="14" height="14" rx="2.5" fill="#fff"/></svg>')
ALFINETE = ('<svg class="ico-fixado" viewBox="0 0 24 24" role="img" aria-label="Fixado">'
            '<path d="M16 3l5 5-2 1-3.5 3.5.5 4.5-2 2-3.8-3.8L5 20.4 3.6 19l5.2-5.2L5 10l2-2 4.5.5L15 5z" '
            'fill="#fff"/></svg>')


# ---------------------------------------------------------------- HTML

def _cabecalho_perfil(perfil: dict, total: int) -> str:
    linhas = perfil["bio"].split("\n")
    visivel = "\n".join(linhas[:2])
    resto = "\n".join(linhas[2:])
    bio = f'<span class="bio-visivel">{marcar(visivel)}</span>'
    if resto:
        bio += (f'<span class="bio-resto" hidden>\n{marcar(resto)}</span>'
                f'<button class="link-mais" data-expande="bio">… mais</button>')
    return f"""
<header class="topo">
  <span class="topo-esq">{_svg(ICO["voltar"], "Voltar")}</span>
  <h1 class="topo-usuario">{e(perfil["usuario"])}</h1>
  <span class="topo-dir">{_svg(ICO["sino"], "Notificações")}{_svg(ICO["mais"], "Opções")}</span>
</header>
<section class="perfil">
  <div class="perfil-linha">
    <img class="avatar" src="{e(perfil["avatar"])}" alt="Foto de perfil de {e(perfil["usuario"])}" width="86" height="86">
    <div class="perfil-dir">
      <p class="perfil-nome">{e(perfil["nome"])}</p>
      <ul class="contadores">
        <li><b>{total}</b> <span>publicações</span></li>
        <li><b>{perfil["seguidores"]}</b> <span>seguidores</span></li>
        <li><b>{perfil["seguindo"]}</b> <span>seguindo</span></li>
      </ul>
    </div>
  </div>
  <p class="bio">{bio}</p>
  <div class="acoes">
    <button class="btn btn-azul" disabled title="Desativado na simulação">Seguir</button>
    <button class="btn" disabled title="Desativado na simulação">Mensagem</button>
    <button class="btn btn-ico" disabled aria-label="Sugestões de contas">{_svg(ICO["add_pessoa"])}</button>
  </div>
</section>"""


def _destaques(destaques: list[dict]) -> str:
    itens = "".join(
        f'<li><span class="destaque-anel"><img src="{e(d["capa"])}" alt="" loading="lazy"></span>'
        f'<span class="destaque-nome">{e(d["nome"])}</span></li>' for d in destaques)
    return f'<ul class="destaques" aria-label="Destaques">{itens}</ul>'


def _grade(posts: list[dict]) -> str:
    itens = []
    for i, p in enumerate(posts):
        icones = (ALFINETE if p["fixado"] else "") + (CARROSSEL if len(p["imagens"]) > 1 else "")
        carrega = "eager" if i < 6 else "lazy"
        itens.append(
            f'<button class="grade-item" data-n="{p["numero"]}" aria-label="Abrir publicação {p["numero"]}: {e(p["titulo"])}">'
            f'<img src="{e(p["imagens"][0]["src"])}" alt="{e(p["imagens"][0]["alt"])}" loading="{carrega}">'
            f'<span class="grade-icones">{icones}</span><span class="selo" aria-hidden="true"></span></button>')
    return f"""
<nav class="abas" aria-label="Abas do perfil">
  <span class="aba ativa" aria-current="page">{_svg(ICO["grade"], "Publicações")}</span>
  <span class="aba">{_svg(ICO["reels"], "Reels")}</span>
  <span class="aba">{_svg(ICO["marcados"], "Marcados")}</span>
</nav>
<div class="grade">{"".join(itens)}</div>"""


def _post(p: dict, usuario: str, avatar: str) -> str:
    n = p["numero"]
    total = len(p["imagens"])
    slides = "".join(
        f'<li class="slide"><img src="{e(img["src"])}" alt="{e(img["alt"])}" loading="lazy" '
        f'width="1080" height="1350"></li>' for img in p["imagens"])
    if total > 1:
        navega = (f'<span class="contador" aria-live="polite">1/{total}</span>'
                  f'<button class="seta seta-e" aria-label="Imagem anterior" hidden>{_svg(ICO["seta_e"])}</button>'
                  f'<button class="seta seta-d" aria-label="Próxima imagem">{_svg(ICO["seta_d"])}</button>')
        pontos = '<span class="pontos" aria-hidden="true">' + "".join(
            f'<i{" class=on" if i == 0 else ""}></i>' for i in range(total)) + "</span>"
    else:
        navega = pontos = ""
    visivel, completo = resumir_legenda(p["legenda"])
    if completo:
        legenda = (f'<span class="leg-curta">{marcar(visivel)}… <button class="link-mais" data-expande="leg">mais</button></span>'
                   f'<span class="leg-completa" hidden>{marcar(completo)}</span>')
    else:
        legenda = marcar(visivel)
    if p["publicado"]:
        quando = f"Publicado em {data_por_extenso(p['data'])}"
    else:
        quando = f"Data prevista: {data_por_extenso(p['data'])} (provisória)"
    proposta = ('<p class="aprov-nota">legenda proposta — nova versão simples (a publicada hoje é a anterior; '
                'a imagem não muda)</p>' if p["legenda_proposta"] else "")
    return f"""
<article class="post" id="post-{n}" data-n="{n}" data-titulo="{e(p["titulo"])}" aria-label="Publicação {n}">
  <header class="post-topo">
    <img class="avatar-mini" src="{e(avatar)}" alt="" width="32" height="32">
    <b>{e(usuario)}</b>
    <span class="post-opcoes">{_svg(ICO["mais"], "Opções")}</span>
  </header>
  <div class="carrossel" data-total="{total}">
    <ul class="trilho" tabindex="0" aria-label="Imagens da publicação {n}{f', {total} imagens' if total > 1 else ''}">{slides}</ul>
    {navega}
  </div>
  <div class="post-acoes">
    <button class="acao" aria-label="Curtir">{_svg(ICO["curtir"])}</button>
    <button class="acao" aria-label="Comentar">{_svg(ICO["comentar"])}</button>
    <button class="acao" aria-label="Compartilhar">{_svg(ICO["compartilhar"])}</button>
    {pontos}
    <button class="acao acao-salvar" aria-label="Salvar">{_svg(ICO["salvar"])}</button>
  </div>
  <p class="legenda"><b>{e(usuario)}</b> {legenda}</p>
  <p class="post-data">{data_curta(p["data"])}</p>
  <section class="aprov" aria-label="Aprovação da publicação {n}">
    <p class="aprov-titulo"><b>Publicação {n}</b> · {e(p["pilar"])}</p>
    <p class="aprov-tema">{e(p["titulo"])}</p>
    <p class="aprov-data">{e(quando)}</p>
    {proposta}
    <div class="aprov-botoes" role="group" aria-label="Sua resposta para a publicação {n}">
      <button class="btn-aprovar" aria-pressed="false">Aprovar</button>
      <button class="btn-ajuste" aria-pressed="false">Pedir ajuste</button>
    </div>
    <label class="aprov-campo" hidden>O que ajustar?
      <textarea rows="3" placeholder="Escreva aqui o que mudar (texto, imagem, data…)"></textarea>
    </label>
  </section>
</article>"""


def montar_pagina(dados: dict) -> str:
    perfil, posts = dados["perfil"], dados["posts"]
    feed = "".join(_post(p, perfil["usuario"], perfil["avatar"]) for p in posts)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#ffffff">
<title>Instagram da Pastoral — aprovação</title>
<style>{CSS}</style></head>
<body class="modo-insta">
<div class="palco">
<div class="faixa" role="note">
  <p><b>Simulação para aprovação — nada disso foi publicado ainda, exceto os 3 posts fixados.</b></p>
  <details><summary>Como usar</summary>
    <ol>
      <li>Esta é uma imitação do Instagram da Pastoral, como ele vai ficar no fim de outubro.</li>
      <li>Toque numa publicação para abri-la. Deslize a imagem para o lado para ver as outras.</li>
      <li>Toque em <b>Modo aprovação</b>. Em cada publicação, toque em <b>Aprovar</b> ou em <b>Pedir ajuste</b> (e escreva o que mudar).</li>
      <li>No fim, toque em <b>Enviar minhas respostas</b> e mande pelo WhatsApp ou por e-mail.</li>
    </ol>
    <p>Suas respostas ficam guardadas neste aparelho; pode parar e continuar depois.</p>
  </details>
  <div class="modos" role="group" aria-label="Modo de visualização">
    <button id="modo-insta" aria-pressed="true">Ver como no Instagram</button>
    <button id="modo-aprov" aria-pressed="false">Modo aprovação</button>
  </div>
  <button id="enviar" class="enviar" hidden>Enviar minhas respostas</button>
</div>
<div class="celular">
  <div class="tela" id="tela">
    <div id="tela-perfil">
      {_cabecalho_perfil(perfil, len(posts))}
      {_destaques(dados["destaques"])}
      {_grade(posts)}
      <p class="rodape">Simulação feita pela Pastoral do Dízimo · datas provisórias</p>
    </div>
    <div id="tela-feed" hidden>
      <header class="topo">
        <button class="topo-esq" id="voltar" aria-label="Voltar para o perfil">{_svg(ICO["voltar"])}</button>
        <h2 class="topo-feed"><small>{e(perfil["usuario"])}</small>Publicações</h2>
        <span class="topo-dir"></span>
      </header>
      {feed}
    </div>
  </div>
</div>
</div>
<dialog id="dialogo" aria-labelledby="dialogo-titulo">
  <h2 id="dialogo-titulo">Suas respostas</h2>
  <p id="dialogo-contagem"></p>
  <textarea id="resumo" rows="10" readonly aria-label="Texto do resumo"></textarea>
  <div class="dialogo-botoes">
    <a id="por-whatsapp" class="btn btn-verde" target="_blank" rel="noopener" autofocus>Enviar pelo WhatsApp</a>
    <button id="copiar" class="btn">Copiar texto</button>
    <a id="por-email" class="btn">Enviar por e-mail</a>
    <button id="fechar" class="btn">Fechar</button>
  </div>
  <p id="copiado" class="copiado" aria-live="polite"></p>
</dialog>
<script>{JS}</script>
</body></html>
"""


CSS = """
:root { --texto:#000; --suave:#737373; --linha:#dbdbdb; --fundo:#fff; --cinza:#efefef; --azul:#0095f6;
  --mencao:#00376b; --foco:#0064e0; --verde:#1c8c4a; --ajuste:#b45309; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: #fff; color: var(--texto);
  font: 14px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
button:disabled { cursor: default; }
:focus-visible { outline: 3px solid var(--foco); outline-offset: 2px; }
[hidden] { display: none !important; }
.ico { width: 24px; height: 24px; display: block; }

/* faixa de aviso, fora do "app" */
.faixa { max-width: 430px; margin: 0 auto; padding: 10px 16px 12px; background: #fff8e6;
  border-bottom: 1px solid #f0dca8; font-size: 14px; color: #3d2e00; }
.faixa p { margin: 0 0 4px; }
.faixa details { margin: 4px 0 8px; }
.faixa summary { cursor: pointer; color: #6b4e00; text-decoration: underline; }
.faixa ol { margin: 6px 0; padding-left: 20px; } .faixa li { margin: 3px 0; }
.modos { display: flex; gap: 6px; }
.modos button { flex: 1; padding: 9px 6px; border-radius: 8px; background: #fff; border: 1px solid #d9c38a;
  font-weight: 600; font-size: 13px; }
.modos button[aria-pressed="true"] { background: #3d2e00; color: #fff; border-color: #3d2e00; }

/* o "celular" */
.celular { max-width: 430px; margin: 0 auto; background: var(--fundo); }
.tela { position: relative; background: var(--fundo); padding-bottom: 80px; }
/* no computador: moldura de celular com rolagem própria; acima de 1000px, faixa ao lado */
@media (min-width: 700px) {
  body { background: #e9e9ee; padding: 20px 0; }
  .faixa { border: 1px solid #f0dca8; border-radius: 12px; margin-bottom: 16px; }
  .celular { width: 414px; height: max(560px, min(860px, calc(100vh - 220px))); border: 12px solid #111;
    border-radius: 48px; overflow: hidden; box-shadow: 0 20px 60px #0003; }
  .tela { height: 100%; overflow-y: auto; scrollbar-width: none; }
  .tela::-webkit-scrollbar { display: none; }
}
@media (min-width: 1000px) {
  .palco { display: flex; justify-content: center; align-items: flex-start; gap: 32px; }
  .faixa { width: 320px; margin: 0; padding: 16px; position: sticky; top: 20px; }
  .celular { margin: 0; height: max(560px, min(860px, calc(100vh - 40px))); }
  .faixa .enviar { position: static; transform: none; width: 100%; margin-top: 14px; }
}

.topo { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; height: 48px;
  padding: 0 12px; background: #fff; }
.topo-esq { width: 56px; display: flex; }
.topo-dir { width: 56px; display: flex; gap: 18px; justify-content: flex-end; }
.topo-usuario { flex: 1; margin: 0; font-size: 18px; font-weight: 700; text-align: center;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.topo-feed { flex: 1; margin: 0; text-align: center; font-size: 16px; font-weight: 700; line-height: 1.1; }
.topo-feed small { display: block; font-size: 12px; font-weight: 600; color: var(--suave); text-transform: uppercase; }

.perfil { padding: 4px 16px 0; }
.perfil-linha { display: flex; align-items: center; gap: 20px; }
.avatar { width: 86px; height: 86px; border-radius: 50%; object-fit: cover; border: 1px solid var(--linha); flex: none; }
.perfil-dir { flex: 1; min-width: 0; }
.perfil-nome { margin: 0 0 6px; font-weight: 600; font-size: 15px; }
.contadores { list-style: none; margin: 0; padding: 0; display: flex; gap: 18px; }
.contadores li { display: flex; flex-direction: column; line-height: 1.2; }
.contadores b { font-size: 16px; } .contadores span { font-size: 13px; }
.bio { margin: 10px 0 0; white-space: pre-line; font-size: 14px; }
.mencao { color: var(--mencao); }
.link-mais { color: var(--suave); }
.acoes { display: flex; gap: 6px; margin: 12px 0 4px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 34px; padding: 0 14px;
  border-radius: 8px; background: var(--cinza); font-weight: 600; font-size: 14px; color: #000; text-decoration: none; }
.acoes .btn { flex: 1; } .acoes .btn-ico { flex: 0 0 38px; padding: 0; }
.acoes .ico { width: 18px; height: 18px; }
.btn-azul { background: var(--azul); color: #fff; }
.acoes .btn:disabled { opacity: 1; }

.destaques { list-style: none; display: flex; gap: 14px; overflow-x: auto; padding: 12px 16px 10px; margin: 0;
  scrollbar-width: none; }
.destaques::-webkit-scrollbar { display: none; }
.destaques li { flex: none; width: 66px; text-align: center; }
.destaque-anel { display: block; width: 66px; height: 66px; border-radius: 50%; border: 1px solid var(--linha); padding: 3px; }
.destaque-anel img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: block; }
.destaque-nome { display: block; margin-top: 5px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.abas { display: flex; border-top: 1px solid var(--linha); }
.aba { flex: 1; display: flex; justify-content: center; padding: 10px 0; color: #a8a8a8; border-bottom: 1px solid transparent; }
.aba.ativa { color: #000; border-bottom: 1px solid #000; }
.grade { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
.grade-item { position: relative; display: block; aspect-ratio: 4 / 5; overflow: hidden; background: var(--cinza); }
.grade-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
.grade-icones { position: absolute; top: 6px; right: 6px; display: flex; gap: 4px; }
.ico-carrossel, .ico-fixado { width: 20px; height: 20px; filter: drop-shadow(0 0 2px #0008); }
.selo { position: absolute; left: 6px; bottom: 6px; }
.rodape { color: var(--suave); font-size: 12px; text-align: center; padding: 18px 16px; margin: 0; }

/* feed */
.post { border-bottom: 1px solid var(--linha); padding-bottom: 12px; scroll-margin-top: 48px; }
.aprov { scroll-margin-top: 60px; scroll-margin-bottom: 90px; }
.post-topo { display: flex; align-items: center; gap: 10px; padding: 8px 12px; }
.avatar-mini { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; border: 1px solid var(--linha); }
.post-opcoes { margin-left: auto; }
.carrossel { position: relative; }
.trilho { list-style: none; margin: 0; padding: 0; display: flex; overflow-x: auto; scroll-snap-type: x mandatory;
  scroll-behavior: smooth; scrollbar-width: none; aspect-ratio: 4 / 5; background: var(--cinza); }
.trilho::-webkit-scrollbar { display: none; }
.slide { flex: 0 0 100%; scroll-snap-align: start; scroll-snap-stop: always; }
.slide img { width: 100%; height: 100%; object-fit: cover; display: block; }
.contador { position: absolute; top: 12px; right: 12px; background: #121212b3; color: #fff; font-size: 12px;
  font-weight: 600; padding: 3px 8px; border-radius: 12px; }
.seta { position: absolute; top: 50%; transform: translateY(-50%); width: 30px; height: 30px; border-radius: 50%;
  background: #ffffffe6; color: #262626; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 4px #0004; }
.seta .ico { width: 18px; height: 18px; }
.seta-e { left: 10px; } .seta-d { right: 10px; }
@media (hover: none) and (pointer: coarse) { .seta { display: none; } }
.post-acoes { position: relative; display: flex; align-items: center; gap: 14px; padding: 8px 12px 4px; }
.acao-salvar { margin-left: auto; }
.pontos { position: absolute; left: 50%; transform: translateX(-50%); display: flex; gap: 4px; }
.pontos i { width: 6px; height: 6px; border-radius: 50%; background: #c7c7c7; }
.pontos i.on { background: var(--azul); }
.legenda { margin: 4px 12px 0; white-space: pre-line; overflow-wrap: anywhere; }
.post-data { margin: 6px 12px 0; color: var(--suave); font-size: 12px; }

/* aprovação */
.aprov { display: none; margin: 12px 12px 4px; padding: 12px; border: 2px solid #d9c38a; border-radius: 12px; background: #fffbf0; }
.modo-aprov .aprov { display: block; }
.aprov p { margin: 0 0 4px; }
.aprov-tema { font-weight: 600; }
.aprov-data { color: #4d4d4d; font-size: 13px; }
.aprov-nota { font-size: 12px; font-style: italic; color: #4d4d4d; }
.aprov-botoes { display: flex; gap: 8px; margin-top: 10px; }
.aprov-botoes button { flex: 1; min-height: 44px; border-radius: 8px; border: 2px solid #bbb; background: #fff; font-weight: 700; }
.btn-aprovar[aria-pressed="true"] { background: var(--verde); border-color: var(--verde); color: #fff; }
.btn-ajuste[aria-pressed="true"] { background: var(--ajuste); border-color: var(--ajuste); color: #fff; }
.aprov-campo { display: block; margin-top: 10px; font-weight: 600; font-size: 13px; }
.aprov-campo textarea { display: block; width: 100%; margin-top: 4px; font: inherit; font-weight: 400; font-size: 16px;
  padding: 8px; border: 1px solid #999; border-radius: 8px; }
.modo-aprov .grade-item[data-estado] .selo { width: 22px; height: 22px; border-radius: 50%; color: #fff; font-weight: 700;
  font-size: 13px; line-height: 22px; text-align: center; box-shadow: 0 0 0 2px #fff; }
.modo-aprov .grade-item[data-estado="aprovado"] .selo { background: var(--verde); }
.modo-aprov .grade-item[data-estado="aprovado"] .selo::after { content: "✓"; }
.modo-aprov .grade-item[data-estado="ajuste"] .selo { background: var(--ajuste); }
.modo-aprov .grade-item[data-estado="ajuste"] .selo::after { content: "!"; }

.enviar { position: fixed; left: 50%; bottom: calc(16px + env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 20;
  width: min(398px, calc(100% - 32px)); min-height: 50px; border-radius: 25px; background: var(--azul); color: #fff;
  font-weight: 700; font-size: 16px; box-shadow: 0 6px 20px #0005; }
dialog { width: min(420px, calc(100% - 24px)); border: 0; border-radius: 16px; padding: 18px; }
dialog::backdrop { background: #0008; }
dialog h2 { margin: 0 0 6px; font-size: 18px; }
#resumo { width: 100%; font: 13px/1.4 inherit; font-family: inherit; padding: 8px; border: 1px solid #ccc; border-radius: 8px; resize: vertical; }
.dialogo-botoes { display: grid; gap: 8px; margin-top: 10px; }
.dialogo-botoes .btn { min-height: 44px; }
.btn-verde { background: #1a7f45; color: #fff; }
.copiado { min-height: 1.2em; margin: 6px 0 0; color: var(--verde); font-weight: 600; }
"""

JS = r"""
(function () {
  var CHAVE = 'pastoral-simulador-respostas-v1';
  var tela = document.getElementById('tela');
  var perfil = document.getElementById('tela-perfil');
  var feed = document.getElementById('tela-feed');
  var respostas = {};
  try { respostas = JSON.parse(localStorage.getItem(CHAVE) || '{}') || {}; } catch (err) { respostas = {}; }
  function guardar() { try { localStorage.setItem(CHAVE, JSON.stringify(respostas)); } catch (err) {} }

  // rolagem: no celular é a página; no computador, a tela dentro da moldura
  function rolador() { return tela.scrollHeight > tela.clientHeight + 1 && getComputedStyle(tela).overflowY === 'auto' ? tela : null; }
  function posicao() { var r = rolador(); return r ? r.scrollTop : window.scrollY; }
  function rolarPara(y) { var r = rolador(); if (r) { r.scrollTop = y; } else { window.scrollTo(0, y); } }
  var posGrade = 0;

  function abrir(n, empilhar) {
    posGrade = posicao();
    perfil.hidden = true; feed.hidden = false;
    var alvo = document.getElementById('post-' + n);
    if (alvo) { alvo.scrollIntoView({ block: 'start' }); var t = alvo.querySelector('.trilho'); if (t) t.focus({ preventScroll: true }); }
    if (empilhar) { try { history.pushState({ post: n }, '', '#post-' + n); } catch (err) {} }
  }
  function fechar() {
    feed.hidden = true; perfil.hidden = false; rolarPara(posGrade);
  }
  document.querySelectorAll('.grade-item').forEach(function (b) {
    b.addEventListener('click', function () { abrir(b.dataset.n, true); });
  });
  document.getElementById('voltar').addEventListener('click', function () {
    if (history.state && history.state.post) { history.back(); } else { fechar(); }
  });
  window.addEventListener('popstate', function (ev) {
    if (ev.state && ev.state.post) { abrir(ev.state.post, false); } else { fechar(); }
  });

  // "mais" da bio e da legenda
  document.querySelectorAll('.link-mais').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.dataset.expande === 'bio') {
        b.previousElementSibling.hidden = false; b.remove();
      } else {
        var curta = b.parentElement; curta.nextElementSibling.hidden = false; curta.remove();
      }
    });
  });

  // carrossel: deslizar (rolagem com encaixe) + setas + pontinhos + "1/7"
  document.querySelectorAll('.carrossel').forEach(function (c) {
    var trilho = c.querySelector('.trilho');
    var total = +c.dataset.total;
    if (total < 2) return;
    var post = c.closest('.post');
    var contador = c.querySelector('.contador');
    var pontos = post.querySelectorAll('.pontos i');
    var ant = c.querySelector('.seta-e'), prox = c.querySelector('.seta-d');
    var atual = 0;
    function mostrar(i) {
      atual = i;
      contador.textContent = (i + 1) + '/' + total;
      pontos.forEach(function (p, k) { p.classList.toggle('on', k === i); });
      ant.hidden = i === 0; prox.hidden = i === total - 1;
    }
    function ir(i) {
      i = Math.max(0, Math.min(total - 1, i));
      trilho.scrollTo({ left: i * trilho.clientWidth, behavior: 'smooth' });
      mostrar(i);
    }
    trilho.addEventListener('scroll', function () {
      var i = Math.round(trilho.scrollLeft / trilho.clientWidth);
      if (i !== atual) mostrar(i);
    }, { passive: true });
    ant.addEventListener('click', function () { ir(atual - 1); });
    prox.addEventListener('click', function () { ir(atual + 1); });
    trilho.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight') { ev.preventDefault(); ir(atual + 1); }
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); ir(atual - 1); }
    });
  });

  // modos
  var botaoInsta = document.getElementById('modo-insta'), botaoAprov = document.getElementById('modo-aprov');
  var enviar = document.getElementById('enviar');
  function modo(aprov) {
    document.body.classList.toggle('modo-aprov', aprov);
    document.body.classList.toggle('modo-insta', !aprov);
    botaoInsta.setAttribute('aria-pressed', String(!aprov));
    botaoAprov.setAttribute('aria-pressed', String(aprov));
    enviar.hidden = !aprov;
    try { localStorage.setItem(CHAVE + '-modo', aprov ? 'aprov' : 'insta'); } catch (err) {}
  }
  botaoInsta.addEventListener('click', function () { modo(false); });
  botaoAprov.addEventListener('click', function () { modo(true); });

  // aprovar / pedir ajuste
  function pintar(n) {
    var post = document.getElementById('post-' + n), r = respostas[n] || {};
    post.querySelector('.btn-aprovar').setAttribute('aria-pressed', String(r.estado === 'aprovado'));
    post.querySelector('.btn-ajuste').setAttribute('aria-pressed', String(r.estado === 'ajuste'));
    post.querySelector('.aprov-campo').hidden = r.estado !== 'ajuste';
    var item = document.querySelector('.grade-item[data-n="' + n + '"]');
    if (r.estado) { item.dataset.estado = r.estado; } else { delete item.dataset.estado; }
  }
  document.querySelectorAll('.post').forEach(function (post) {
    var n = post.dataset.n, campo = post.querySelector('textarea');
    campo.value = (respostas[n] && respostas[n].comentario) || '';
    function marcar(estado) {
      var r = respostas[n] || {};
      r.estado = r.estado === estado ? '' : estado;       // tocar de novo desfaz
      respostas[n] = r; guardar(); pintar(n);
      if (r.estado === 'ajuste') campo.focus();
    }
    post.querySelector('.btn-aprovar').addEventListener('click', function () { marcar('aprovado'); });
    post.querySelector('.btn-ajuste').addEventListener('click', function () { marcar('ajuste'); });
    campo.addEventListener('input', function () {
      respostas[n] = respostas[n] || {}; respostas[n].comentario = campo.value; guardar();
    });
    pintar(n);
  });

  // resumo para enviar
  function montarResumo() {
    var posts = Array.prototype.slice.call(document.querySelectorAll('.post'))
      .sort(function (a, b) { return a.dataset.n - b.dataset.n; });
    var ok = 0, aj = 0, sem = 0;
    var linhas = posts.map(function (p) {
      var n = p.dataset.n, r = respostas[n] || {}, s;
      if (r.estado === 'aprovado') { ok++; s = 'APROVADO'; }
      else if (r.estado === 'ajuste') { aj++; s = 'PEDIR AJUSTE' + (r.comentario && r.comentario.trim() ? ': ' + r.comentario.trim() : ''); }
      else { sem++; s = 'sem resposta'; }
      return 'Publicação ' + n + ' — ' + p.dataset.titulo + '\n→ ' + s;
    });
    var cab = 'Respostas sobre o Instagram da Pastoral do Dízimo (simulação)\n' +
      'Aprovadas: ' + ok + ' · Ajustes: ' + aj + ' · Sem resposta: ' + sem + '\n';
    return { texto: cab + '\n' + linhas.join('\n\n'), ok: ok, aj: aj, sem: sem };
  }
  var dialogo = document.getElementById('dialogo');
  enviar.addEventListener('click', function () {
    var r = montarResumo();
    document.getElementById('resumo').value = r.texto;
    document.getElementById('dialogo-contagem').textContent = r.sem
      ? 'Ainda faltam ' + r.sem + ' publicações sem resposta. Pode enviar assim mesmo ou voltar e completar.'
      : 'Todas as publicações têm resposta. Obrigado!';
    document.getElementById('por-whatsapp').href = 'https://wa.me/?text=' + encodeURIComponent(r.texto);
    document.getElementById('por-email').href = 'mailto:?subject=' +
      encodeURIComponent('Aprovação — Instagram da Pastoral do Dízimo') + '&body=' + encodeURIComponent(r.texto);
    document.getElementById('copiado').textContent = '';
    if (dialogo.showModal) { dialogo.showModal(); } else { dialogo.setAttribute('open', ''); }
    document.getElementById('resumo').scrollTop = 0;
    document.getElementById('por-whatsapp').focus();
  });
  document.getElementById('fechar').addEventListener('click', function () { dialogo.close ? dialogo.close() : dialogo.removeAttribute('open'); });
  document.getElementById('copiar').addEventListener('click', function () {
    var campo = document.getElementById('resumo'), aviso = document.getElementById('copiado');
    function feito() { aviso.textContent = 'Texto copiado. Agora é só colar na conversa.'; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(campo.value).then(feito, function () { campo.select(); document.execCommand('copy'); feito(); });
    } else { campo.select(); document.execCommand('copy'); feito(); }
  });

  var inicial = 'insta';
  try { inicial = localStorage.getItem(CHAVE + '-modo') || 'insta'; } catch (err) {}
  modo(inicial === 'aprov');
  if (/^#post-\d+$/.test(location.hash)) { var n0 = location.hash.slice(6); try { history.replaceState({ post: n0 }, ''); } catch (err) {} abrir(n0, false); }
})();
"""


# ---------------------------------------------------------------- gravação

def gerar(raiz: Path = RAIZ, site: Path | None = None) -> Path:
    """Copia estreia e destaques para <site>/midia/ e grava <site>/aprovacao/index.html."""
    raiz = Path(raiz)
    site = Path(site) if site else raiz / "site"
    dados = coletar(raiz)
    render = raiz / "content" / "estreia" / "render"

    estreia = site / "midia" / "estreia"
    estreia.mkdir(parents=True, exist_ok=True)
    for p in dados["posts"]:
        if p["semana"] == "estreia":
            for img in p["imagens"]:
                nome = Path(img["src"]).name
                shutil.copyfile(render / nome, estreia / nome)
    destaques = site / "midia" / "destaques"
    destaques.mkdir(parents=True, exist_ok=True)
    for d in DESTAQUES:
        nome = f"destaque-{d['arquivo']}.jpg"
        shutil.copyfile(render / nome, destaques / nome)

    # as artes das semanas e o avatar já moram em site/midia/ do repositório: confere que existem
    faltando = [img["src"] for p in dados["posts"] if p["semana"] != "estreia" for img in p["imagens"]
                if not (raiz / "site" / img["src"][3:]).is_file()]
    if faltando:
        raise FileNotFoundError("artes ausentes em site/midia/ (rode preview --semana): " + ", ".join(faltando))

    saida = site / "aprovacao" / "index.html"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(montar_pagina(dados), encoding="utf-8")
    return saida


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gera o simulador do Instagram para aprovação (site/aprovacao/)")
    ap.add_argument("--raiz", type=Path, default=RAIZ, help="raiz do repositório")
    args = ap.parse_args(argv)
    saida = gerar(args.raiz)
    print(f"{saida} + site/midia/estreia/ + site/midia/destaques/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
