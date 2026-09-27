"""ADR-011 — o JS do painel num navegador de verdade (Chromium via Playwright), com a API do Worker simulada.

Confere: sem código = só leitura (nenhuma chamada à API); o código sai do fragmento e vai só no header
Authorization; o estado do Worker distribui os cartões (aprovado → Aprovadas e Agendadas; versão diferente
→ volta para Pendentes); aprovar / pedir ajuste / desfazer mandam o corpo certo; 401 e 409 são tratados.
Pula se o Playwright ou o Chromium não estiverem instalados.
"""
import functools
import http.server
import json
import threading

import pytest

from pastoral import simulador

sync_api = pytest.importorskip("playwright.sync_api")
# a CSP da página proíbe eval: os testes esperam por seletores, nunca por wait_for_function

API = "https://api.exemplo.test"
CODIGO = "c0d1g0-de-teste_0123456789abcdefghijklmn"
V4, V9 = "4" * 32, "9" * 32


def dados():
    def post(n, publicado, data, versao):
        return {"numero": n, "titulo": f"Título {n}", "pilar": "Formação", "semana": "estreia" if publicado else "2026-W40",
                "data": data, "publicado": publicado, "fixado": publicado, "legenda": "Legenda.",
                "legenda_proposta": False, "versao": versao,
                "imagens": [{"src": f"../midia/x/post-{n}-01.jpg", "alt": f"Alt {n}"}]}
    return {
        "perfil": {"usuario": "pastoraldodizimo.arquifln", "nome": "Pastoral", "bio": "Bio.",
                   "avatar": "../midia/perfil/avatar.jpg", "seguidores": 1, "seguindo": 1},
        "destaques": [],
        "posts": [post(1, True, "2026-09-26T21:47:40-03:00", None),
                  post(9, False, "2026-10-16T19:00:00-03:00", V9),
                  post(4, False, "2026-09-29T19:00:00-03:00", V4)],
    }


def evento(post, acao, versao, comentario=""):
    return {"id": 1, "post": post, "semana": "2026-W40", "acao": acao, "comentario": comentario,
            "versao_conteudo": versao, "autor": "Padre", "criado_em": "2026-10-01T12:00:00+00:00",
            "origem": "painel", "commit_sha": "abc"}


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("site")
    (pasta / "aprovacao").mkdir()
    (pasta / "aprovacao" / "index.html").write_text(simulador.montar_pagina(dados(), API), encoding="utf-8")
    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    manipulador = functools.partial(Silencioso, directory=str(pasta))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/aprovacao/"
    httpd.shutdown()


@pytest.fixture(scope="module")
def navegador():
    try:
        pw = sync_api.sync_playwright().start()
        b = pw.chromium.launch()
    except Exception as erro:          # Chromium não instalado
        pytest.skip(f"Chromium indisponível: {erro}")
    yield b
    b.close()
    pw.stop()


class ApiFalsa:
    """Responde /api/estado e /api/decisao como o Worker, registrando os pedidos."""

    def __init__(self, estado, status_estado=200, status_decisao=200):
        self.estado, self.status_estado, self.status_decisao = estado, status_estado, status_decisao
        self.pedidos = []

    def __call__(self, route):
        req = route.request
        cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        self.pedidos.append({"metodo": req.method, "url": req.url, "auth": req.headers.get("authorization"),
                             "corpo": json.loads(req.post_data) if req.post_data else None})
        if req.url.endswith("/api/estado"):
            corpo = {"autor": "Padre", "posts": self.estado} if self.status_estado == 200 else {"erro": "x"}
            return route.fulfill(status=self.status_estado, headers=cors, json=corpo)
        pedido = self.pedidos[-1]["corpo"]
        if self.status_decisao != 200:
            return route.fulfill(status=self.status_decisao, headers=cors, json={"erro": "conteudo_mudou", "mensagem": "mudou"})
        versao = V4 if pedido["post"] == 4 else V9
        ev = evento(pedido["post"], pedido["acao"], versao, pedido.get("comentario", ""))
        self.estado[str(pedido["post"])] = ev
        return route.fulfill(status=200, headers=cors, json={"ok": True, "estado": ev})


def abrir(navegador, url, api):
    pagina = navegador.new_page()
    pagina.route(f"{API}/**", api)
    pagina.goto(url)
    pagina.wait_for_load_state("networkidle")
    for b in pagina.locator(".bloco-botao").all():
        b.click()
    return pagina


def ids(pagina, lista):
    return pagina.eval_on_selector_all(f"#lista-{lista} > li", "els => els.map(e => e.dataset.n)")


