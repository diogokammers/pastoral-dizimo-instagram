"""Simulador do perfil no Instagram para o Padre ver e aprovar tudo de uma vez.

Gera site/aprovacao/index.html: uma página que imita o app do Instagram (celular, tema claro) com o
perfil @pastoraldodizimo.arquifln, os destaques e TODAS as publicações — as 3 da estreia (já
publicadas e fixadas, com a legenda simples proposta em docs/auditoria/) e as da reserva
(content/semanas/*/, datas provisórias de agenda.json). Tocar num post abre o feed, com carrossel
deslizável. O celular mostra só o Instagram; a aprovação fica num painel ao lado (abaixo, no celular),
com os blocos Pendentes / Aprovadas / Em ajuste. As respostas ficam no aparelho (localStorage) e o
botão "Enviar minhas respostas" monta um resumo para WhatsApp, e-mail ou copiar. Nenhum servidor:
é uma página estática no GitHub Pages.

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
LIMITE_LEGENDA = 100         # caracteres visíveis (nome + legenda) antes do "… mais", ~2 linhas no app
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
    """(parte visível, texto inteiro) — recolhida, o app mostra ~2 linhas corridas, cortadas no fim de
    uma palavra, e põe "… mais"; o texto inteiro (com parágrafos) só aparece ao tocar. Sem sobra: ("…", "")."""
    texto = texto.strip()
    corrido = " ".join(texto.split())
    if len(corrido) <= limite:
        return texto, ""
    corte = corrido.rfind(" ", 0, limite + 1)
    visivel = corrido[:corte if corte > 0 else limite].rstrip(" ,;:.…—-")
    return visivel, texto


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
            f'<span class="grade-icones">{icones}</span></button>')
    return f"""
<nav class="abas" aria-label="Abas do perfil">
  <span class="aba ativa" aria-current="page">{_svg(ICO["grade"], "Publicações")}</span>
  <span class="aba">{_svg(ICO["reels"], "Reels")}</span>
  <span class="aba">{_svg(ICO["marcados"], "Marcados")}</span>
</nav>
<div class="grade">{"".join(itens)}</div>"""


def _legenda(texto: str, usuario: str) -> str:
    """Nome em negrito + início da legenda (~2 linhas) e "… mais"; ao tocar, o texto inteiro."""
    visivel, completo = resumir_legenda(texto, LIMITE_LEGENDA - len(usuario) - 1)
    nome = f"<b>{e(usuario)}</b>"
    if not completo:
        return f'<p class="legenda">{nome} {marcar(visivel)}</p>'
    return (f'<p class="legenda leg-curta">{nome} <span class="leg-texto">{marcar(visivel)}</span>… '
            f'<button class="link-mais" data-expande="leg" aria-label="Ler a legenda inteira">mais</button></p>'
            f'<p class="legenda leg-completa" hidden>{nome} {marcar(completo)}</p>')


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
    return f"""
<article class="post" id="post-{n}" data-n="{n}" aria-label="Publicação {n}">
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
  {_legenda(p["legenda"], usuario)}
  <p class="post-data">{data_curta(p["data"])}</p>
</article>"""


def _item_painel(p: dict) -> str:
    """Um cartão do painel de aprovação; o JS o move entre Pendentes, Aprovadas e Em ajuste."""
    n = p["numero"]
    quando = (f"Publicado em {data_por_extenso(p['data'])}" if p["publicado"]
              else f"Data prevista: {data_por_extenso(p['data'])}")
    nota = ('<p class="item-nota">Já está no ar. Aprovar aqui = aprovar a <b>nova legenda simples</b> '
            '(legenda proposta — nova versão simples; a imagem não muda).</p>' if p["legenda_proposta"] else "")
    return f"""
