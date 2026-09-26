"""Fatia 5 (parte) — prévia autocontida do pacote de estreia para o Diogo e o Padre."""
import json
import re

import pytest

from pastoral import preview


@pytest.fixture
def dados(raiz):
    return json.loads((raiz / "content/estreia/posts.json").read_text(encoding="utf-8"))


@pytest.fixture
def bio(raiz):
    return preview.ler_bio(raiz / "content/estreia/bio.md")


def imagens_falsas(dados):
    nomes = [f"post-{p['numero']}-{i:02d}.jpg" for p in dados["posts"] for i in range(1, len(p["slides"]) + 1)]
    nomes += [f"destaque-{d['arquivo']}.jpg" for d in preview.DESTAQUES]
    return {n: f"img/{n}" for n in nomes}


def test_ler_bio(bio):
    assert bio["nome"] == "Pastoral do Dízimo | Arquidiocese de Florianópolis"
    assert bio["principal"].startswith("Evangelizar, formar e fortalecer")
    assert len(bio["alternativas"]) == 2


def test_pagina_tem_texto_de_apoio_para_o_padre(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    assert "O que estamos pedindo para aprovar" in html


def test_pagina_tem_perfil_destaques_e_grade(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    assert "pastoraldodizimo.arquifln" in html and bio["nome"] in html   # como no app, sem "@"
    for d in preview.DESTAQUES:
        assert d["nome"] in html and f"img/destaque-{d['arquivo']}.jpg" in html
    assert html.count('class="grade-item"') == 3


def test_pagina_tem_todos_os_slides_legendas_e_alt_texts(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    total = sum(len(p["slides"]) for p in dados["posts"])
    assert html.count('class="slide"') == total
    for p in dados["posts"]:
        assert p["titulo"] in html
        primeira_linha = p["legenda"].splitlines()[0]
        assert primeira_linha.replace('"', "&quot;") in html
        for s in p["slides"]:
            assert s["alt_text"].replace('"', "&quot;") in html
        for item in p.get("a_conferir", []):
            assert item.replace('"', "&quot;") in html


def test_pagina_nao_carrega_nada_de_fora(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    assert not re.search(r'(src|href)="https?://', html)
    assert "<link" not in html


def test_main_gera_html_autocontido(raiz, tmp_path):
    saida = tmp_path / "index.html"
    assert preview.main(["--saida", str(saida)]) == 0
    html = saida.read_text(encoding="utf-8")
    assert "data:image/jpeg;base64," in html and 'src="post-' not in html


def test_carrossel_navega_no_navegador(raiz, tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    saida = tmp_path / "index.html"
    preview.main(["--saida", str(saida)])
    try:
        with sync_api.sync_playwright() as p:
            nav = p.chromium.launch()
            pagina = nav.new_page()
            pagina.goto(saida.as_uri())
            post = pagina.locator("#post-1")
            assert post.locator(".contador").inner_text() == "1/7"
            post.locator("button.proximo").click()
            assert post.locator(".contador").inner_text() == "2/7"
            assert "Quem somos" in post.locator(".alt-atual").inner_text()
            nav.close()
    except Exception as erro:
        if "Executable doesn't exist" in str(erro):
            pytest.skip("Chromium indisponível")
        raise
