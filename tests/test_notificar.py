"""Fatia 5 — e-mail semanal pela API HTTP da Resend com links assinados (ADR-009). Rede sempre falsa."""
import json
import shutil
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
import yaml

from pastoral import aprovacao, notificar

FIXTURE = Path(__file__).parent / "fixtures" / "semana-exemplo"
SEMANA = "2026-W41"
SEGREDO = "segredo-link-de-teste"
AGORA = 1790000000
CONFIG = {
    "aprovacao": {"email": "dono@exemplo.org", "remetente": "Pastoral do Dízimo <onboarding@resend.dev>",
                  "worker_url": "https://pastoral-dizimo-aprovacao.exemplo.workers.dev", "validade_dias": 7},
    "midia": {"base_url": "https://exemplo.github.io/repo/"},
}


class TransporteFalso:
    def __init__(self, status=200, corpo=b'{"id": "email-123"}'):
        self.status, self.corpo = status, corpo
        self.pedidos = []

    def __call__(self, url, corpo, headers):
        self.pedidos.append({"url": url, "corpo": json.loads(corpo), "headers": headers})
        return self.status, self.corpo


def proibido(*_):
    pytest.fail("a rede não pode ser chamada neste caso")


@pytest.fixture
def raiz(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "repo")
    return tmp_path / "repo"


def params(url):
    return dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))


def test_config_real_tem_bloco_de_aprovacao(raiz):
    cfg = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))["aprovacao"]
    assert cfg["email"] == "pastoraldodizimo.arquifln@gmail.com"
    assert "onboarding@resend.dev" in cfg["remetente"]
    assert cfg["worker_url"].startswith("https://pastoral-dizimo-aprovacao.")
    assert cfg["validade_dias"] == 7


def test_links_assinados_validos_com_nonce_proprio(raiz):
    prep = notificar.preparar(raiz, SEMANA, CONFIG, SEGREDO, AGORA)
    links = prep["links"]
    todos = [links["aprovar_tudo"]] + [u for p in links["posts"].values() for u in p.values()]
    assert len(todos) == 5
    nonces = set()
    for url in todos:
        assert url.startswith("https://pastoral-dizimo-aprovacao.exemplo.workers.dev/a?")
        p = params(url)
        assert aprovacao.motivo_link_invalido(SEGREDO, p, AGORA) is None
        assert int(p["e"]) == AGORA + 7 * 86400
        assert p["v"] == prep["versao"]
        nonces.add(p["n"])
    assert len(nonces) == 5, "cada link tem nonce próprio (aprovar o 12 não queima o link do 13)"
    assert params(links["posts"][13]["ajustar"])["a"] == "ajustar_post"
    assert params(links["aprovar_tudo"])["p"] == ""


def test_versao_e_a_mesma_que_o_worker_calcula(raiz):
    vetores = json.loads((Path(__file__).parent / "fixtures" / "vetores-python.json").read_text(encoding="utf-8"))
    assert notificar.preparar(raiz, SEMANA, CONFIG, SEGREDO, AGORA)["versao"] == vetores["semana"]["versao"]


def test_corpo_do_email(raiz):
    email = notificar.preparar(raiz, SEMANA, CONFIG, SEGREDO, AGORA)["email"]
    assert email["assunto"] == "Aprovação dos posts da semana 2026-W41"
    html = email["html"]
    assert "O dízimo é gratidão" in html and "Imagem única" in html
    assert "terça-feira, 06/10/2026, 19:00" in html
    assert 'href="https://exemplo.github.io/repo/semanas/2026-W41/"' in html
    assert "Aprovar tudo" in html and "Aprovar post 12" in html and "Pedir ajuste no post 13" in html
    for url in [notificar.preparar(raiz, SEMANA, CONFIG, SEGREDO, AGORA)["links"]["aprovar_tudo"]]:
        assert "&amp;" in html and url.split("&h=")[0].split("?")[0] in html
    hrefs = [unescape(h) for h in html.split('href="')[1:]]
    assert all(h.split('"')[0].startswith("https://") for h in hrefs)
    assert "Vetor de teste" in html            # primeira linha da legenda
    assert "Vetor de teste" in email["texto"] and "https://" in email["texto"]


