"""Fatia 1 — medição de tokens do cartão (medido via claude -p ou estimado chars/4 [H])."""
import json

from pastoral import medir_tokens as mt


def test_estimativa_chars_por_4():
    assert mt.estimar_tokens("a" * 400) == 100
    assert mt.estimar_tokens("abc") == 1  # arredonda para cima


def test_total_de_entrada_soma_cache():
    envelope = {"is_error": False, "usage": {
        "input_tokens": 10, "cache_creation_input_tokens": 200, "cache_read_input_tokens": 3000}}
    assert mt.total_entrada(envelope) == 3210


def test_total_de_entrada_recusa_erro():
    assert mt.total_entrada({"is_error": True, "usage": {"input_tokens": 0}}) is None


def test_medir_usa_diferenca_entre_chamadas():
    # base (só "responda ok") = 1000; com cartão = 3500 → cartão = 2500
    respostas = iter([
        json.dumps({"is_error": False, "usage": {"input_tokens": 1000}}),
        json.dumps({"is_error": False, "usage": {"input_tokens": 3500}}),
    ])
    r = mt.medir("texto do cartão", modelo="haiku", executar=lambda prompt, modelo: next(respostas))
    assert r == {"tokens": 2500, "metodo": "claude -p (medido)", "modelo": "haiku"}


def test_medir_cai_para_estimativa_se_cli_falha():
    falha = json.dumps({"is_error": True, "result": "Failed to authenticate", "usage": {}})
    r = mt.medir("x" * 800, modelo="haiku", executar=lambda prompt, modelo: falha)
    assert r["tokens"] == 200
    assert r["metodo"].startswith("estimativa chars/4 [H]")
    assert "Failed to authenticate" in r["motivo"]


def test_medir_cai_para_estimativa_se_cli_ausente():
    def explode(prompt, modelo):
        raise FileNotFoundError("claude")
    r = mt.medir("y" * 40, modelo="haiku", executar=explode)
    assert r["tokens"] == 10 and "[H]" in r["metodo"]
