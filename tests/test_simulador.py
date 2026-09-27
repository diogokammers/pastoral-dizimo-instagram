"""Simulador do perfil no Instagram para o aprovador (site/aprovacao/) — painel ligado ao Worker (ADR-011/012)."""
import json
import re
import shutil

import pytest

from pastoral import aprovacao, simulador

API = "https://pastoral-dizimo-aprovacao.exemplo.workers.dev"


@pytest.fixture
def dados():
    """Perfil mínimo: 2 posts fixados publicados e 2 futuros (um de imagem única)."""
    def post(n, fixado, publicado, data, slides, legenda="Legenda curta."):
        return {
            "numero": n, "titulo": f"Título {n}", "pilar": "Formação", "semana": "2026-W40",
            "data": data, "publicado": publicado, "fixado": fixado, "legenda": legenda,
            "legenda_proposta": publicado, "versao": None if publicado else f"{n:032x}",
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
    html = simulador.montar_pagina(dados, API)
    assert "pastoraldodizimo.arquifln" in html
    assert "Pastoral do Dízimo | Arquidiocese de Florianópolis" in html
    assert re.search(r"<b>4</b>\s*<span>publicações</span>", html)
    assert re.search(r"<b>73</b>\s*<span>seguidores</span>", html)
    assert re.search(r"<b>2</b>\s*<span>seguindo</span>", html)
    assert '<span class="mencao">@pe.alexjr</span>' in html
    assert '<span class="mencao">@arquifloripa</span>' in html
    assert "../midia/perfil/avatar.jpg" in html


def test_botoes_seguir_e_mensagem_desativados(dados):
    html = simulador.montar_pagina(dados, API)
    assert re.search(r"<button[^>]*disabled[^>]*>Seguir</button>", html)
    assert re.search(r"<button[^>]*disabled[^>]*>Mensagem</button>", html)


def test_destaques_na_ordem(dados):
    html = simulador.montar_pagina(dados, API)
    assert html.index(">Dízimo<") < html.index(">Arquifln<")
    assert "../midia/destaques/destaque-dizimo.jpg" in html


def test_grade_na_ordem_com_alfinete_e_icone_de_carrossel(dados):
    html = simulador.montar_pagina(dados, API)
    itens = re.findall(r'<button class="grade-item" data-n="(\d+)"', html)
    assert itens == ["1", "2", "9", "4"]
    assert html.count('class="ico-fixado"') == 2
    assert html.count('class="ico-carrossel"') == 3          # post 9 tem 1 imagem só


def test_feed_tem_carrossel_contador_alt_e_data(dados):
    html = simulador.montar_pagina(dados, API)
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
    html = simulador.montar_pagina(dados, API)
    post1 = html[html.index('id="post-1"'):html.index('id="post-2"')]
    assert post1.count('class="link-mais"') == 1 and "leg-completa" in post1
    assert post1.count("<b>pastoraldodizimo.arquifln</b>") == 3      # topo, recolhida e expandida
    post2 = html[html.index('id="post-2"'):html.index('id="post-9"')]
    assert "link-mais" not in post2                                   # legenda curta: sem "mais"


def test_celular_so_mostra_o_instagram(dados):
    html = simulador.montar_pagina(dados, API)
    celular = html[html.index('<div class="celular">'):html.index('<aside class="painel"')]
    for proibido in ("Aprovar", "Pedir ajuste", "legenda proposta", "Modo aprovação", "selo"):
        assert proibido not in celular, proibido
    assert "Modo aprovação" not in html and "Ver como no Instagram" not in html


def painel_de(html):
    return html[html.index('<aside class="painel"'):html.index("</aside>")]


def test_painel_pendentes_so_com_o_que_nao_foi_publicado(dados):
    """Pedido 1: posts já publicados (1–3) não aparecem em Pendentes; ficam em Já publicadas."""
    painel = painel_de(simulador.montar_pagina(dados, API))
    assert "Pendentes de aprovação" in painel and "Aprovadas" in painel and "Em ajuste" in painel
    pendentes = painel[painel.index('id="bloco-pendentes"'):painel.index('id="bloco-aprovadas"')]
    assert re.findall(r'<li class="item" id="item-(\d+)"', pendentes) == ["4", "9"]
    assert 'id="conta-pendentes">(2)' in painel
    assert painel.count('data-acao="aprovar"') == 2 and painel.count('data-acao="ajuste"') == 2
    assert painel.count('data-acao="salvar"') == 2 and "Salvar ajuste" in painel
    assert "Editar" in painel and "Desfazer" in painel
    assert "terça-feira, 29/09/2026, 19:00" in pendentes
    assert "nova legenda simples" not in painel
    assert 'href="#painel"' in simulador.montar_pagina(dados, API)


def test_itens_levam_semana_e_versao_do_conteudo(dados):
    painel = painel_de(simulador.montar_pagina(dados, API))
    assert 'id="item-4" data-n="4" data-semana="2026-W40" data-versao="' + f"{4:032x}" + '"' in painel
    assert 'id="item-9" data-n="9" data-semana="2026-W40" data-versao="' + f"{9:032x}" + '"' in painel


def test_painel_blocos_recolhiveis_e_listas_de_publicadas_e_agendadas(dados):
    painel = painel_de(simulador.montar_pagina(dados, API))
    ordem = re.findall(r'<section class="bloco" id="bloco-(\w+)"', painel)
    assert ordem == ["pendentes", "aprovadas", "ajuste", "publicadas", "agendadas"]
    assert painel.count('aria-expanded="false"') == 5 and 'aria-expanded="true"' not in painel
    assert len(re.findall(r'class="bloco-corpo" id="corpo-\w+" hidden', painel)) == 5
    assert 'id="conta-publicadas">(2)' in painel
    publicadas = painel[painel.index('id="bloco-publicadas"'):painel.index('id="bloco-agendadas"')]
    assert re.findall(r'item-titulo" data-abrir="(\d+)"', publicadas) == ["1", "2"]
    assert "Publicado em sábado, 26/09/2026, 21:47" in publicadas


def test_agendadas_so_mostra_aprovadas(dados):
    """Pedido 2: Agendadas começa vazia; o JS mostra só os itens aprovados (com a data provisória)."""
    painel = painel_de(simulador.montar_pagina(dados, API))
    assert 'id="conta-agendadas">(0)' in painel
    agendadas = painel[painel.index('id="bloco-agendadas"'):]
    assert re.findall(r'<li class="item item-simples item-agendado" data-n="(\d+)" hidden>', agendadas) == ["4", "9"]
    assert "Previsto para terça-feira, 29/09/2026, 19:00 (provisória)" in agendadas
    assert 'id="vazio-agendadas"' in agendadas


def test_faixa_de_aviso(dados):
    """Sem "simulação" nem "nada foi publicado" (a página é o instrumento real); o Como usar explica rascunho e envio."""
    html = simulador.montar_pagina(dados, API)
    assert "simulação" not in html.lower()
    assert "nada disso foi publicado ainda" not in html and "exceto os 3 posts fixados" not in html
    assert "Como usar" in html and "a enviar" in html and "Enviar respostas" in html and "Desfazer" in html
    assert "15 minutos" in html
    assert "Enviar minhas respostas" not in html and "wa.me" not in html


def test_sem_mencao_a_padre(dados):
    """O sistema usa o termo neutro "aprovador" (ADR-012)."""
    html = simulador.montar_pagina(dados, API).lower()
    assert "padre" not in html


def test_rascunho_no_aparelho_e_envio_com_codigo(dados):
    """ADR-012: respostas como rascunho no localStorage (com try/catch); o código só é pedido no envio,
    vai só no header Authorization e só para a API (CSP connect-src); não há código na página."""
    html = simulador.montar_pagina(dados, API)
    assert f'var API = "{API}";' in html
    assert f"connect-src {API}" in html and '<meta name="referrer" content="no-referrer">' in html
    assert "pastoral-painel-rascunho-v1" in html and "try { localStorage.setItem(CHAVE" in html
    assert "localStorage.removeItem('pastoral-painel-codigo-v1')" in html, "apaga o código guardado pela versão antiga"
    assert '<input id="codigo" type="password" autocomplete="off"' in html
    assert "'Authorization': 'Bearer ' + codigo" in html
    assert "/api/estado" in html and "/api/decisoes" in html and "/api/decisao'" not in html
    assert 'id="enviar"' in html and 'data-acao="descartar"' in html
    assert "#c=" not in html and "?c=" not in html and "location.hash.match" not in html
    assert "localStorage.setItem(CHAVE, codigo" not in html and "so-leitura" not in html


def test_url_da_api_precisa_ser_https(dados):
    with pytest.raises(ValueError):
        simulador.montar_pagina(dados, "http://inseguro.exemplo")
    with pytest.raises(ValueError):
        simulador.montar_pagina(dados, 'https://x.exemplo/"><script>')


def test_sem_dependencias_externas(dados):
    html = simulador.montar_pagina(dados, API)
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
    assert all(p["versao"] is None for p in d["posts"][:3])
    assert "@pe.alexjr" in d["perfil"]["bio"]
    assert [x["nome"] for x in d["destaques"]] == ["Dízimo", "Formação", "Agenda", "Perguntas", "Arquifln"]
    for p in d["posts"]:
        assert p["imagens"] and all(x["alt"] for x in p["imagens"])


def test_versao_de_cada_post_e_a_do_worker(raiz):
    """data-versao = aprovacao.versao_post do item do ADR-008 (o Worker calcula igual no GitHub)."""
    d = simulador.coletar(raiz)
    semana = "2026-W41"
    pasta = raiz / "content" / "semanas" / semana
    agenda = json.loads((pasta / "agenda.json").read_text(encoding="utf-8"))
    lote = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
    itens = aprovacao.itens_semana(agenda, lote, lambda a: (raiz / "site" / "midia" / semana / a).read_bytes())
    por_numero = {p["numero"]: p for p in d["posts"]}
    for item in itens:
        assert por_numero[item["numero"]]["versao"] == aprovacao.versao_post(semana, item)


def copia_minima(raiz, destino):
    """Cópia do repositório só com o que o simulador lê (estreia, semanas, mídia, docs)."""
    for parte in ("content", "site/midia", "docs/auditoria"):
        shutil.copytree(raiz / parte, destino / parte)
    return destino


def test_post_de_semana_ja_publicado_sai_de_pendentes(raiz, tmp_path):
    copia = copia_minima(raiz, tmp_path / "repo")
    (copia / "content" / "semanas" / "2026-W40" / "publicado.json").write_text(json.dumps(
        {"semana": "2026-W40", "posts": [{"numero": 4, "ig_media_id": "1"}]}), encoding="utf-8")
    d = simulador.coletar(copia)
    p4 = next(p for p in d["posts"] if p["numero"] == 4)
    assert p4["publicado"] is True
    painel = painel_de(simulador.montar_pagina(d, API))
    pendentes = painel[painel.index('id="bloco-pendentes"'):painel.index('id="bloco-aprovadas"')]
    assert 'id="item-4"' not in pendentes and 'id="item-5"' in pendentes


def test_coletar_filtra_semanas(raiz):
    d = simulador.coletar(raiz, semanas=["2026-W41"])
    assert sorted(p["numero"] for p in d["posts"]) == [1, 2, 3, 6, 7]


def test_gerar_copia_midia_e_grava_pagina(raiz, tmp_path):
    saida = simulador.gerar(raiz, site=tmp_path, api_url=API)
    assert saida == tmp_path / "aprovacao" / "index.html"
    html = saida.read_text(encoding="utf-8")
    assert (tmp_path / "midia" / "estreia" / "post-1-01.jpg").is_file()
    assert (tmp_path / "midia" / "destaques" / "destaque-dizimo.jpg").is_file()
    # toda imagem referenciada existe (as semanas vêm de site/midia/ do repositório)
    for src in re.findall(r'src="\.\./(midia/[^"]+)"', html):
        assert (tmp_path / src).is_file() or (raiz / "site" / src).is_file(), src
    assert f'var API = "{API}";' in html


def test_gerar_pagina_de_teste_em_outro_destino_copia_as_artes(raiz, tmp_path):
    saida = simulador.gerar(raiz, site=tmp_path, api_url=API, destino="aprovacao-teste", semanas=["2026-W41"])
    assert saida == tmp_path / "aprovacao-teste" / "index.html"
    assert (tmp_path / "midia" / "2026-W41" / "post-7-08.jpg").is_file()
    html = saida.read_text(encoding="utf-8")
    assert 'id="item-6"' in html and 'id="item-4"' not in html
