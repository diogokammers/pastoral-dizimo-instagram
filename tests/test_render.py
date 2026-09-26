"""Fatia 4 — templates HTML/CSS + render com Playwright + QA (arquitetura §1.1, §4.2, §6)."""
import pytest
from PIL import Image

from pastoral import lint, render


@pytest.fixture(scope="module")
def config():
    return lint.carregar_config(render.RAIZ / "config.yaml")


# ---------- unitários (sem navegador) ----------

def test_tokens_css_vem_do_config(config):
    css = render.tokens_css(config)
    assert "--vermelho: #A3121C" in css and "--vermelho-profundo: #7E0F17" in css and "--prata: #F3F2EE" in css


def test_html_da_capa_tem_titulo_e_assinatura_tipografica(config):
    html = render.montar_html({"template": "capa", "eyebrow": "Formação", "titulo": "O que é o dízimo?"},
                              config, indice=1, total=7)
    assert "O que é o dízimo?" in html and "@pastoraldodizimo.arquifln" in html
    assert "Pastoral do Dízimo" in html
    assert "<img" not in html          # marca.simbolo: null → sem símbolo


def test_html_escapa_texto(config):
    html = render.montar_html({"template": "conteudo", "titulo": "<script>x</script>", "texto": "a & b"},
                              config, indice=2, total=3)
    assert "<script>x" not in html and "&lt;script&gt;" in html and "a &amp; b" in html


def test_html_do_conteudo_tem_numeracao(config):
    html = render.montar_html({"template": "conteudo", "titulo": "T", "texto": "x"}, config, indice=2, total=7)
    assert "2/7" in html


def test_html_de_cada_template_usa_fontes_locais(config):
    css = (render.TEMPLATES / "base.css").read_text(encoding="utf-8")
    assert "Cormorant Garamond" in css and "Source Sans 3" in css
    for fonte in ["cormorant-garamond/CormorantGaramond-wght.ttf", "source-sans-3/SourceSans3-wght.ttf"]:
        assert f"../assets/fonts/{fonte}" in css and (render.RAIZ / "assets/fonts" / fonte).exists()
    assert "fonts.googleapis" not in css
    for t in ["capa", "conteudo", "citacao", "cta"]:
        html = render.montar_html({"template": t, "titulo": "T", "texto": "x", "referencia": "2Cor 9,7"},
                                  config, indice=1, total=2)
        assert 'href="base.css"' in html and render.TEMPLATES.as_uri() in html


def test_html_do_destaque_tem_icone_svg(config):
    html = render.montar_html_destaque("livro", config)
    assert "<svg" in html and "1920" in html


def test_cinco_destaques_sem_paroquias():
    # ADR-007: o destaque "Paróquias" foi removido
    assert [d["nome"] for d in render.DESTAQUES] == ["Dízimo", "Formação", "Agenda", "Perguntas", "Arquifln"]
    for d in render.DESTAQUES:
        assert (render.RAIZ / "templates" / "icones" / f"{d['icone']}.svg").exists()


# ---------- tema de fundo (ADR-007) ----------

@pytest.mark.parametrize("post, esperado", [
    ({"fixado": True}, "vermelho"),
    ({"importante": True}, "vermelho"),
    ({"fixado": True, "importante": False}, "vermelho"),
    ({}, "creme"),
    ({"fixado": False, "importante": False}, "creme"),
])
def test_tema_segue_fixado_ou_importante(post, esperado):
    assert render.tema_do_post(post) == esperado


def test_tema_vermelho_capa_e_cta_escuros_conteudo_prata():
    assert render.classe_fundo("capa", "vermelho") == "escuro"
    assert render.classe_fundo("cta", "vermelho") == "escuro"
    assert render.classe_fundo("conteudo", "vermelho") == "claro"
    assert render.classe_fundo("citacao", "vermelho") == "claro"


def test_tema_creme_todos_os_slides_em_creme():
    for t in ["capa", "conteudo", "citacao", "cta"]:
        assert render.classe_fundo(t, "creme") == "creme"


def test_html_leva_a_classe_do_tema(config):
    slide = {"template": "capa", "titulo": "T"}
    assert 'class="arte escuro"' in render.montar_html(slide, config, 1, 2)          # padrão: vermelho
    assert 'class="arte creme"' in render.montar_html(slide, config, 1, 2, tema="creme")
    css = (render.TEMPLATES / "base.css").read_text(encoding="utf-8")
    assert ".creme" in css and "var(--creme)" in css


def test_razao_de_contraste_conhecida():
    # identidade-visual §3: vermelho sobre prata 7,05:1; dourado sobre prata 2,79:1
    assert render.contraste("#A3121C", "#F3F2EE") == pytest.approx(7.05, abs=0.02)
    assert render.contraste("#B08D3B", "#F3F2EE") == pytest.approx(2.79, abs=0.02)


# ---------- integração (Playwright + Chromium) ----------

