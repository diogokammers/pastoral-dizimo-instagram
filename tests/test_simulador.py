"""Simulador do perfil no Instagram para o Padre aprovar (site/aprovacao/)."""
import re

import pytest

from pastoral import simulador


@pytest.fixture
def dados():
    """Perfil mínimo: 2 posts fixados publicados e 2 futuros (um de imagem única)."""
    def post(n, fixado, publicado, data, slides, legenda="Legenda curta."):
        return {
            "numero": n, "titulo": f"Título {n}", "pilar": "Formação", "semana": "2026-W40",
            "data": data, "publicado": publicado, "fixado": fixado, "legenda": legenda,
            "legenda_proposta": publicado,
            "imagens": [{"src": f"../midia/x/post-{n}-{i:02d}.jpg", "alt": f"Alt {n}.{i}"}
                        for i in range(1, slides + 1)],
        }
    return {
        "perfil": {"usuario": "pastoraldodizimo.arquifln",
                   "nome": "Pastoral do Dízimo | Arquidiocese de Florianópolis",
                   "bio": "Linha um.\nLinha dois.\n@pe.alexjr\n@arquifloripa",
                   "avatar": "../midia/perfil/avatar.jpg", "seguidores": 73, "seguindo": 2},
        "destaques": [{"nome": "Dízimo", "capa": "../midia/destaques/destaque-dizimo.jpg"},
                      {"nome": "Arquifln", "capa": "../midia/destaques/destaque-arquifln.jpg"}],
        "posts": [
            post(1, True, True, "2026-09-26T21:47:40-03:00", 3, "Bem-vindos! " + "palavra " * 40),
            post(2, True, True, "2026-09-26T21:47:40-03:00", 2),
            post(9, False, False, "2026-10-16T19:00:00-03:00", 1),
            post(4, False, False, "2026-09-29T19:00:00-03:00", 2),
        ],
    }


def test_pagina_tem_perfil_contadores_e_bio_com_mencoes(dados):
    html = simulador.montar_pagina(dados)
    assert "pastoraldodizimo.arquifln" in html
    assert "Pastoral do Dízimo | Arquidiocese de Florianópolis" in html
    assert re.search(r"<b>4</b>\s*<span>publicações</span>", html)
    assert re.search(r"<b>73</b>\s*<span>seguidores</span>", html)
    assert re.search(r"<b>2</b>\s*<span>seguindo</span>", html)
    assert '<span class="mencao">@pe.alexjr</span>' in html
    assert '<span class="mencao">@arquifloripa</span>' in html
    assert "../midia/perfil/avatar.jpg" in html


def test_botoes_seguir_e_mensagem_desativados(dados):
    html = simulador.montar_pagina(dados)
    assert re.search(r"<button[^>]*disabled[^>]*>Seguir</button>", html)
    assert re.search(r"<button[^>]*disabled[^>]*>Mensagem</button>", html)


def test_destaques_na_ordem(dados):
    html = simulador.montar_pagina(dados)
    assert html.index(">Dízimo<") < html.index(">Arquifln<")
    assert "../midia/destaques/destaque-dizimo.jpg" in html


def test_grade_na_ordem_com_alfinete_e_icone_de_carrossel(dados):
    html = simulador.montar_pagina(dados)
    itens = re.findall(r'<button class="grade-item" data-n="(\d+)"', html)
    assert itens == ["1", "2", "9", "4"]
    assert html.count('class="ico-fixado"') == 2
    assert html.count('class="ico-carrossel"') == 3          # post 9 tem 1 imagem só


def test_feed_tem_carrossel_contador_alt_e_data(dados):
    html = simulador.montar_pagina(dados)
    assert 'alt="Alt 1.3"' in html and 'alt="Alt 9.1"' in html
    assert "1/3" in html
    assert "26 de setembro" in html and "16 de outubro" in html
    assert 'aria-label="Curtir"' in html and 'aria-label="Salvar"' in html


def test_legenda_longa_truncada_com_mais():
    texto = "Bem-vindos! Este é o perfil.\n\n" + "palavra " * 40
    curta, completo = simulador.resumir_legenda(texto, 100)
    assert curta.startswith("Bem-vindos! Este é o perfil. palavra")   # corrida, sem quebras
    assert len(curta) <= 100 and curta.endswith("palavra")               # corta no fim de palavra
    assert completo == texto.strip()                                     # expandida: texto inteiro, com parágrafos
    assert simulador.resumir_legenda("Curta.") == ("Curta.", "")


def test_legenda_no_post_recolhida_e_expandida_sem_repetir(dados):
    html = simulador.montar_pagina(dados)
    post1 = html[html.index('id="post-1"'):html.index('id="post-2"')]
    assert post1.count('class="link-mais"') == 1 and "leg-completa" in post1
    assert post1.count("<b>pastoraldodizimo.arquifln</b>") == 3      # topo, recolhida e expandida
    post2 = html[html.index('id="post-2"'):html.index('id="post-9"')]
    assert "link-mais" not in post2                                   # legenda curta: sem "mais"


