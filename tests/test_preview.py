"""Fatia 5 (parte) — prévia autocontida do pacote de estreia para o Diogo e o aprovador."""
import json
import re
import shutil
from pathlib import Path

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


def test_pagina_tem_texto_de_apoio_para_o_aprovador(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    assert "O que estamos pedindo para aprovar" in html


def test_apoio_fala_em_5_destaques_sem_paroquias(dados, bio):
    html = preview.montar_pagina(dados, bio, imagens_falsas(dados))
    assert "Capas dos 5 destaques" in html and "6 destaques" not in html
    assert "Paróquias" not in html


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


# ---------- fatia 5: prévia semanal (site/semanas/<semana>/) e artes públicas (site/midia/<semana>/) ----------

FIXTURE_SEMANA = Path(__file__).parent / "fixtures" / "semana-exemplo" / "content" / "semanas" / "2026-W41"
BRIEFING = {"semana": "2026-W41", "posts": [
    {"indice": 12, "data": "2026-10-06", "hora": "19:00", "fuso": "America/Sao_Paulo"},
    {"indice": 13, "data": "2026-10-09", "hora": "19:00", "fuso": "America/Sao_Paulo"}]}


@pytest.fixture
def repo_semana(tmp_path):
    pasta = tmp_path / "content" / "semanas" / "2026-W41"
    (pasta / "render").mkdir(parents=True)
    shutil.copy(FIXTURE_SEMANA / "posts.json", pasta / "posts.json")
    (pasta / "briefing.json").write_text(json.dumps(BRIEFING), encoding="utf-8")
    for nome in ("post-12-01.jpg", "post-12-02.jpg", "post-13-01.jpg"):
        (pasta / "render" / nome).write_bytes(b"\xff\xd8" + nome.encode())
    (pasta / "render" / "qa.json").write_text(json.dumps({"posts": [
        {"post": 12, "arquivo": "post-12-01.jpg", "ok": True}, {"post": 12, "arquivo": "post-12-02.jpg", "ok": True},
        {"post": 13, "arquivo": "post-13-01.jpg", "ok": False}]}), encoding="utf-8")
    return tmp_path


def test_semana_grava_agenda_copia_artes_e_gera_pagina(repo_semana):
    html_path = preview.gerar_semana(repo_semana, "2026-W41", usuario="@pastoraldodizimo.arquifln")
    assert html_path == repo_semana / "site" / "semanas" / "2026-W41" / "index.html"

    agenda = json.loads((repo_semana / "content/semanas/2026-W41/agenda.json").read_text(encoding="utf-8"))
    assert agenda == json.loads((FIXTURE_SEMANA / "agenda.json").read_text(encoding="utf-8"))

    midia = repo_semana / "site" / "midia" / "2026-W41"
    assert sorted(p.name for p in midia.iterdir()) == ["post-12-01.jpg", "post-12-02.jpg", "post-13-01.jpg"]
    assert (midia / "post-12-02.jpg").read_bytes() == b"\xff\xd8post-12-02.jpg"

    html = html_path.read_text(encoding="utf-8")
    assert 'src="../../midia/2026-W41/post-12-01.jpg"' in html
    assert html.count('class="slide"') == 3
    assert "O dízimo é gratidão" in html and "Imagem única" in html
    assert "Nada foi publicado" in html
    assert "terça-feira, 06/10/2026, 19:00" in html
    assert "QA automático: revisar post-13-01.jpg" in html
    assert not re.search(r'(src|href)="https?://', html)


def test_semana_remove_arte_velha_de_versao_anterior(repo_semana):
    midia = repo_semana / "site" / "midia" / "2026-W41"
    midia.mkdir(parents=True)
    (midia / "post-12-03.jpg").write_bytes(b"velha")
    preview.gerar_semana(repo_semana, "2026-W41")
    assert not (midia / "post-12-03.jpg").exists()


def test_semana_sem_arte_renderizada_falha(repo_semana):
    (repo_semana / "content/semanas/2026-W41/render/post-12-02.jpg").unlink()
    with pytest.raises(FileNotFoundError, match="post-12-02.jpg"):
        preview.gerar_semana(repo_semana, "2026-W41")


def test_main_semana(repo_semana):
    assert preview.main(["--semana", "2026-W41", "--raiz", str(repo_semana)]) == 0
    assert (repo_semana / "site/semanas/2026-W41/index.html").exists()
