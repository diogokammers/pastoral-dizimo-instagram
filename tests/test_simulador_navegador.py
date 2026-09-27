"""ADR-012 — o JS do painel num navegador de verdade (Chromium via Playwright), com a API do Worker simulada.

Confere: o estado vem do GET público (sem código); Aprovar/Pedir ajuste/Desfazer viram RASCUNHO no
aparelho ("a enviar"), sem chamar a API, e sobrevivem a recarregar; "Enviar respostas" pede o código,
que vai só no header Authorization; código errado (401) e bloqueio (429) param o envio sem perder o
rascunho; com o código certo, cada post é enviado e o que falhar (409) fica marcado, sem travar os outros.
O código usado aqui é inventado. Pula se o Playwright ou o Chromium não estiverem instalados.
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
CODIGO = "Xyzw"
V4, V9, V7 = "4" * 32, "9" * 32, "7" * 32


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
                  post(7, False, "2026-10-09T19:00:00-03:00", V7),
                  post(4, False, "2026-09-29T19:00:00-03:00", V4)],
    }


VERSOES = {4: V4, 7: V7, 9: V9}


def evento(post, acao, versao, comentario=""):
    return {"id": 1, "post": post, "semana": "2026-W40", "acao": acao, "comentario": comentario,
            "versao_conteudo": versao, "autor": "Aprovador", "criado_em": "2026-10-01T12:00:00+00:00",
            "origem": "painel", "commit_sha": "abc"}


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("site")
    (pasta / "aprovacao").mkdir()
    (pasta / "aprovacao" / "index.html").write_text(simulador.montar_pagina(dados(), API), encoding="utf-8")
    # página longa como a real (11 posts + estreia): o painel fica bem abaixo do "celular"
    longa = dados()
    for n in range(20, 32):
        extra = dict(longa["posts"][1], numero=n, titulo=f"Título {n}", versao=f"{n:032x}")
        longa["posts"].append(extra)
    (pasta / "aprovacao-longa").mkdir()
    (pasta / "aprovacao-longa" / "index.html").write_text(simulador.montar_pagina(longa, API), encoding="utf-8")

    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(pasta)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/aprovacao/"
    httpd.shutdown()


@pytest.fixture(scope="module")
def pw_motores():
    """Uma só instância do Playwright por módulo (o modo síncrono não admite duas ao mesmo tempo)."""
    pw = sync_api.sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="module")
def navegador(pw_motores):
    try:
        b = pw_motores.chromium.launch()
    except Exception as erro:          # Chromium não instalado
        pytest.skip(f"Chromium indisponível: {erro}")
    yield b
    b.close()


class ApiFalsa:
    """Responde /api/estado (público) e /api/decisoes (com código) como o Worker, registrando os pedidos."""

    def __init__(self, estado, bloqueado=False, conflito=()):
        self.estado, self.bloqueado, self.conflito = estado, bloqueado, set(conflito)
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
            return route.fulfill(status=200, headers=cors, json={"posts": self.estado})
        if self.bloqueado:
            return route.fulfill(status=429, headers=cors, json={"erro": "bloqueado", "mensagem": "Bloqueado até as 10:15."})
        if req.headers.get("authorization") != f"Bearer {CODIGO}":
            return route.fulfill(status=401, headers=cors, json={"erro": "codigo_invalido", "mensagem": "Código errado. Restam 4."})
        resultados = []
        for d in self.pedidos[-1]["corpo"]["decisoes"]:
            if d["post"] in self.conflito:
                resultados.append({"ok": False, "post": d["post"], "status": 409, "erro": "conteudo_mudou",
                                   "mensagem": "Esta publicação mudou."})
                continue
            ev = evento(d["post"], d["acao"], VERSOES[d["post"]], d.get("comentario", ""))
            self.estado[str(d["post"])] = ev
            resultados.append({"ok": True, "post": d["post"], "status": 200, "estado": ev})
        return route.fulfill(status=200, headers=cors, json={"ok": all(r["ok"] for r in resultados), "resultados": resultados})


def abrir(navegador, url, api, contexto=None):
    ctx = contexto or navegador.new_context()
    pagina = ctx.new_page()
    pagina.route(f"{API}/**", api)
    pagina.goto(url)
    pagina.wait_for_load_state("networkidle")
    for b in pagina.locator(".bloco-botao").all():
        if b.get_attribute("aria-expanded") == "false":
            b.click()
    return pagina


def ids(pagina, lista):
    return pagina.eval_on_selector_all(f"#lista-{lista} > li", "els => els.map(e => e.dataset.n)")


def agendadas(pagina):
    return pagina.eval_on_selector_all("#lista-agendadas > li:not([hidden])", "els => els.map(e => e.dataset.n)")


def posts_enviados(api):
    return [p for p in api.pedidos if p["metodo"] == "POST"]


def test_rascunho_nao_chama_a_api_e_sobrevive_a_recarregar(navegador, servidor):
    api = ApiFalsa({"4": evento(4, "aprovar", V4), "9": evento(9, "ajustar", "0" * 32, "trocar")})
    ctx = navegador.new_context()
    ctx.add_init_script("try { localStorage.setItem('pastoral-painel-codigo-v1', 'antigo') } catch (e) {}")
    pagina = abrir(navegador, servidor, api, ctx)
    assert api.pedidos[0]["url"].endswith("/api/estado") and api.pedidos[0]["auth"] is None, "GET público, sem código"
    assert pagina.evaluate("localStorage.getItem('pastoral-painel-codigo-v1')") is None, "código antigo apagado"
    # 4 aprovado na versão atual → Aprovadas e Agendadas; 9 teve ajuste numa versão antiga → Pendentes
    assert ids(pagina, "aprovadas") == ["4"] and ids(pagina, "pendentes") == ["7", "9"] and agendadas(pagina) == ["4"]
    assert "mudou depois da resposta" in pagina.inner_text("#item-9 .item-status")
    assert pagina.is_disabled("#enviar")

    pagina.click("#item-9 .btn-aprovar")
    pagina.click("#item-7 [data-acao=ajuste]")
    pagina.fill("#item-7 textarea", "  Trocar a capa.  ")
    pagina.click("#item-7 [data-acao=salvar]")
    pagina.click("#item-4 [data-acao=desfazer]")
    assert posts_enviados(api) == [], "rascunho não grava nada no servidor"
    assert ids(pagina, "aprovadas") == ["9"] and ids(pagina, "ajuste") == ["7"] and ids(pagina, "pendentes") == ["4"]
    assert "A enviar: aprovação" in pagina.inner_text("#item-9 .item-status")
    assert "A enviar: tirar a aprovação" in pagina.inner_text("#item-4 .item-status")
    assert agendadas(pagina) == ["4"], "Agendadas só mostra o que já vale no servidor"
    assert pagina.inner_text("#envio-resumo") == "3 respostas a enviar."
    rascunho = json.loads(pagina.evaluate("localStorage.getItem('pastoral-painel-rascunho-v1')"))
    assert rascunho["7"] == {"acao": "ajustar", "comentario": "Trocar a capa.", "semana": "2026-W40", "versao": V7}

    pagina.reload()
    pagina.wait_for_load_state("networkidle")
    for b in pagina.locator(".bloco-botao").all():
        b.click()
    assert ids(pagina, "aprovadas") == ["9"] and ids(pagina, "ajuste") == ["7"] and ids(pagina, "pendentes") == ["4"]
    pagina.click("#item-4 [data-acao=descartar]")
    assert ids(pagina, "aprovadas") == ["4", "9"] and pagina.inner_text("#envio-resumo") == "2 respostas a enviar."
    assert posts_enviados(api) == []
    ctx.close()


def test_codigo_errado_e_bloqueio_param_o_envio_sem_perder_o_rascunho(navegador, servidor):
    api = ApiFalsa({})
    pagina = abrir(navegador, servidor, api)
    pagina.click("#item-4 .btn-aprovar")
    pagina.click("#item-7 .btn-aprovar")
    pagina.click("#enviar")
    pagina.fill("#codigo", "xyzw")
    pagina.click("#confirmar")
    pagina.wait_for_selector("#dialogo-aviso:has-text('Código errado')")
    assert len(posts_enviados(api)) == 1, "para no primeiro 401"
    assert posts_enviados(api)[0]["auth"] == "Bearer xyzw"
    assert pagina.input_value("#codigo") == "", "o código digitado é apagado"
    assert ids(pagina, "aprovadas") == ["4", "7"] and pagina.inner_text("#envio-resumo") == "2 respostas a enviar."
    api.bloqueado = True
    pagina.fill("#codigo", CODIGO)
    pagina.click("#confirmar")
    pagina.wait_for_selector("#dialogo-aviso:has-text('Bloqueado')")
    assert pagina.inner_text("#envio-resumo") == "2 respostas a enviar."
    assert "Xyzw" not in (pagina.evaluate("JSON.stringify(localStorage)")), "o código nunca é guardado"
    pagina.context.close()


def test_codigo_certo_envia_cada_post_e_mostra_o_que_falhou(navegador, servidor):
    api = ApiFalsa({"4": evento(4, "aprovar", V4)}, conflito={9})
    pagina = abrir(navegador, servidor, api)
    pagina.click("#item-9 .btn-aprovar")
    pagina.click("#item-7 [data-acao=ajuste]")
    pagina.fill("#item-7 textarea", "Trocar a capa.")
    pagina.click("#item-7 [data-acao=salvar]")
    pagina.click("#item-4 [data-acao=desfazer]")
    pagina.click("#enviar")
    pagina.fill("#codigo", CODIGO)
    pagina.click("#confirmar")
    pagina.wait_for_selector("#envio-resultado:not([hidden])")
    enviados = posts_enviados(api)
    assert [p["corpo"]["decisoes"] for p in enviados] == [
        [{"semana": "2026-W40", "post": 4, "acao": "desfazer"}],
        [{"semana": "2026-W40", "post": 7, "acao": "ajustar", "comentario": "Trocar a capa."}],
        [{"semana": "2026-W40", "post": 9, "acao": "aprovar", "versao": V9}],
    ], "um post por pedido, na ordem"
    assert all(p["auth"] == f"Bearer {CODIGO}" and CODIGO not in p["url"] for p in enviados)
    resultado = pagina.inner_text("#envio-resultado")
    assert "2 respostas enviadas e gravadas." in resultado and "Publicação 9: não enviada" in resultado
    assert ids(pagina, "ajuste") == ["7"] and ids(pagina, "pendentes") == ["4"] and ids(pagina, "aprovadas") == ["9"]
    assert "A enviar: aprovação" in pagina.inner_text("#item-9 .item-status"), "o que falhou continua a enviar"
    assert "Não foi enviado" in pagina.inner_text("#item-9 .item-aviso")
    assert "Ajuste pedido por Aprovador" in pagina.inner_text("#item-7 .item-status")
    assert agendadas(pagina) == []
    assert pagina.inner_text("#envio-resumo") == "1 resposta a enviar."
    assert not pagina.is_visible("#dialogo-codigo")
    pagina.context.close()


# ---------- celular de verdade (emulação de dispositivo: viewport, isMobile, hasTouch, userAgent) ----------

@pytest.mark.parametrize("motor,aparelho", [("webkit", "iPhone 13"), ("webkit", "iPhone SE"), ("chromium", "Pixel 7")])
def test_celular_botao_aprovacoes_leva_ao_painel_e_fluxo_por_toque(pw_motores, servidor, motor, aparelho):
    """Regressão do bug do celular: no Safari/iOS, tocar em "Aprovações" voltava ao topo (popstate →
    fechar() → rolarPara(0)). Agora o botão leva ao painel, abre Pendentes e o fluxo inteiro funciona por toque."""
    try:
        nav = getattr(pw_motores, motor).launch()
    except Exception as erro:
        pytest.skip(f"{motor} indisponível: {erro}")
    ctx = nav.new_context(**pw_motores.devices[aparelho])
    api = ApiFalsa({})
    pagina = ctx.new_page()
    pagina.route(f"{API}/**", api)
    pagina.goto(servidor.replace("/aprovacao/", "/aprovacao-longa/"))
    pagina.wait_for_load_state("networkidle")
    assert pagina.evaluate("document.getElementById('painel').getBoundingClientRect().top") > pagina.viewport_size["height"]
    assert pagina.is_visible("#ir-painel"), "botão fixo visível enquanto o painel está fora da tela"
    pagina.tap("#ir-painel")
    pagina.wait_for_timeout(300)
    topo = pagina.evaluate("document.getElementById('painel').getBoundingClientRect().top")
    assert abs(topo) < 5, f"o painel devia estar no topo da tela, está em {topo}"
    assert pagina.evaluate("scrollY") > 0
    assert pagina.is_visible("#item-4 .btn-aprovar"), "Pendentes aberto pelo botão"
    assert not pagina.is_visible("#ir-painel"), "com o painel na tela, o botão fixo some e não cobre o Enviar"
    pagina.tap("#item-4 .btn-aprovar")
    assert pagina.is_visible("#enviar") and pagina.is_enabled("#enviar")
    pagina.locator("#enviar").scroll_into_view_if_needed()
    pagina.tap("#enviar")
    pagina.tap("#codigo")
    pagina.fill("#codigo", CODIGO)
    pagina.tap("#confirmar")
    pagina.wait_for_selector("#envio-resultado:not([hidden])")
    assert "1 resposta enviada e gravada." in pagina.inner_text("#envio-resultado")
    assert [p["corpo"]["decisoes"][0]["post"] for p in posts_enviados(api)] == [4]
    ctx.close()
    nav.close()
