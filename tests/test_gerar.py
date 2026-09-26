"""Fatia 3 — gerar.py com o LLM mockado (o CLI não está logado nesta máquina)."""
import json

import pytest

from pastoral import gerar, lint
from test_lint import post_valido


@pytest.fixture
def config(raiz):
    return lint.carregar_config(raiz / "config.yaml")


@pytest.fixture
def schema(raiz):
    return raiz / "schemas/posts.schema.json"


BRIEFING = {"semana": "2026-W41", "posts": [{"numero": 2, "titulo": "O que é o dízimo?", "pilar": "Formação"}]}


def envelope(dados: dict | str, erro: bool = False) -> str:
    """Imita o stdout de `claude -p --output-format json`."""
    resultado = dados if isinstance(dados, str) else "```json\n" + json.dumps(dados, ensure_ascii=False) + "\n```"
    return json.dumps({"is_error": erro, "result": resultado,
                       "usage": {"input_tokens": 10, "output_tokens": 20}, "total_cost_usd": 0.01})


def test_prompt_leva_cartao_briefing_e_schema():
    p = gerar.montar_prompt(BRIEFING, "CARTAO-XYZ", {"title": "SCHEMA-XYZ"})
    assert "CARTAO-XYZ" in p and "SCHEMA-XYZ" in p and "O que é o dízimo?" in p


def test_prompt_de_revisao_inclui_erros():
    p = gerar.montar_prompt(BRIEFING, "c", {}, erros=["post 2: termo proibido \"taxa\""])
    assert "termo proibido" in p


def test_extrair_json_de_bloco_markdown():
    assert gerar.extrair_json('texto antes\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extrair_json_puro():
    assert gerar.extrair_json('{"a": {"b": 2}}') == {"a": {"b": 2}}


def test_gera_na_primeira_tentativa(config, schema):
    chamadas = []

    def falso(prompt, modelo):
        chamadas.append(prompt)
        return envelope({"lote": "2026-W41", "posts": [post_valido()]})

    r = gerar.gerar(BRIEFING, "cartão", schema, config, executar=falso)
    assert r["erros"] == [] and r["tentativas"] == 1 and len(chamadas) == 1
    assert r["dados"]["posts"][0]["numero"] == 2
    assert r["uso"][0]["output_tokens"] == 20


def test_regenera_uma_vez_quando_lint_reprova(config, schema):
    ruim = post_valido()
    ruim["legenda"] = "Não é taxa.\n\nPastoral do Dízimo — Arquidiocese de Florianópolis"
    respostas = [envelope({"lote": "x", "posts": [ruim]}), envelope({"lote": "x", "posts": [post_valido()]})]
    prompts = []

    def falso(prompt, modelo):
        prompts.append(prompt)
        return respostas.pop(0)

    r = gerar.gerar(BRIEFING, "cartão", schema, config, executar=falso)
    assert r["tentativas"] == 2 and r["erros"] == []
    assert "taxa" in prompts[1]


def test_devolve_erros_se_continuar_reprovado(config, schema):
    ruim = post_valido()
    ruim["cta"] = "doar"

    def falso(prompt, modelo):
        return envelope({"lote": "x", "posts": [ruim]})

    r = gerar.gerar(BRIEFING, "cartão", schema, config, executar=falso)
    assert r["tentativas"] == 2 and any("CTA" in e for e in r["erros"])


def test_erro_do_cli_levanta_excecao(config, schema):
    def falso(prompt, modelo):
        return envelope("Failed to authenticate", erro=True)

    with pytest.raises(gerar.ErroGeracao, match="authenticate"):
        gerar.gerar(BRIEFING, "cartão", schema, config, executar=falso)