<li class="item" id="item-{n}" data-n="{n}" data-titulo="{e(p["titulo"])}">
  <button class="item-abrir" data-abrir="{n}" aria-label="Ver a publicação {n} no celular">
    <img src="{e(p["imagens"][0]["src"])}" alt="" loading="lazy" width="60" height="75">
  </button>
  <div class="item-texto">
    <button class="item-titulo" data-abrir="{n}"><b>{n}.</b> {e(p["titulo"])}</button>
    <p class="item-data">{e(quando)}</p>
    {nota}
    <p class="item-comentario" hidden></p>
  </div>
  <div class="item-acoes">
    <button class="btn-aprovar" data-acao="aprovar">Aprovar</button>
    <button class="btn-ajuste" data-acao="ajuste">Pedir ajuste</button>
    <button class="btn-leve" data-acao="editar">Editar</button>
    <button class="btn-leve" data-acao="desfazer">Desfazer</button>
  </div>
  <div class="item-campo" hidden>
    <label>O que ajustar?<textarea rows="3" placeholder="Escreva aqui o que mudar (texto, imagem, data…)"></textarea></label>
    <p class="item-aviso" aria-live="polite"></p>
    <div class="item-acoes-campo">
      <button class="btn-ajuste" data-acao="salvar">Salvar ajuste</button>
      <button class="btn-leve" data-acao="cancelar">Cancelar</button>
    </div>
  </div>
</li>"""


def _bloco(chave: str, titulo: str, conta: int, corpo: str) -> str:
    """Bloco recolhível do painel: começa sempre fechado; o título é o botão de abrir/fechar."""
    return f"""
  <section class="bloco" id="bloco-{chave}">
    <h2><button class="bloco-botao" aria-expanded="false" aria-controls="corpo-{chave}">
      <span>{titulo} <span class="conta" id="conta-{chave}">({conta})</span></span>
      <span class="bloco-sinal" aria-hidden="true"></span></button></h2>
    <div class="bloco-corpo" id="corpo-{chave}" hidden>{corpo}</div>
  </section>"""


def _item_simples(p: dict) -> str:
    """Item das listas "Já publicadas" e "Agendadas": miniatura, nº, título e data; abre o post."""
    n = p["numero"]
    quando = (f"Publicado em {data_por_extenso(p['data'])}" if p["publicado"]
              else f"Previsto para {data_por_extenso(p['data'])} (provisória)")
    return (f'<li class="item item-simples"><button class="item-abrir" data-abrir="{n}" '
            f'aria-label="Ver a publicação {n} no celular"><img src="{e(p["imagens"][0]["src"])}" alt="" loading="lazy" '
            f'width="60" height="75"></button><div class="item-texto"><button class="item-titulo" data-abrir="{n}">'
            f'<b>{n}.</b> {e(p["titulo"])}</button><p class="item-data">{e(quando)}</p></div></li>')


def _painel(posts: list[dict]) -> str:
    por_numero = sorted(posts, key=lambda p: p["numero"])
    itens = "".join(_item_painel(p) for p in por_numero)
    publicadas = [p for p in por_numero if p["publicado"]]
    agendadas = sorted((p for p in posts if not p["publicado"]), key=lambda p: (p["data"], p["numero"]))
    blocos = "".join([
        _bloco("pendentes", "Pendentes de aprovação", len(posts),
               f'<ul class="lista" id="lista-pendentes">{itens}</ul>'
               '<p class="vazio" id="vazio-pendentes" hidden>Nenhuma publicação pendente. Obrigado!</p>'),
        _bloco("aprovadas", "Aprovadas", 0,
               '<ul class="lista" id="lista-aprovadas"></ul><p class="vazio" id="vazio-aprovadas">Nenhuma ainda.</p>'),
        _bloco("ajuste", "Em ajuste", 0,
               '<ul class="lista" id="lista-ajuste"></ul><p class="vazio" id="vazio-ajuste">Nenhuma ainda.</p>'),
        _bloco("publicadas", "Já publicadas", len(publicadas),
               '<ul class="lista">' + "".join(_item_simples(p) for p in publicadas) + "</ul>"),
        _bloco("agendadas", "Agendadas", len(agendadas),
               '<p class="vazio">Datas previstas, ainda provisórias.</p>'
               '<ul class="lista">' + "".join(_item_simples(p) for p in agendadas) + "</ul>"),
    ])
    return f"""