def agendadas(pagina):
    return pagina.eval_on_selector_all("#lista-agendadas > li:not([hidden])", "els => els.map(e => e.dataset.n)")


def test_sem_codigo_so_leitura_sem_chamar_a_api(navegador, servidor):
    api = ApiFalsa({})
    pagina = abrir(navegador, servidor, api)
    assert api.pedidos == []
    assert "so-leitura" in pagina.evaluate("document.body.className")
    assert ids(pagina, "pendentes") == ["4", "9"]                 # o publicado (1) não está em Pendentes
    assert not pagina.locator("#item-4 .btn-aprovar").is_visible()
    assert agendadas(pagina) == []
    assert "Modo só leitura" in pagina.inner_text("#acesso")
    pagina.close()


def test_com_codigo_estado_distribui_e_decisoes_vao_para_a_api(navegador, servidor):
    api = ApiFalsa({"4": evento(4, "aprovar", V4), "9": evento(9, "ajustar", "0" * 32, "trocar")})
    pagina = abrir(navegador, servidor + "#c=" + CODIGO, api)
    assert "c=" not in pagina.url, "o código sai da barra de endereço"
    assert pagina.evaluate("localStorage.getItem('pastoral-painel-codigo-v1')") == CODIGO
    assert api.pedidos[0]["metodo"] == "GET" and api.pedidos[0]["auth"] == f"Bearer {CODIGO}"
    assert "c0d1g0" not in api.pedidos[0]["url"], "o código nunca vai na URL"
    assert "Padre" in pagina.inner_text("#acesso")
    # 4 aprovado na versão atual → Aprovadas e Agendadas; 9 teve ajuste numa versão antiga → Pendentes
    assert ids(pagina, "aprovadas") == ["4"] and ids(pagina, "pendentes") == ["9"] and agendadas(pagina) == ["4"]
    assert "mudou depois da resposta" in pagina.inner_text("#item-9 .item-status")

    pagina.click("#item-9 .btn-aprovar")
    pagina.wait_for_selector("#lista-aprovadas #item-9", state="attached")
    assert api.pedidos[-1]["corpo"] == {"acao": "aprovar", "versao": V9, "semana": "2026-W40", "post": 9}
    assert api.pedidos[-1]["auth"] == f"Bearer {CODIGO}"
    assert agendadas(pagina) == ["4", "9"]                        # por data: 29/09 antes de 16/10

    pagina.click("#item-4 [data-acao=desfazer]")
    pagina.wait_for_selector("#lista-pendentes #item-4", state="attached")
    assert api.pedidos[-1]["corpo"] == {"acao": "desfazer", "semana": "2026-W40", "post": 4}
    assert agendadas(pagina) == ["9"]

    pagina.click("#item-4 [data-acao=ajuste]")
    pagina.fill("#item-4 textarea", "  Trocar a capa.  ")
    pagina.click("#item-4 [data-acao=salvar]")
    pagina.wait_for_selector("#lista-ajuste #item-4", state="attached")
    assert api.pedidos[-1]["corpo"] == {"acao": "ajustar", "comentario": "Trocar a capa.", "semana": "2026-W40", "post": 4}
    assert "Trocar a capa." in pagina.inner_text("#item-4 .item-comentario")
    assert pagina.inner_text("#conta-pendentes") == "(0)"

    pagina.click("#sair")
    assert pagina.evaluate("localStorage.getItem('pastoral-painel-codigo-v1')") is None
    assert "so-leitura" in pagina.evaluate("document.body.className")
    pagina.close()


def test_codigo_invalido_vira_so_leitura_e_e_esquecido(navegador, servidor):
    api = ApiFalsa({}, status_estado=401)
    pagina = abrir(navegador, servidor + "#c=" + CODIGO, api)
    assert "não vale mais" in pagina.inner_text("#acesso")
    assert pagina.evaluate("localStorage.getItem('pastoral-painel-codigo-v1')") is None
    assert "so-leitura" in pagina.evaluate("document.body.className")
    pagina.close()


def test_conteudo_mudou_409_avisa_sem_mover(navegador, servidor):
    api = ApiFalsa({}, status_decisao=409)
    pagina = abrir(navegador, servidor + "#c=" + CODIGO, api)
    pagina.click("#item-4 .btn-aprovar")
    pagina.wait_for_selector("#item-4 .item-aviso:has-text('recarregue')")
    assert ids(pagina, "pendentes") == ["4", "9"] and agendadas(pagina) == []
    pagina.close()
