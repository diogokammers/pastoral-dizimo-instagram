"""ADR-013 — a página de links num navegador de verdade (Playwright), celular WebKit e Chromium, com a API simulada.

Confere: os dois botões abrem o formulário certo (e o "voltar" volta); "Outra" mostra o campo da paróquia;
pedido de capacitação torna o contato obrigatório; sem consentimento não envia; envio certo mostra o
agradecimento e manda o JSON esperado; 429 e 500 mostram aviso e preservam o texto digitado.
Pula se o Playwright ou o navegador não estiverem instalados.
"""
import functools
import http.server
import json
import threading
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PUBLICO = Path(__file__).resolve().parent.parent / "links" / "public"
PAROQUIA = "Tijucas - São Sebastião"


@pytest.fixture(scope="module")
def servidor():
    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(PUBLICO)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()


@pytest.fixture(scope="module")
def pw():
    p = sync_api.sync_playwright().start()
    yield p
    p.stop()


APARELHOS = [("webkit", "iPhone 13"), ("chromium", "Pixel 7")]


@pytest.fixture(params=APARELHOS, ids=[a for _, a in APARELHOS])
def pagina(request, pw, servidor):
    motor, aparelho = request.param
    try:
        nav = getattr(pw, motor).launch()
    except Exception as erro:
        pytest.skip(f"{motor} indisponível: {erro}")
    ctx = nav.new_context(**pw.devices[aparelho])
    pg = ctx.new_page()
    pg.route("https://fonts.googleapis.com/**", lambda r: r.abort())
    pg.route("https://fonts.gstatic.com/**", lambda r: r.abort())
    pg.api = {"status": 200, "corpo": {"ok": True}, "pedidos": []}

    def api(route):
        pg.api["pedidos"].append(json.loads(route.request.post_data))
        route.fulfill(status=pg.api["status"], json=pg.api["corpo"])

    pg.route("**/api/resposta", api)
    pg.goto(servidor)
    yield pg
    ctx.close()
    nav.close()


def abrir(pg, botao):
    """Toca o botão e espera o formulário (a troca de #hash é assíncrona)."""
    pg.tap(f"text={botao}")
    pg.wait_for_selector("#formulario:not([hidden]) #f-paroquia")


def preencher_agente(pg, pedido="Dificuldade na pastoral"):
    abrir(pg, "Sou agente da Pastoral")
    pg.select_option("#f-paroquia", PAROQUIA)
    pg.select_option("#f-funcao", "Coordenador(a)")
    pg.select_option("#f-pedido", pedido)
    pg.check("input[name=temas][value='Prestação de contas e transparência']")
    pg.fill("#f-descricao", "Precisamos de ajuda para apresentar os resultados.")


def test_botoes_abrem_o_formulario_certo_e_voltar(pagina):
    abrir(pagina, "Sou fiel")
    assert pagina.inner_text("#form-titulo") == "Fiel"
    assert pagina.locator("#f-assunto").is_visible()
    pagina.tap("#voltar")
    pagina.wait_for_selector("#inicio:not([hidden])")
    abrir(pagina, "Sou agente da Pastoral")
    assert pagina.inner_text("#form-titulo") == "Agente da Pastoral"
    assert pagina.locator("input[name=temas]").count() == 13


def test_outra_paroquia_mostra_o_campo(pagina):
    abrir(pagina, "Sou fiel")
    assert not pagina.locator("#c-paroquia_outra").is_visible()
    pagina.select_option("#f-paroquia", "Outra")
    assert pagina.locator("#c-paroquia_outra").is_visible()


def test_capacitacao_exige_contato_e_consentimento_exigido(pagina):
    preencher_agente(pagina, "Pedido de capacitação")
    assert "precisamos saber como falar com você" in pagina.inner_text("#ajuda-contato")
    pagina.tap("#enviar")
    assert pagina.api["pedidos"] == []
    for campo in ("nome", "contato", "consentimento"):
        assert pagina.locator(f"#erro-{campo}").is_visible(), campo
    pagina.fill("#f-nome", "Ana")
    pagina.fill("#f-contato", "ana@exemplo.test")
    pagina.check("#consentimento")
    pagina.tap("#enviar")
    pagina.wait_for_selector("#obrigado:not([hidden])")
    enviado = pagina.api["pedidos"][0]
    assert enviado["tipo"] == "agente" and enviado["pedido"] == "Pedido de capacitação"
    assert enviado["temas"] == ["Prestação de contas e transparência"]
    assert enviado["consentimento"] is True and enviado["site"] == ""


def test_fiel_anonimo_envia(pagina):
    abrir(pagina, "Sou fiel")
    pagina.select_option("#f-assunto", "Dúvida sobre o dízimo")
    pagina.fill("#f-mensagem", "Como faço o cadastro?")
    pagina.check("#consentimento")
    pagina.tap("#enviar")
    pagina.wait_for_selector("#obrigado:not([hidden])")
    assert pagina.api["pedidos"][0]["nome"] == "" and pagina.api["pedidos"][0]["paroquia"] == ""


@pytest.mark.parametrize("status,trecho", [(429, "Muitos envios"), (500, "Seu texto continua aqui")])
def test_erro_da_api_avisa_e_preserva_o_texto(pagina, status, trecho):
    pagina.api.update(status=status, corpo={"ok": False})
    preencher_agente(pagina)
    pagina.check("#consentimento")
    pagina.tap("#enviar")
    pagina.wait_for_selector("#aviso:not([hidden])")
    assert trecho in pagina.inner_text("#aviso")
    assert pagina.input_value("#f-descricao").startswith("Precisamos de ajuda")
    assert pagina.locator("#formulario").is_visible()
    assert pagina.is_enabled("#enviar")