<aside class="painel" id="painel" aria-label="Aprovação das publicações">
  <div class="faixa" role="note">
    <p><b>Simulação para aprovação — nada disso foi publicado ainda, exceto os 3 posts fixados.</b></p>
    <details><summary>Como usar</summary>
      <ol>
        <li>O celular mostra como o Instagram da Pastoral vai ficar no fim de outubro. Toque numa publicação
          para abri-la e deslize a imagem para o lado para ver as outras. Toque em "mais" para ler a legenda inteira.</li>
        <li>Toque em <b>Pendentes de aprovação</b> para abrir a lista. Em cada publicação, toque em <b>Aprovar</b>
          ou em <b>Pedir ajuste</b>; no ajuste, escreva o que mudar e toque em <b>Salvar ajuste</b>.
          Tocar na imagem ou no título mostra a publicação no celular.</li>
        <li>As respondidas vão para <b>Aprovadas</b> ou <b>Em ajuste</b>, onde dá para desfazer ou editar.</li>
        <li>No fim, toque em <b>Enviar minhas respostas</b> e mande pelo WhatsApp ou por e-mail.</li>
      </ol>
      <p>Suas respostas ficam guardadas neste aparelho; pode parar e continuar depois.</p>
    </details>
  </div>
  {blocos}
  <button id="enviar" class="enviar">Enviar minhas respostas</button>