def test_celular_so_mostra_o_instagram(dados):
    html = simulador.montar_pagina(dados)
    celular = html[html.index('<div class="celular">'):html.index('<aside class="painel"')]
    for proibido in ("Aprovar", "Pedir ajuste", "legenda proposta", "Modo aprovação", "selo"):
        assert proibido not in celular, proibido
    assert "Modo aprovação" not in html and "Ver como no Instagram" not in html


def test_painel_com_blocos_contadores_e_itens(dados):
    html = simulador.montar_pagina(dados)
    painel = html[html.index('<aside class="painel"'):html.index("</aside>")]
    assert "Pendentes de aprovação" in painel and "Aprovadas" in painel and "Em ajuste" in painel
    assert 'id="conta-pendentes">(4)' in painel
    assert re.findall(r'<li class="item" id="item-(\d+)"', painel) == ["1", "2", "4", "9"]
    assert painel.count('data-acao="aprovar"') == 4 and painel.count('data-acao="ajuste"') == 4
    assert painel.count('data-acao="salvar"') == 4 and "Salvar ajuste" in painel
    assert "Editar" in painel and "Desfazer" in painel
    assert "terça-feira, 29/09/2026, 19:00" in painel and "Publicado em" in painel
    assert painel.count("nova legenda simples") == 2                  # posts 1-3 (aqui, 1 e 2)
    assert "Enviar minhas respostas" in painel
    assert 'href="#painel"' in html and "Aprovações (4 pendentes)" in html
    assert "https://wa.me/?text=" in html and "mailto:?" in html
    assert "localStorage" in html and "try {" in html



def test_painel_blocos_recolhiveis_e_listas_de_publicadas_e_agendadas(dados):
    html = simulador.montar_pagina(dados)
    painel = html[html.index('<aside class="painel"'):html.index("</aside>")]
    ordem = re.findall(r'<section class="bloco" id="bloco-(\w+)"', painel)
    assert ordem == ["pendentes", "aprovadas", "ajuste", "publicadas", "agendadas"]
    assert painel.count('aria-expanded="false"') == 5 and 'aria-expanded="true"' not in painel
    assert len(re.findall(r'class="bloco-corpo" id="corpo-\w+" hidden', painel)) == 5
    assert 'id="conta-publicadas">(2)' in painel and 'id="conta-agendadas">(2)' in painel
    publicadas = painel[painel.index('id="bloco-publicadas"'):painel.index('id="bloco-agendadas"')]
    assert re.findall(r'item-titulo" data-abrir="(\d+)"', publicadas) == ["1", "2"]
    assert "Publicado em sábado, 26/09/2026, 21:47" in publicadas
    agendadas = painel[painel.index('id="bloco-agendadas"'):]
    assert re.findall(r'item-titulo" data-abrir="(\d+)"', agendadas) == ["4", "9"]   # por data
    assert "Previsto para terça-feira, 29/09/2026, 19:00 (provisória)" in agendadas


def test_faixa_de_aviso(dados):
    html = simulador.montar_pagina(dados)
    assert "Simulação para aprovação — nada disso foi publicado ainda, exceto os 3 posts fixados." in html


def test_sem_dependencias_externas(dados):
    html = simulador.montar_pagina(dados)
    assert not re.search(r'(src|href)="https?://', html)
    assert "base64" not in html


def test_coletar_do_repositorio(raiz):
    d = simulador.coletar(raiz)
    assert [p["numero"] for p in d["posts"]] == [1, 2, 3, 11, 10, 9, 8, 7, 6, 5, 4]
    assert [p["fixado"] for p in d["posts"][:4]] == [True, True, True, False]
    assert all(p["publicado"] for p in d["posts"][:3])
    # posts 1-3 usam a legenda simples proposta (ADR-010), não a publicada
    assert d["posts"][0]["legenda"].startswith("Bem-vindos! Este é o perfil")
    assert d["posts"][0]["legenda_proposta"] is True
    assert "@pe.alexjr" in d["perfil"]["bio"]
    assert [x["nome"] for x in d["destaques"]] == ["Dízimo", "Formação", "Agenda", "Perguntas", "Arquifln"]
    for p in d["posts"]:
        assert p["imagens"] and all(x["alt"] for x in p["imagens"])


def test_gerar_copia_midia_e_grava_pagina(raiz, tmp_path):
    saida = simulador.gerar(raiz, site=tmp_path)
    assert saida == tmp_path / "aprovacao" / "index.html"
    html = saida.read_text(encoding="utf-8")
    assert (tmp_path / "midia" / "estreia" / "post-1-01.jpg").is_file()
    assert (tmp_path / "midia" / "destaques" / "destaque-dizimo.jpg").is_file()
    # toda imagem referenciada existe (as semanas vêm de site/midia/ do repositório)
    for src in re.findall(r'src="\.\./(midia/[^"]+)"', html):
        assert (tmp_path / src).is_file() or (raiz / "site" / src).is_file(), src
