"""Fatias 5/6 — regras comuns da aprovação por e-mail (ADR-009), espelhadas no Worker (worker/src/nucleo.js).

Os vetores em tests/fixtures/vetores-python.json são gerados por este módulo e verificados no JS;
a aprovação gerada pelo Worker (tests/fixtures/semana-exemplo/aprovacao-worker.json) é verificada aqui.
"""
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pastoral import aprovacao, publicar

FIXTURE = Path(__file__).parent / "fixtures" / "semana-exemplo"
SEMANA = "2026-W41"
SEGREDO_LINK = "segredo-link-de-teste"
SEGREDO_APROV = "segredo-aprovacao-de-teste"


def ler(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture
def posts():
    return ler(FIXTURE / "content" / "semanas" / SEMANA / "posts.json")


@pytest.fixture
def agenda():
    return ler(FIXTURE / "content" / "semanas" / SEMANA / "agenda.json")


def ler_arte(arquivo):
    return (FIXTURE / "site" / "midia" / SEMANA / arquivo).read_bytes()


# ---------- agenda ----------

def test_agendado_para_usa_fuso_do_briefing():
    item = {"data": "2026-10-06", "hora": "19:00", "fuso": "America/Sao_Paulo"}
    assert aprovacao.agendado_para(item) == "2026-10-06T19:00:00-03:00"


def test_montar_agenda_liga_indice_do_briefing_ao_numero_do_post(posts):
    briefing = {"semana": SEMANA, "posts": [
        {"indice": 12, "data": "2026-10-06", "hora": "19:00", "fuso": "America/Sao_Paulo"},
        {"indice": 13, "data": "2026-10-09", "hora": "19:00", "fuso": "America/Sao_Paulo"}]}
    agenda = aprovacao.montar_agenda(SEMANA, posts, briefing)
    assert agenda["semana"] == SEMANA
    assert [p["numero"] for p in agenda["posts"]] == [12, 13]
    assert agenda["posts"][0]["agendado_para"] == "2026-10-06T19:00:00-03:00"
    assert agenda["posts"][0]["artes"] == ["post-12-01.jpg", "post-12-02.jpg"]
    assert agenda["posts"][1]["artes"] == ["post-13-01.jpg"]


def test_montar_agenda_recusa_post_sem_data(posts):
    with pytest.raises(ValueError, match="13"):
        aprovacao.montar_agenda(SEMANA, posts, {"posts": [
            {"indice": 12, "data": "2026-10-06", "hora": "19:00", "fuso": "America/Sao_Paulo"}]})


# ---------- itens e versão ----------

def test_itens_semana_batem_com_o_portao(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    assert [i["numero"] for i in itens] == [12, 13]
    p12 = next(p for p in posts["posts"] if p["numero"] == 12)
    assert itens[0]["legenda_sha256"] == publicar.sha256(publicar.texto_legenda(p12).encode("utf-8"))
    assert itens[0]["alt_text_sha256"] == publicar.sha256(publicar.texto_alt(p12).encode("utf-8"))
    assert itens[0]["artes"][1] == {"arquivo": "post-12-02.jpg", "sha256": publicar.sha256(ler_arte("post-12-02.jpg"))}
    assert set(itens[0]) == {"numero", "agendado_para", "legenda_sha256", "alt_text_sha256", "artes"}


def test_itens_semana_recusa_artes_diferentes_dos_slides(posts, agenda):
    agenda["posts"][0]["artes"] = ["post-12-01.jpg"]
    with pytest.raises(ValueError, match="slides"):
        aprovacao.itens_semana(agenda, posts, ler_arte)


def test_versao_muda_se_um_byte_da_arte_muda(posts, agenda):
    v1 = aprovacao.versao(SEMANA, aprovacao.itens_semana(agenda, posts, ler_arte))
    v2 = aprovacao.versao(SEMANA, aprovacao.itens_semana(agenda, posts, lambda a: ler_arte(a) + b"x"))
    assert len(v1) == 32 and v1 != v2


# ---------- links assinados ----------

def params_validos(**troca):
    base = {"s": SEMANA, "a": "aprovar_post", "p": "12", "e": "1791000000", "n": "a1b2c3d4e5f60718",
            "v": "0" * 32}
    base.update(troca)
    base["h"] = aprovacao.assinar_link(SEGREDO_LINK, base)
    return base


AGORA = 1790000000


def test_link_valido():
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params_validos(), AGORA) is None


@pytest.mark.parametrize("campo,valor", [("s", "2026-W42"), ("a", "ajustar_post"), ("p", "13"),
                                         ("e", "1791000001"), ("n", "a1b2c3d4e5f60719"), ("v", "1" * 32)])
def test_link_adulterado_em_qualquer_campo_e_recusado(campo, valor):
    params = params_validos()
    params[campo] = valor
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params, AGORA) == "assinatura inválida"