def test_enviar_resend_monta_pedido_certo():
    t = TransporteFalso()
    email = {"assunto": "A", "html": "<p>x</p>", "texto": "x"}
    assert notificar.enviar_resend("re_teste", CONFIG["aprovacao"], email, transporte=t) == "email-123"
    pedido = t.pedidos[0]
    assert pedido["url"] == "https://api.resend.com/emails"
    assert pedido["corpo"] == {"from": "Pastoral do Dízimo <onboarding@resend.dev>", "to": ["dono@exemplo.org"],
                               "subject": "A", "html": "<p>x</p>", "text": "x"}
    assert pedido["headers"]["Authorization"] == "Bearer re_teste"
    assert "urllib" not in pedido["headers"]["User-Agent"]


def test_erro_da_resend_mascara_a_chave():
    t = TransporteFalso(403, b'{"message": "chave re_segredo invalida"}')
    with pytest.raises(notificar.ErroNotificacao) as erro:
        notificar.enviar_resend("re_segredo", CONFIG["aprovacao"], {"assunto": "A", "html": "h", "texto": "t"}, transporte=t)
    assert "re_segredo" not in str(erro.value) and "403" in str(erro.value)


def escrever_config(raiz, **troca):
    cfg = {**CONFIG, "aprovacao": {**CONFIG["aprovacao"], **troca}}
    (raiz / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return str(raiz / "config.yaml")


def test_dry_run_grava_html_e_nao_envia(raiz, tmp_path, monkeypatch):
    monkeypatch.setattr(notificar, "transporte_urllib", proibido)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("LINK_HMAC_SECRET", raising=False)
    saida = tmp_path / "email.html"
    codigo = notificar.main([SEMANA, "--dry-run", "--saida", str(saida), "--raiz", str(raiz),
                             "--config", escrever_config(raiz)])
    assert codigo == 0
    assert "Aprovar tudo" in saida.read_text(encoding="utf-8")


def test_envio_real_sem_chave_falha_claro(raiz, monkeypatch, capsys):
    monkeypatch.setattr(notificar, "transporte_urllib", proibido)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("LINK_HMAC_SECRET", SEGREDO)
    assert notificar.main([SEMANA, "--raiz", str(raiz), "--config", escrever_config(raiz)]) == 1
    assert "RESEND_API_KEY" in capsys.readouterr().err


def test_envio_real_com_worker_placeholder_falha(raiz, monkeypatch, capsys):
    monkeypatch.setattr(notificar, "transporte_urllib", proibido)
    monkeypatch.setenv("RESEND_API_KEY", "re_teste")
    monkeypatch.setenv("LINK_HMAC_SECRET", SEGREDO)
    cfg = escrever_config(raiz, worker_url="https://pastoral-dizimo-aprovacao.SEU-SUBDOMINIO.workers.dev")
    assert notificar.main([SEMANA, "--raiz", str(raiz), "--config", cfg]) == 1
    assert "worker_url" in capsys.readouterr().err


def test_envio_real_com_transporte_falso(raiz, monkeypatch, capsys):
    t = TransporteFalso()
    monkeypatch.setattr(notificar, "transporte_urllib", t)
    monkeypatch.setenv("RESEND_API_KEY", "re_teste\r\n")
    monkeypatch.setenv("LINK_HMAC_SECRET", SEGREDO + "\n")      # quebra de linha colada no secret é ignorada
    assert notificar.main([SEMANA, "--raiz", str(raiz), "--config", escrever_config(raiz)]) == 0
    assert len(t.pedidos) == 1 and t.pedidos[0]["headers"]["Authorization"] == "Bearer re_teste"
    saida = capsys.readouterr().out
    assert "email-123" in saida and "re_teste" not in saida
    html = t.pedidos[0]["corpo"]["html"]
    url = unescape(html.split('href="')[2].split('"')[0])
    assert aprovacao.motivo_link_invalido(SEGREDO, params(url), AGORA) is None
