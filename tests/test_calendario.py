"""Fatia 2 — calendário litúrgico calculado (datas conferidas em docs/pesquisa.md e 04 §5)."""
from datetime import date

import pytest

from pastoral import calendario as cal


# Datas conferidas por dois métodos em docs/pesquisa.md (03 §8, 04 §5)
def test_datas_conferidas_na_pesquisa():
    assert cal.primeiro_domingo_advento(2026) == date(2026, 11, 29)
    m = cal.datas_moveis(2027)
    assert m["cinzas"] == date(2027, 2, 10)
    assert m["pascoa"] == date(2027, 3, 28)
    assert m["pentecostes"] == date(2027, 5, 16)
    assert m["corpus_christi"] == date(2027, 5, 27)


def test_pascoa_usa_metodo_ocidental():
    assert cal.pascoa(2026) == date(2026, 4, 5)
    assert cal.pascoa(2025) == date(2025, 4, 20)


def test_derivacoes_2026():
    m = cal.datas_moveis(2026)
    assert m["cinzas"] == date(2026, 2, 18)
    assert m["ramos"] == date(2026, 3, 29)
    assert m["pentecostes"] == date(2026, 5, 24)
    assert m["cristo_rei"] == date(2026, 11, 22)
    assert m["advento"] == date(2026, 11, 29)


def test_advento_quando_natal_cai_no_domingo():
    # Natal de 2022 foi domingo → 1º Domingo do Advento em 27/11/2022
    assert cal.primeiro_domingo_advento(2022) == date(2022, 11, 27)


def test_epifania_e_batismo_no_brasil():
    m = cal.datas_moveis(2027)
    assert m["epifania"] == date(2027, 1, 3)   # domingo entre 2 e 8 de janeiro
    assert m["batismo"] == date(2027, 1, 10)


@pytest.mark.parametrize("dia, tempo, cor", [
    (date(2026, 10, 6), "Tempo Comum", "verde"),
    (date(2026, 12, 1), "Advento", "roxo"),
    (date(2026, 12, 25), "Natal", "branco"),
    (date(2027, 1, 20), "Tempo Comum", "verde"),
    (date(2027, 2, 10), "Quaresma", "roxo"),
    (date(2027, 3, 26), "Tríduo Pascal", "vermelho"),   # Sexta-feira da Paixão
    (date(2027, 3, 28), "Tempo Pascal", "branco"),
    (date(2027, 5, 16), "Tempo Pascal", "vermelho"),    # Pentecostes
    (date(2027, 5, 27), "Tempo Comum", "branco"),       # Corpus Christi
])
def test_tempo_e_cor(dia, tempo, cor):
    assert cal.tempo_liturgico(dia) == tempo
    assert cal.cor_liturgica(dia) == cor


def test_celebracoes_entre_inclui_fixas_e_moveis():
    nomes = [c["nome"] for c in cal.celebracoes_entre(date(2026, 10, 12), date(2026, 10, 18))]
    assert "Nossa Senhora Aparecida" in nomes
    nomes = [c["nome"] for c in cal.celebracoes_entre(date(2027, 3, 22), date(2027, 3, 28))]
    assert "Domingo da Páscoa" in nomes and "Sexta-feira da Paixão" in nomes


def test_padroeira_da_arquidiocese():
    nomes = [c["nome"] for c in cal.celebracoes_entre(date(2026, 11, 25), date(2026, 11, 25))]
    assert any("Catarina" in n for n in nomes)


def test_campanha_da_fraternidade_2027():
    cf = cal.campanha_fraternidade(2027)
    assert cf["tema"] == "Fraternidade e o Cuidado das Crianças"
    assert "Mt 18,5" in cf["lema"]
    assert cal.campanha_fraternidade(2031)["tema"] == "a confirmar"


def test_gancho_da_semana():
    g = cal.gancho_semana(2026, 42)
    assert g["inicio"] == "2026-10-12" and g["fim"] == "2026-10-18"
    assert g["tempo"] == "Tempo Comum"
    assert g["mes_tematico"] == "Mês Missionário"
    assert any(c["nome"] == "Nossa Senhora Aparecida" for c in g["celebracoes"])


def test_gancho_na_quaresma_traz_campanha():
    g = cal.gancho_semana(2027, 7)   # semana de 15/02/2027
    assert g["tempo"] == "Quaresma"
    assert g["campanha_fraternidade"]["tema"].startswith("Fraternidade")
