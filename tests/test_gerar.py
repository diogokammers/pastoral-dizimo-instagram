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
    assert r["tentativas"] == 3 and any("CTA" in e for e in r["erros"])


def test_erro_do_cli_levanta_excecao(config, schema):
    def falso(prompt, modelo):
        return envelope("Failed to authenticate", erro=True)

    with pytest.raises(gerar.ErroGeracao, match="authenticate"):
        gerar.gerar(BRIEFING, "cartão", schema, config, executar=falso)


# ---------- formato real do CLI, briefing imposto, alias do modelo e métricas ----------

def envelope_real(dados: dict, duracao_ms: int = 1234) -> str:
    """Formato real de `claude -p --output-format json` (CLI 2.1.x): um objeto `type: result`."""
    return json.dumps({
        "type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
        "duration_ms": duracao_ms, "duration_api_ms": 1000, "session_id": "abc",
        "result": "Aqui está.\n\n```json\n" + json.dumps(dados, ensure_ascii=False) + "\n```\n",
        "total_cost_usd": 0.5, "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "cache_creation_input_tokens": 5, "cache_read_input_tokens": 7,
                  "output_tokens": 900, "server_tool_use": {"web_search_requests": 0}},
        "modelUsage": {"claude-opus-5-5": {"inputTokens": 100}},
    })


BRIEFING_RESERVA = {"semana": "2026-W40", "posts": [
    {"indice": 4, "tema": 6, "titulo": "Quem é o agente?", "pilar": "Vida pastoral", "fixado": False},
    {"indice": 5, "tema": 4, "titulo": "Dízimo x Oferta", "pilar": "Formação", "fixado": False, "importante": True},
]}


def test_envelope_real_do_cli(config, schema):
    r = gerar.gerar(BRIEFING, "c", schema, config,
                    executar=lambda p, m: envelope_real({"lote": "2026-W41", "posts": [post_valido()]}))
    assert r["erros"] == [] and r["dados"]["posts"][0]["numero"] == 2
    uso = r["uso"][0]
    assert uso["input_tokens"] == 100 and uso["output_tokens"] == 900
    assert uso["cache_read_input_tokens"] == 7 and uso["custo_usd"] == 0.5 and uso["duracao_ms"] == 1234
    assert uso["modelo"] == config["geracao"]["modelo"]


def test_envelope_em_lista_pega_o_result(config, schema):
    """Com --verbose o CLI devolve a lista de mensagens; o `type: result` é o que vale."""
    lista = json.dumps([{"type": "system"}, json.loads(envelope_real({"lote": "x", "posts": [post_valido()]}))])
    r = gerar.gerar(BRIEFING, "c", schema, config, executar=lambda p, m: lista)
    assert r["erros"] == []


def test_briefing_impoe_numero_e_fundo(config, schema):
    """numero = indice global (4, 5…); fixado sempre do briefing (creme); importante só se o briefing marcar."""
    a, b = post_valido(), post_valido()
    a.update(numero=6, fixado=True)          # o modelo usou o número do tema e marcou fixado
    b.update(numero=99, importante=False)
    r = gerar.gerar(BRIEFING_RESERVA, "c", schema, config,
                    executar=lambda p, m: envelope_real({"lote": "2026-W40", "posts": [a, b]}))
    p4, p5 = r["dados"]["posts"]
    assert (p4["numero"], p4["fixado"], "importante" in p4) == (4, False, False)
    assert (p5["numero"], p5["fixado"], p5["importante"]) == (5, False, True)


def test_modelo_inexistente_cai_para_o_alias(config, schema):
    modelos = []

    def falso(prompt, modelo):
        modelos.append(modelo)
        if modelo == config["geracao"]["modelo"]:
            return json.dumps({"type": "result", "is_error": True,
                               "result": "There's an issue with the selected model (x). It may not exist "
                                         "or you may not have access to it."})
        return envelope_real({"lote": "x", "posts": [post_valido()]})

    r = gerar.gerar(BRIEFING, "c", schema, config, executar=falso)
    assert modelos == [config["geracao"]["modelo"], config["geracao"]["alias"]]
    assert r["erros"] == [] and r["modelo"] == config["geracao"]["alias"]


def test_alias_do_modelo_no_config(config):
    assert config["geracao"]["alias"] == "opus"


def test_cli_com_falha_sem_stdout_vira_erro_legivel(monkeypatch):
    import subprocess

    def run_falso(cmd, **kw):
        assert cmd[:4] == ["claude", "-p", "--output-format", "json"] and "--model" in cmd
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error: unknown option")

    monkeypatch.setattr(gerar.subprocess, "run", run_falso)
    env = json.loads(gerar.executar_claude("oi", "opus"))
    assert env["is_error"] is True and "unknown option" in env["result"]


def test_main_grava_posts_e_metricas(tmp_path, monkeypatch):
    pasta = tmp_path / "2026-W40"
    pasta.mkdir()
    (pasta / "briefing.json").write_text(json.dumps(BRIEFING_RESERVA, ensure_ascii=False), encoding="utf-8")
    a, b = post_valido(), post_valido()
    monkeypatch.setattr(gerar, "executar_claude",
                        lambda p, m: envelope_real({"lote": "2026-W40", "posts": [a, b]}, duracao_ms=4000))
    assert gerar.main([str(pasta / "briefing.json")]) == 0
    posts = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
    assert [p["numero"] for p in posts["posts"]] == [4, 5]
    m = json.loads((pasta / "metricas-geracao.json").read_text(encoding="utf-8"))
    assert m["semana"] == "2026-W40" and m["tentativas"] == 1 and m["erros"] == 0
    assert m["total"]["input_tokens"] == 100 and m["total"]["output_tokens"] == 900
    assert m["total"]["custo_usd"] == 0.5 and m["total"]["duracao_cli_s"] == 4.0
    assert m["duracao_s"] >= 0 and m["modelo"] and m["gerado_em"]


def test_prompt_explicita_limite_de_palavras():
    prompt = gerar.montar_prompt({"posts": []}, "cartão", {})
    assert "NO MÁXIMO 20 palavras" in prompt


def test_prompt_exige_escopo_das_quatro_fontes():
    """Regra do Diogo: só Doc. CNBB 106, CIC, CDC e Bíblia, sempre com número."""
    prompt = gerar.montar_prompt({"posts": []}, "cartão", {})
    for trecho in ["Doc. CNBB 106", "CIC", "cân.", "Bíblia", "voluntário"]:
        assert trecho in prompt