def test_link_expirado():
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params_validos(e=str(AGORA - 1)), AGORA) == "link expirado"


def test_link_com_segredo_errado():
    assert aprovacao.motivo_link_invalido("outro", params_validos(), AGORA) == "assinatura inválida"


@pytest.mark.parametrize("troca", [{"a": "publicar"}, {"s": "2026-41"}, {"p": ""}, {"n": "curto"},
                                   {"v": "xyz"}, {"e": "amanhã"}])
def test_link_malformado(troca):
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params_validos(**troca), AGORA) == "link malformado"


def test_aprovar_tudo_nao_leva_post():
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params_validos(a="aprovar_tudo", p=""), AGORA) is None
    assert aprovacao.motivo_link_invalido(SEGREDO_LINK, params_validos(a="aprovar_tudo"), AGORA) == "link malformado"


def test_segredo_vazio_nunca_valida():
    with pytest.raises(ValueError):
        aprovacao.assinar_link("", params_validos())
    assert aprovacao.motivo_link_invalido("", params_validos(), AGORA) == "segredo ausente"


def test_url_do_link():
    url = aprovacao.url_link("https://w.exemplo.workers.dev/", SEGREDO_LINK, SEMANA, "ajustar_post", 12,
                             1791000000, "a1b2c3d4e5f60718", "0" * 32)
    assert url.startswith("https://w.exemplo.workers.dev/a?s=2026-W41&a=ajustar_post&p=12&e=1791000000&")
    assert "&h=" in url


# ---------- montagem do aprovacao.json (o Worker faz igual) ----------