@pytest.fixture(scope="module")
def renderizador():
    pytest.importorskip("playwright")
    try:
        with render.Renderizador() as r:
            yield r
    except Exception as erro:  # Chromium ausente
        pytest.skip(f"Chromium indisponível: {erro}")


def test_slide_normal_passa_no_qa(renderizador, config, tmp_path):
    destino = tmp_path / "ok.jpg"
    html = render.montar_html({"template": "conteudo", "titulo": "Um gesto de fé",
                               "texto": "O dízimo é a resposta agradecida de quem reconhece que tudo vem de Deus."},
                              config, indice=2, total=7)
    qa = renderizador.renderizar_html(html, destino, 1080, 1350)
    assert qa["ok"], qa
    img = Image.open(destino)
    assert img.format == "JPEG" and img.size == (1080, 1350) and img.mode == "RGB"
    assert img.info.get("icc_profile")               # perfil sRGB embutido
    assert qa["bytes"] < 8 * 1024 * 1024 and qa["fontes_ok"]


def test_overflow_proposital_e_detectado(renderizador, config, tmp_path):
    html = render.montar_html({"template": "conteudo", "titulo": "Estouro", "texto": " ".join(["palavra"] * 300)},
                              config, indice=2, total=3)
    qa = renderizador.renderizar_html(html, tmp_path / "overflow.jpg", 1080, 1350)
    assert not qa["ok"] and qa["overflow"]


def test_contraste_baixo_e_detectado(renderizador, tmp_path):
    html = (render.RAIZ / "tests/fixtures/contraste-baixo.html").read_text(encoding="utf-8")
    qa = renderizador.renderizar_html(html, tmp_path / "contraste.jpg", 1080, 1350)
    assert not qa["ok"] and qa["contraste"]
    assert qa["contraste"][0]["razao"] < 4.5


def test_texto_fora_da_area_segura_e_detectado(renderizador, tmp_path):
    html = (render.RAIZ / "tests/fixtures/fora-da-area-segura.html").read_text(encoding="utf-8")
    qa = renderizador.renderizar_html(html, tmp_path / "area.jpg", 1080, 1350)
    assert not qa["ok"] and len(qa["area_segura"]) == 2      # um na lateral, um no rodapé


def test_dimensao_errada_e_detectada(renderizador, config, tmp_path):
    html = render.montar_html({"template": "capa", "titulo": "T"}, config, indice=1, total=2)
    qa = renderizador.renderizar_html(html, tmp_path / "d.jpg", 1080, 1350, esperado=(1080, 1080))
    assert not qa["ok"] and qa["dimensoes"] == [1080, 1350]


def test_destaque_1080x1920(renderizador, config, tmp_path):
    qa = renderizador.renderizar_html(render.montar_html_destaque("cruz", config), tmp_path / "d.jpg", 1080, 1920)
    assert qa["ok"], qa
    assert Image.open(tmp_path / "d.jpg").size == (1080, 1920)


def test_post_comum_em_creme_passa_no_qa(renderizador, config, tmp_path):
    post = {"numero": 8, "slides": [
        {"template": "capa", "eyebrow": "Formação", "titulo": "Título de teste", "texto": "Apoio", "alt_text": "a"},
        {"template": "conteudo", "eyebrow": "Parte", "titulo": "Um gesto de fé", "texto": "Texto corrido.",
         "fonte": "Doc. CNBB 106, n. 12", "alt_text": "a"},
        {"template": "citacao", "texto": "Deus ama quem dá com alegria.", "referencia": "2Cor 9,7", "alt_text": "a"},
        {"template": "cta", "titulo": "Salve este post", "texto": "Para rever.", "alt_text": "a"},
    ]}
    resultados = renderizador.renderizar_post(post, tmp_path, config)
    assert all(r["tema"] == "creme" for r in resultados)
    assert all(r["ok"] for r in resultados), resultados
    # o fundo renderizado é o creme do config (canto superior esquerdo)
    r, g, b = Image.open(tmp_path / "post-8-01.jpg").getpixel((5, 5))
    alvo = config["marca"]["paleta"]["creme"].lstrip("#")
    assert all(abs(v - int(alvo[i:i + 2], 16)) <= 3 for v, i in zip((r, g, b), (0, 2, 4)))


def test_renderiza_post_inteiro(renderizador, config, tmp_path):
    post = {"numero": 9, "slides": [
        {"template": "capa", "eyebrow": "Formação", "titulo": "Título de teste", "alt_text": "a"},
        {"template": "citacao", "texto": "Deus ama quem dá com alegria.", "referencia": "2Cor 9,7", "alt_text": "a"},
        {"template": "cta", "titulo": "Salve este post", "texto": "Para rever.", "alt_text": "a"},
    ]}
    resultados = renderizador.renderizar_post(post, tmp_path, config)
    assert [r["arquivo"] for r in resultados] == ["post-9-01.jpg", "post-9-02.jpg", "post-9-03.jpg"]
    assert all(r["ok"] for r in resultados), resultados
