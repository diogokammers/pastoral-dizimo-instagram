"""Pacote de estreia (ADR-005): os 3 posts fixados passam no schema e no lint, e a bio cabe no limite."""
import json
import re

import pytest

from pastoral import lint


@pytest.fixture
def dados(raiz):
    return json.loads((raiz / "content/estreia/posts.json").read_text(encoding="utf-8"))


def test_estreia_passa_no_schema(dados, raiz):
    assert lint.validar_schema(dados, raiz / "schemas/posts.schema.json") == []


def test_estreia_passa_no_lint(dados, raiz):
    assert lint.verificar_lote(dados, lint.carregar_config(raiz / "config.yaml")) == []


def test_estreia_tem_os_tres_fixados(dados):
    assert [p["numero"] for p in dados["posts"]] == [1, 2, 3]
    assert all(p["formato"] == "carrossel" for p in dados["posts"])


def test_estreia_sao_fixados_e_usam_tema_vermelho(dados):
    from pastoral import render
    assert all(p.get("fixado") is True for p in dados["posts"])
    assert {render.tema_do_post(p) for p in dados["posts"]} == {"vermelho"}


def test_schema_aceita_importante_e_fixado_booleanos(dados, raiz):
    import copy
    lote = copy.deepcopy(dados)
    lote["posts"][0]["importante"] = True
    assert lint.validar_schema(lote, raiz / "schemas/posts.schema.json") == []
    lote["posts"][0]["importante"] = "sim"
    assert lint.validar_schema(lote, raiz / "schemas/posts.schema.json") != []


def test_render_da_estreia_sem_destaque_paroquias(raiz):
    pasta = raiz / "content/estreia/render"
    assert not (pasta / "destaque-paroquias.jpg").exists()
    assert len(list(pasta.glob("destaque-*.jpg"))) == 5


def test_post3_tem_as_quatro_dimensoes_sem_doc106(dados):
    p = dados["posts"][2]
    post3 = json.dumps([p["slides"], p["legenda"]], ensure_ascii=False)  # só o que o público lê
    for d in ["religiosa", "eclesial", "missionária", "caritativa"]:
        assert d in post3.lower()
    assert "106" not in post3 and "social" not in post3.lower()


def test_bio_ate_150_caracteres(raiz):
    """Cada proposta de bio (blocos ```text) cabe no limite do Instagram."""
    bio = (raiz / "content/estreia/bio.md").read_text(encoding="utf-8")
    blocos = re.findall(r"```text\n(.*?)\n```", bio, re.DOTALL)
    assert len(blocos) >= 2
    for b in blocos:
        assert len(b) <= 150, (len(b), b)
