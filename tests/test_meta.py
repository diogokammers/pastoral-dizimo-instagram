"""Fatia 7 — cliente mínimo da Meta (Instagram API with Instagram Login). Nenhum teste chama a rede."""
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from pastoral import meta

TOKEN = "IGAAtokenSecreto123"


class Transporte:
    """Transporte falso: registra pedidos e devolve respostas pré-programadas (status, dict)."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.pedidos = []

    def __call__(self, metodo, url, dados):
        corpo = parse_qs(dados.decode("utf-8")) if dados else {}
        self.pedidos.append({"metodo": metodo, "url": url, "corpo": corpo,
                             "query": parse_qs(urlsplit(url).query), "caminho": urlsplit(url).path})
        status, resposta = self.respostas.pop(0)
        return status, json.dumps(resposta).encode("utf-8")


def cliente(respostas, **kw):
    t = Transporte(respostas)
    c = meta.ClienteMeta(TOKEN, "1789", versao="v26.0", transporte=t,
                         dormir=kw.pop("dormir", lambda s: None), **kw)
    return c, t


def test_criar_item_de_carrossel():
    c, t = cliente([(200, {"id": "c1"})])
    assert c.criar_item_carrossel("https://x/a.jpg", alt_text="Capa") == "c1"
    p = t.pedidos[0]
    assert p["metodo"] == "POST"
    assert p["url"].startswith("https://graph.instagram.com/v26.0/1789/media")
    assert p["corpo"]["image_url"] == ["https://x/a.jpg"]
    assert p["corpo"]["is_carousel_item"] == ["true"]
    assert p["corpo"]["alt_text"] == ["Capa"]
    assert p["corpo"]["access_token"] == [TOKEN]
    assert TOKEN not in p["url"]          # POST: token só no corpo, nunca na URL


def test_criar_carrossel():
    c, t = cliente([(200, {"id": "car"})])
    assert c.criar_carrossel(["c1", "c2"], "Legenda") == "car"
    corpo = t.pedidos[0]["corpo"]
    assert corpo["media_type"] == ["CAROUSEL"]
    assert corpo["children"] == ["c1,c2"]
    assert corpo["caption"] == ["Legenda"]


def test_criar_carrossel_recusa_mais_de_10_ou_menos_de_2():
    c, _ = cliente([])
    with pytest.raises(meta.ErroMeta):
        c.criar_carrossel([str(i) for i in range(11)], "x")
    with pytest.raises(meta.ErroMeta):
        c.criar_carrossel(["so1"], "x")


def test_aguardar_ate_finished():
    esperas = []
    c, t = cliente([(200, {"status_code": "IN_PROGRESS"}), (200, {"status_code": "FINISHED"})],
                   dormir=esperas.append)
    c.aguardar("c1", intervalo=60, maximo=300)
    assert t.pedidos[0]["query"]["fields"] == ["status_code"]
    assert t.pedidos[0]["caminho"] == "/v26.0/c1"
    assert esperas == [60]


def test_aguardar_erro_e_timeout():
    c, _ = cliente([(200, {"status_code": "ERROR"})])
    with pytest.raises(meta.ErroMeta, match="ERROR"):
        c.aguardar("c1", intervalo=60, maximo=300)
    c, _ = cliente([(200, {"status_code": "IN_PROGRESS"})] * 10)
    with pytest.raises(meta.ErroMeta, match="tempo"):
        c.aguardar("c1", intervalo=60, maximo=120)


def test_media_publish_e_permalink():
    c, t = cliente([(200, {"id": "m9"}), (200, {"id": "m9", "permalink": "https://www.instagram.com/p/X/"})])
    assert c.media_publish("car") == "m9"
    assert t.pedidos[0]["caminho"] == "/v26.0/1789/media_publish"
    assert t.pedidos[0]["corpo"]["creation_id"] == ["car"]
    assert c.permalink("m9") == "https://www.instagram.com/p/X/"


def test_refresh_access_token():
    c, t = cliente([(200, {"access_token": "novo", "token_type": "bearer", "expires_in": 5184000})])
    r = c.refresh_access_token()
    assert r["access_token"] == "novo"
    p = t.pedidos[0]
    assert p["metodo"] == "GET"
    assert p["caminho"] == "/refresh_access_token"
    assert p["query"]["grant_type"] == ["ig_refresh_token"]


def test_verificar_faz_so_get_me():
    c, t = cliente([(200, {"user_id": "1789", "username": "pastoraldodizimo.arquifln"})])
    assert c.me()["username"] == "pastoraldodizimo.arquifln"
    assert t.pedidos[0]["metodo"] == "GET"
    assert t.pedidos[0]["caminho"] == "/v26.0/me"
    assert t.pedidos[0]["query"]["fields"] == ["user_id,username"]


def test_erro_http_mascara_o_token():
    c, _ = cliente([(400, {"error": {"message": f"Invalid token {TOKEN}", "code": 190}})])
    with pytest.raises(meta.ErroMeta) as erro:
        c.me()
    texto = str(erro.value)
    assert TOKEN not in texto
    assert "***" in texto
    assert "190" in texto


def test_falha_de_rede_mascara_o_token():
    def quebra(metodo, url, dados):
        raise OSError(f"falhou ao abrir {url}")
    c = meta.ClienteMeta(TOKEN, "1789", transporte=quebra)
    with pytest.raises(meta.ErroMeta) as erro:
        c.me()
    assert TOKEN not in str(erro.value)


def test_repr_nao_mostra_token():
    c, _ = cliente([])
    assert TOKEN not in repr(c)
    assert TOKEN not in str(vars(c).get("versao", ""))


def test_mascarar():
    assert meta.mascarar(f"a {TOKEN} b", TOKEN) == "a *** b"
    assert meta.mascarar("sem token", "") == "sem token"


def test_do_ambiente_exige_variaveis(monkeypatch):
    monkeypatch.delenv("IG_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("IG_USER_ID", raising=False)
    with pytest.raises(meta.ErroMeta, match="IG_ACCESS_TOKEN"):
        meta.ClienteMeta.do_ambiente({})
    monkeypatch.setenv("IG_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("IG_USER_ID", "1789")
    c = meta.ClienteMeta.do_ambiente({"meta": {"versao_api": "v99.0"}})
    assert c.versao == "v99.0"


def test_config_tem_meta_e_midia(raiz):
    import yaml
    config = yaml.safe_load((raiz / "config.yaml").read_text(encoding="utf-8"))
    assert config["meta"]["host"] == "https://graph.instagram.com"
    assert config["meta"]["versao_api"].startswith("v")
    assert config["midia"]["base_url"] == "https://diogokammers.github.io/pastoral-dizimo-instagram/"
    assert config["midia"]["pasta"] == "site/midia"


def test_cli_verificar(monkeypatch, capsys):
    monkeypatch.setenv("IG_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("IG_USER_ID", "1789")
    t = Transporte([(200, {"user_id": "1789", "username": "pastoraldodizimo.arquifln"})])
    monkeypatch.setattr(meta, "transporte_urllib", t)
    assert meta.main(["--verificar"]) == 0
    saida = capsys.readouterr().out
    assert "pastoraldodizimo.arquifln" in saida
    assert TOKEN not in saida
    assert len(t.pedidos) == 1 and t.pedidos[0]["metodo"] == "GET"


def test_cli_renovar_grava_arquivo_sem_imprimir(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("IG_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("IG_USER_ID", "1789")
    t = Transporte([(200, {"access_token": "tokenNovo456", "expires_in": 5184000})])
    monkeypatch.setattr(meta, "transporte_urllib", t)
    destino = tmp_path / "novo.txt"
    assert meta.main(["--renovar", "--saida", str(destino)]) == 0
    assert destino.read_text(encoding="utf-8") == "tokenNovo456"
    saida = capsys.readouterr()
    assert "tokenNovo456" not in saida.out + saida.err
    assert TOKEN not in saida.out + saida.err
    assert "60" in saida.out            # dias de validade