</aside>"""


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
<body>
<div class="palco">
<div class="celular">
  <div class="tela" id="tela">
    <div id="tela-perfil">
      {_cabecalho_perfil(perfil, len(posts))}
      {_destaques(dados["destaques"])}
      {_grade(posts)}
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
{_painel(posts)}
</div>
<a href="#painel" class="ir-painel" id="ir-painel">Aprovações ({len(posts)} pendentes)</a>
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
  --mencao:#00376b; --foco:#0064e0; --verde:#1c7a43; --ajuste:#a64a07; --painel:#fffbf0; --borda:#e3cf96; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { margin: 0; background: #fff; color: var(--texto);
  font: 14px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: inherit; }
button:disabled { cursor: default; }
:focus-visible { outline: 3px solid var(--foco); outline-offset: 2px; }
[hidden] { display: none !important; }
.ico { width: 24px; height: 24px; display: block; }

/* o "celular" */
.celular { max-width: 430px; margin: 0 auto; background: var(--fundo); }
.tela { position: relative; background: var(--fundo); }

/* painel de aprovação (fora do "app") */
.painel { max-width: 430px; margin: 0 auto; padding: 16px 16px 90px; background: var(--painel);
  border-top: 6px solid var(--borda); color: #2b2100; scroll-margin-top: 0; }
.faixa { padding: 12px 14px; background: #fff3cf; border: 1px solid var(--borda); border-radius: 12px; font-size: 14px; }
.faixa p { margin: 0 0 4px; }
.faixa details { margin-top: 4px; }
.faixa summary { cursor: pointer; color: #5c4300; text-decoration: underline; font-weight: 600; }
.faixa ol { margin: 6px 0; padding-left: 20px; } .faixa li { margin: 4px 0; }
.bloco { margin-top: 10px; background: #fff; border: 1px solid #e6dcc0; border-radius: 12px; }
.bloco h2 { font-size: 16px; margin: 0; }
.bloco-botao { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 8px;
  min-height: 48px; padding: 8px 14px; font-weight: 700; color: #2b2100; }
.bloco-sinal { flex: none; width: 26px; height: 26px; border-radius: 50%; background: #f3ead2; position: relative; }
.bloco-sinal::before, .bloco-sinal::after { content: ""; position: absolute; left: 7px; top: 12px; width: 12px; height: 2px;
  background: #2b2100; }
.bloco-sinal::after { transform: rotate(90deg); }
.bloco-botao[aria-expanded="true"] .bloco-sinal::after { display: none; }
.bloco-corpo { padding: 0 10px 10px; }
.bloco-corpo > .vazio { margin: 0 4px 8px; }
.conta { color: #5c4a1a; font-weight: 600; }
.lista { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.vazio { margin: 0; color: #5c5c5c; font-size: 13px; }
.bloco .item { background: #fffdf7; }
.item { display: grid; grid-template-columns: 60px 1fr; gap: 6px 10px; padding: 10px; background: #fff;
  border: 1px solid #e6dcc0; border-radius: 12px; }
.item-abrir img { width: 60px; height: 75px; object-fit: cover; display: block; border-radius: 4px; }
.item-texto { min-width: 0; }
.item-titulo { display: block; font-weight: 600; color: #000; text-decoration: underline; text-decoration-color: #0003; }
.item-texto p { margin: 3px 0 0; font-size: 13px; color: #4d4d4d; }
.item-nota { font-style: italic; }
.item-comentario { color: #6b3000 !important; background: #fff4ea; padding: 6px 8px; border-radius: 6px; white-space: pre-line; }
.item-acoes, .item-campo { grid-column: 1 / -1; }
.item-acoes, .item-acoes-campo { display: flex; gap: 8px; flex-wrap: wrap; }
.item-acoes button, .item-acoes-campo button { flex: 1; min-height: 44px; border-radius: 8px; font-weight: 700; padding: 0 10px; text-align: center; }
.btn-aprovar { background: var(--verde); color: #fff; }
.btn-ajuste { background: #fff; color: var(--ajuste); border: 2px solid var(--ajuste) !important; }
.item-acoes-campo .btn-ajuste { background: var(--ajuste); color: #fff; }
.btn-leve { flex: 0 1 auto !important; min-height: 36px !important; background: #f2f2f2; color: #333; font-weight: 600 !important; }
.item-campo label { display: block; font-weight: 600; font-size: 13px; }
.item-campo textarea { display: block; width: 100%; margin-top: 4px; font: inherit; font-weight: 400; font-size: 16px;
  padding: 8px; border: 1px solid #999; border-radius: 8px; }
.item-aviso { margin: 4px 0; min-height: 1em; font-size: 13px; color: var(--ajuste); }
.item[data-estado="aprovado"] { border-color: #b7dcc4; }
.item[data-estado="ajuste"] { border-color: #f0c9a6; }
.enviar { display: block; width: 100%; margin-top: 20px; min-height: 50px; border-radius: 25px; background: var(--azul);
  color: #fff; font-weight: 700; font-size: 16px; text-align: center; box-shadow: 0 4px 14px #0003; }
.ir-painel { position: fixed; right: 12px; bottom: calc(12px + env(safe-area-inset-bottom)); z-index: 20;
  background: #2b2100e6; color: #fff; text-decoration: none; font-size: 13px; font-weight: 600;
  padding: 8px 14px; border-radius: 18px; box-shadow: 0 2px 10px #0004; }

/* no computador: moldura de celular com rolagem própria */
@media (min-width: 700px) {
  body { background: #e9e9ee; }
  .celular { width: 414px; margin: 20px auto; height: max(560px, min(860px, calc(100vh - 40px))); border: 12px solid #111;
    border-radius: 48px; overflow: hidden; box-shadow: 0 20px 60px #0003; }
  .tela { height: 100%; overflow-y: auto; scrollbar-width: none; }
  .tela::-webkit-scrollbar { display: none; }
  .painel { border: 1px solid var(--borda); border-radius: 16px; margin-bottom: 20px; }
}
/* a partir de 1000px: painel à esquerda, celular à direita, cada um com sua rolagem */
@media (min-width: 1000px) {
  .palco { display: flex; justify-content: center; align-items: flex-start; gap: 32px; padding: 20px; }
  .painel { order: -1; width: 400px; max-width: none; margin: 0; padding-bottom: 16px;
    max-height: calc(100vh - 40px); overflow-y: auto; }
  .celular { margin: 0; flex: none; }
  .ir-painel { display: none; }
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

/* feed */
.post { border-bottom: 1px solid var(--linha); padding-bottom: 12px; scroll-margin-top: 48px; }
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
.legenda { margin: 4px 12px 0; overflow-wrap: anywhere; }
.leg-completa { white-space: pre-line; }
.post-data { margin: 6px 12px 0; color: var(--suave); font-size: 12px; }

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
  function rolador() { return getComputedStyle(tela).overflowY === 'auto' ? tela : null; }
  function posicao() { var r = rolador(); return r ? r.scrollTop : window.scrollY; }
  function rolarPara(y) { var r = rolador(); if (r) { r.scrollTop = y; } else { window.scrollTo({ top: y, behavior: 'instant' }); } }
  var posGrade = 0;

  function abrir(n, empilhar) {
    if (feed.hidden) posGrade = posicao();
    perfil.hidden = true; feed.hidden = false;
    ajustarLegendas();
    var alvo = document.getElementById('post-' + n);
    if (alvo) {
      var r = rolador();
      if (r) { r.scrollTop = alvo.offsetTop - 48; } else { alvo.scrollIntoView({ block: 'start', behavior: 'instant' }); }
      var t = alvo.querySelector('.trilho'); if (t) t.focus({ preventScroll: true });
    }
    if (empilhar) { try { history.pushState({ post: n }, '', '#post-' + n); } catch (err) {} }
  }
  function fechar() { feed.hidden = true; perfil.hidden = false; rolarPara(posGrade); }
  document.querySelectorAll('.grade-item').forEach(function (b) {
    b.addEventListener('click', function () { abrir(b.dataset.n, true); });
  });
  document.getElementById('voltar').addEventListener('click', function () {
    if (history.state && history.state.post) { history.back(); } else { fechar(); }
  });
  window.addEventListener('popstate', function (ev) {
    if (ev.state && ev.state.post) { abrir(ev.state.post, false); } else { fechar(); }
  });

  // telas estreitas: tira palavras do fim até a legenda recolhida caber em 2 linhas, como o app
  function ajustarLegendas() {
    document.querySelectorAll('.leg-curta').forEach(function (p) {
      var t = p.querySelector('.leg-texto');
      if (t.children.length) return;                       // com @menção no começo: deixa como está
      if (!t.dataset.orig) t.dataset.orig = t.textContent;
      t.textContent = t.dataset.orig;
      var alt = parseFloat(getComputedStyle(p).lineHeight);
      while (p.getBoundingClientRect().height > alt * 2.5 && t.textContent.indexOf(' ') > 0) {
        t.textContent = t.textContent.replace(/\s+\S+$/, '').replace(/[\s,;:.…—-]+$/, '');
      }
    });
  }
  window.addEventListener('resize', function () { if (!feed.hidden) ajustarLegendas(); });

  // "mais" da bio e da legenda (a versão curta some e entra o texto inteiro, sem repetir o começo)
  document.querySelectorAll('.link-mais').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.dataset.expande === 'bio') {
        b.previousElementSibling.hidden = false; b.remove();
      } else {
        var curta = b.closest('.leg-curta'); curta.nextElementSibling.hidden = false; curta.remove();
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

  // painel: cada cartão vai para Pendentes, Aprovadas ou Em ajuste conforme a resposta
  var listas = { '': 'pendentes', aprovado: 'aprovadas', ajuste: 'ajuste' };
  var itens = Array.prototype.slice.call(document.querySelectorAll('.item:not(.item-simples)'));
  function estado(n) { return (respostas[n] && respostas[n].estado) || ''; }
  function mostrarBotoes(item, visiveis) {
    item.querySelectorAll('.item-acoes button').forEach(function (b) { b.hidden = visiveis.indexOf(b.dataset.acao) < 0; });
  }
  function pintarItem(item) {
    var n = item.dataset.n, st = estado(n), editando = item.dataset.editando === '1';
    var r = respostas[n] || {};
    item.dataset.estado = st || 'pendente';
    var campo = item.querySelector('.item-campo');
    campo.hidden = !editando;
    item.querySelector('.item-acoes').hidden = editando;
    var com = item.querySelector('.item-comentario');
    com.hidden = !(st === 'ajuste' && r.comentario && !editando);
    com.textContent = st === 'ajuste' ? 'Ajuste pedido: ' + (r.comentario || '') : '';
    if (st === 'aprovado') mostrarBotoes(item, ['desfazer']);
    else if (st === 'ajuste') mostrarBotoes(item, ['editar', 'desfazer']);
    else mostrarBotoes(item, ['aprovar', 'ajuste']);
  }
  function redistribuir() {
    var contas = { pendentes: 0, aprovadas: 0, ajuste: 0 };
    itens.forEach(function (item) {
      var nome = listas[estado(item.dataset.n)];
      document.getElementById('lista-' + nome).appendChild(item);   // mantém a ordem por número
      contas[nome]++;
      pintarItem(item);
    });
    Object.keys(contas).forEach(function (k) {
      document.getElementById('conta-' + k).textContent = '(' + contas[k] + ')';
      document.getElementById('vazio-' + k).hidden = contas[k] > 0;
    });
    document.getElementById('ir-painel').textContent = contas.pendentes
      ? 'Aprovações (' + contas.pendentes + (contas.pendentes === 1 ? ' pendente)' : ' pendentes)')
      : 'Aprovações (tudo respondido)';
  }
  itens.forEach(function (item) {
    var n = item.dataset.n, texto = item.querySelector('textarea'), aviso = item.querySelector('.item-aviso');
    item.addEventListener('click', function (ev) {
      var b = ev.target.closest('button'); if (!b) return;
      if (b.dataset.abrir) { abrir(b.dataset.abrir, true); return; }
      var acao = b.dataset.acao; if (!acao) return;
      var r = respostas[n] || {};
      if (acao === 'aprovar') { respostas[n] = { estado: 'aprovado', comentario: r.comentario || '' }; }
      else if (acao === 'ajuste' || acao === 'editar') {
        item.dataset.editando = '1'; texto.value = r.comentario || ''; aviso.textContent = '';
        pintarItem(item); texto.focus(); return;
      }
      else if (acao === 'cancelar') { item.dataset.editando = ''; pintarItem(item); return; }
      else if (acao === 'salvar') {
        if (!texto.value.trim()) { aviso.textContent = 'Escreva o que precisa mudar antes de salvar.'; texto.focus(); return; }
        item.dataset.editando = ''; respostas[n] = { estado: 'ajuste', comentario: texto.value.trim() };
      }
      else if (acao === 'desfazer') { respostas[n] = { estado: '', comentario: r.comentario || '' }; }
      guardar(); redistribuir();
      var foco = item.querySelector('.item-acoes button:not([hidden])'); if (foco) foco.focus({ preventScroll: false });
    });
  });
  redistribuir();

  // blocos recolhíveis: sempre começam fechados
  document.querySelectorAll('.bloco-botao').forEach(function (b) {
    b.addEventListener('click', function () {
      var aberto = b.getAttribute('aria-expanded') === 'true';
      b.setAttribute('aria-expanded', String(!aberto));
      document.getElementById(b.getAttribute('aria-controls')).hidden = aberto;
    });
  });
  document.querySelectorAll('.item-simples').forEach(function (li) {
    li.addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-abrir]'); if (b) abrir(b.dataset.abrir, true);
    });
  });

  // resumo para enviar
  function montarResumo() {
    var ok = 0, aj = 0, sem = 0;
    var linhas = itens.map(function (item) {
      var n = item.dataset.n, r = respostas[n] || {}, s;
      if (r.estado === 'aprovado') { ok++; s = 'APROVADO'; }
      else if (r.estado === 'ajuste') { aj++; s = 'PEDIR AJUSTE: ' + (r.comentario || ''); }
      else { sem++; s = 'sem resposta'; }
      var nota = item.querySelector('.item-nota') ? ' (nova legenda simples)' : '';
      return 'Publicação ' + n + ' — ' + item.dataset.titulo + nota + '\n→ ' + s;
    });
    var cab = 'Respostas sobre o Instagram da Pastoral do Dízimo (simulação)\n' +
      'Aprovadas: ' + ok + ' · Ajustes: ' + aj + ' · Sem resposta: ' + sem + '\n';
    return { texto: cab + '\n' + linhas.join('\n\n'), sem: sem };
  }
  var dialogo = document.getElementById('dialogo');
  document.getElementById('enviar').addEventListener('click', function () {
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
