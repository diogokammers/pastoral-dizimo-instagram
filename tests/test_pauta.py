"""Fatia 2 — pauta semanal determinística (ciclo 70/20/10, fila de temas, gancho litúrgico)."""
import json
from collections import Counter

import pytest
import yaml

from pastoral import pauta


@pytest.fixture
def config(raiz):
    return yaml.safe_load((raiz / "config.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def temas(raiz):
    return pauta.carregar_temas(raiz / "content" / "temas.yaml")


def test_temas_sem_reels(temas):
    numeros = [t["numero"] for t in temas]
    for reels in (10, 11, 12, 13, 14, 21, 25):
        assert reels not in numeros
    assert len(temas) == 23
    assert numeros == sorted(numeros)


def test_temas_tem_pilar_e_formato_validos(temas):
    for t in temas:
        assert t["pilar"] in pauta.PILARES, t
        assert t["formato"] in ("carrossel", "imagem_unica"), t


def test_tres_primeiros_sao_os_fixados(temas, config):
    seq = pauta.sequencia(temas, config["pauta"]["ciclo_pilares"], config["pauta"]["fixados"], 3)
    assert [t["numero"] for t in seq] == [1, 2, 3]
    assert [t["titulo"] for t in seq][1:] == ["O que é o dízimo?", "Para onde vai o dízimo?"]


def test_ciclo_de_10_respeita_70_20_10(temas, config):
    seq = pauta.sequencia(temas, config["pauta"]["ciclo_pilares"], config["pauta"]["fixados"], 20)
    for bloco in (seq[:10], seq[10:20]):
        c = Counter(t["pilar"] for t in bloco)
        assert c == {"Formação": 7, "Vida pastoral": 2, "Convite institucional": 1}


def test_sequencia_nao_repete_ate_esgotar_e_depois_recomeca(temas, config):
    seq = pauta.sequencia(temas, config["pauta"]["ciclo_pilares"], config["pauta"]["fixados"], 30)
    primeiros = [t["numero"] for t in seq[:23]]
    assert len(set(primeiros)) == 23
    assert all(t["rodada"] == 1 for t in seq[:23])
    assert seq[23]["rodada"] == 2


def test_sequencia_ordem_esperada(temas, config):
    seq = pauta.sequencia(temas, config["pauta"]["ciclo_pilares"], config["pauta"]["fixados"], 8)
    assert [t["numero"] for t in seq] == [1, 2, 3, 6, 4, 5, 7, 9]


def test_briefing_primeira_semana(temas, config):
    b = pauta.montar_briefing("2026-W41", config, temas)
    assert b["semana"] == "2026-W41"
    assert [p["tema"] for p in b["posts"]] == [1, 2]
    assert [p["data"] for p in b["posts"]] == ["2026-10-06", "2026-10-09"]
    assert all(p["hora"] == "19:00" and p["fuso"] == "America/Sao_Paulo" for p in b["posts"])
    assert all(p["fixado"] for p in b["posts"])
    assert b["posts"][0]["tempo_liturgico"] == "Tempo Comum"
    assert b["gancho_liturgico"]["mes_tematico"] == "Mês Missionário"


def test_briefing_segunda_semana(temas, config):
    b = pauta.montar_briefing("2026-W42", config, temas)
    assert [p["tema"] for p in b["posts"]] == [3, 6]
    assert b["posts"][0]["fixado"] is True and b["posts"][1]["fixado"] is False
    assert "pendencia" in b["posts"][0]           # post 3: dimensões a confirmar
    assert b["posts"][1]["pilar"] == "Vida pastoral"


def test_briefing_antes_do_inicio_falha(temas, config):
    with pytest.raises(ValueError):
        pauta.montar_briefing("2026-W40", config, temas)


def test_briefing_deterministico_e_salvo(temas, config, tmp_path):
    a = pauta.montar_briefing("2026-W50", config, temas)
    b = pauta.montar_briefing("2026-W50", config, temas)
    assert a == b
    caminho = pauta.salvar_briefing(a, tmp_path)
    assert caminho == tmp_path / "2026-W50" / "briefing.json"
    assert json.loads(caminho.read_text(encoding="utf-8")) == a
    assert caminho.read_bytes() == pauta.salvar_briefing(b, tmp_path).read_bytes()


def test_semana_invalida(temas, config):
    with pytest.raises(ValueError):
        pauta.montar_briefing("2026-41", config, temas)