def test_montar_aprovacao_valida_no_portao(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    dados, mudou = aprovacao.montar_aprovacao(None, SEMANA, itens, [12, 13], "n1", "Diogo",
                                              "2026-10-05T13:00:00+00:00", SEGREDO_APROV)
    assert mudou
    assert list(dados) == ["semana", "aprovado_por", "aprovado_em", "nonce", "posts", "assinatura"]
    assert publicar.assinatura_valida(dados, SEGREDO_APROV)


def test_montar_aprovacao_e_idempotente(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    d1, _ = aprovacao.montar_aprovacao(None, SEMANA, itens, [12], "n1", "Diogo", "t1", SEGREDO_APROV)
    d2, mudou = aprovacao.montar_aprovacao(d1, SEMANA, itens, [12], "n2", "Diogo", "t2", SEGREDO_APROV)
    assert not mudou and d2 is d1
    d3, mudou = aprovacao.montar_aprovacao(d1, SEMANA, itens, [13], "n1", "Diogo", "t3", SEGREDO_APROV)
    assert not mudou, "mesmo nonce (link já usado) não grava de novo"
    d4, mudou = aprovacao.montar_aprovacao(d1, SEMANA, itens, [13], "n3", "Diogo", "t4", SEGREDO_APROV)
    assert mudou and [p["numero"] for p in d4["posts"]] == [12, 13] and d4["nonce"] == "n3"


def test_montar_aprovacao_recusa_post_fora_da_semana(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    with pytest.raises(ValueError):
        aprovacao.montar_aprovacao(None, SEMANA, itens, [99], "n1", "Diogo", "t", SEGREDO_APROV)


# ---------- teste cruzado Python ↔ JS ----------

def test_vetores_python_estao_atualizados():
    """O arquivo que o JS verifica é exatamente o que o Python gera hoje."""
    assert ler(Path(__file__).parent / "fixtures" / "vetores-python.json") == aprovacao.gerar_vetores()


def repo_com_aprovacao(tmp_path, aprov):
    shutil.copytree(FIXTURE, tmp_path / "repo")
    raiz = tmp_path / "repo"
    (raiz / "content" / "semanas" / SEMANA / "aprovacao.json").write_text(
        json.dumps(aprov, ensure_ascii=False), encoding="utf-8")
    return raiz


def test_aprovacao_gerada_pelo_worker_passa_no_portao(tmp_path):
    """Vetor JS → Python: o aprovacao.json que o Worker grava é aceito por publicar.py."""
    aprov = ler(FIXTURE / "aprovacao-worker.json")
    assert publicar.assinatura_valida(aprov, SEGREDO_APROV)
    raiz = repo_com_aprovacao(tmp_path, aprov)
    agora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    prontos, recusados = publicar.avaliar_semana(raiz, raiz / "site" / "midia", SEMANA, SEGREDO_APROV, agora, set())
    assert recusados == [] and [p["numero"] for p in prontos] == [12, 13]


def test_worker_regenera_o_mesmo_vetor(tmp_path):
    """Com Node disponível, roda o Worker de novo e confere que o arquivo versionado não envelheceu."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node indisponível")
    raiz = Path(__file__).resolve().parent.parent
    saida = tmp_path / "aprov.json"
    proc = subprocess.run([node, str(raiz / "worker" / "scripts" / "vetor-worker.mjs"), str(saida)],
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert ler(saida) == ler(FIXTURE / "aprovacao-worker.json")


# ---------- painel (ADR-011): versão de um post e remoção da aprovação ----------

def test_versao_post_muda_com_qualquer_parte_do_item(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    v = aprovacao.versao_post(SEMANA, itens[0])
    assert len(v) == 32 and v == aprovacao.versao_post(SEMANA, dict(itens[0]))
    assert v != aprovacao.versao_post("2026-W42", itens[0])
    assert v != aprovacao.versao_post(SEMANA, {**itens[0], "legenda_sha256": "0" * 64})
    assert v != aprovacao.versao_post(SEMANA, {**itens[0], "agendado_para": "2026-10-07T19:00:00-03:00"})
    assert v != aprovacao.versao_post(SEMANA, itens[1])


def test_remover_da_aprovacao_reassina_sem_o_post(posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    d1, _ = aprovacao.montar_aprovacao(None, SEMANA, itens, [12, 13], "n1", "Diogo", "t1", SEGREDO_APROV)
    d2, mudou = aprovacao.remover_da_aprovacao(d1, SEMANA, 12, "n2", "Aprovador", "t2", SEGREDO_APROV)
    assert mudou and [p["numero"] for p in d2["posts"]] == [13]
    assert d2["aprovado_por"] == "Aprovador" and d2["nonce"] == "n2"
    assert list(d2) == ["semana", "aprovado_por", "aprovado_em", "nonce", "posts", "assinatura"]
    assert publicar.assinatura_valida(d2, SEGREDO_APROV)
    d3, mudou = aprovacao.remover_da_aprovacao(d2, SEMANA, 12, "n3", "Aprovador", "t3", SEGREDO_APROV)
    assert not mudou and d3 is d2, "remover o que não está lá não grava"
    d4, mudou = aprovacao.remover_da_aprovacao(d2, SEMANA, 13, "n4", "Aprovador", "t4", SEGREDO_APROV)
    assert mudou and d4["posts"] == [] and publicar.assinatura_valida(d4, SEGREDO_APROV)
    assert aprovacao.remover_da_aprovacao(None, SEMANA, 12, "n5", "Aprovador", "t5", SEGREDO_APROV) == (None, False)


def test_post_removido_da_aprovacao_e_recusado_pelo_portao(tmp_path, posts, agenda):
    itens = aprovacao.itens_semana(agenda, posts, ler_arte)
    d1, _ = aprovacao.montar_aprovacao(None, SEMANA, itens, [12, 13], "n1", "Aprovador", "t1", SEGREDO_APROV)
    d2, _ = aprovacao.remover_da_aprovacao(d1, SEMANA, 12, "n2", "Aprovador", "t2", SEGREDO_APROV)
    raiz = repo_com_aprovacao(tmp_path, d2)
    agora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    prontos, recusados = publicar.avaliar_semana(raiz, raiz / "site" / "midia", SEMANA, SEGREDO_APROV, agora, set())
    assert [p["numero"] for p in prontos] == [13] and recusados == []
