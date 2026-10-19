"""ADR-015 — fila de publicação: um post por semana (quarta, 18h), em ordem de aprovação."""
from datetime import datetime, timezone

import pytest

from pastoral import fila

CFG = {"fuso": "America/Sao_Paulo", "dias": [{"dia": "quarta", "hora": "18:00"}], "fila": True}


def utc(texto):
    return datetime.fromisoformat(texto).astimezone(timezone.utc)


# ---------- horários ----------

def test_ultimo_horario_e_a_quarta_18h_mais_recente_ate_agora():
    # segunda 19/10 → quarta anterior 14/10
    assert fila.ultimo_horario(utc("2026-10-19T19:00:00-03:00"), CFG).isoformat() == "2026-10-14T18:00:00-03:00"
    # na própria quarta, às 18:00 em ponto, o horário já vale
    assert fila.ultimo_horario(utc("2026-10-21T18:00:00-03:00"), CFG).isoformat() == "2026-10-21T18:00:00-03:00"
    # na quarta às 17:59 ainda é a quarta anterior
    assert fila.ultimo_horario(utc("2026-10-21T17:59:00-03:00"), CFG).isoformat() == "2026-10-14T18:00:00-03:00"


def test_proximo_horario_e_a_quarta_18h_seguinte_depois_de_agora():
    assert fila.proximo_horario(utc("2026-10-19T19:00:00-03:00"), CFG).isoformat() == "2026-10-21T18:00:00-03:00"
    # às 18:00 em ponto o próximo já é a quarta seguinte
    assert fila.proximo_horario(utc("2026-10-21T18:00:00-03:00"), CFG).isoformat() == "2026-10-28T18:00:00-03:00"


def test_horario_a_partir_de_uma_data_fixa():
    """Data fixa = "não antes de": a primeira quarta 18h em ou depois dela."""
    assert fila.horario_a_partir(utc("2026-10-09T19:00:00-03:00"), CFG).isoformat() == "2026-10-14T18:00:00-03:00"
    assert fila.horario_a_partir(utc("2026-10-21T18:00:00-03:00"), CFG).isoformat() == "2026-10-21T18:00:00-03:00"


def test_varios_dias_na_semana():
    cfg = {**CFG, "dias": [{"dia": "terca", "hora": "19:00"}, {"dia": "sexta", "hora": "19:00"}]}
    assert fila.ultimo_horario(utc("2026-10-19T19:00:00-03:00"), cfg).isoformat() == "2026-10-16T19:00:00-03:00"
    assert fila.proximo_horario(utc("2026-10-19T19:00:00-03:00"), cfg).isoformat() == "2026-10-20T19:00:00-03:00"


def test_dia_invalido_recusado():
    with pytest.raises(ValueError, match="dia"):
        fila.ultimo_horario(utc("2026-10-19T19:00:00-03:00"), {**CFG, "dias": [{"dia": "lunes", "hora": "18:00"}]})


# ---------- escolha ----------

def pronto(numero, agendado=None, aprovado_em="2026-10-01T10:00:00+00:00"):
    return {"semana": "2026-W42", "numero": numero, "agendado_para": agendado, "aprovado_em": aprovado_em}


AGORA = utc("2026-10-21T18:00:30-03:00")            # quarta, logo depois das 18h


def test_sem_nada_publicado_desde_o_horario_sai_um_so_na_ordem_de_aprovacao():
    prontos = [pronto(9, aprovado_em="2026-10-20T10:00:00+00:00"),
               pronto(8, aprovado_em="2026-10-19T10:00:00+00:00"),
               pronto(10, aprovado_em="2026-10-21T10:00:00+00:00")]
    escolhido, restantes = fila.escolher(prontos, [], AGORA, CFG)
    assert escolhido["numero"] == 8
    assert [r["numero"] for r in restantes] == [9, 10]


def test_data_fixa_vencida_vem_antes_da_fila():
    prontos = [pronto(8, aprovado_em="2026-10-01T10:00:00+00:00"),
               pronto(7, agendado="2026-10-09T19:00:00-03:00", aprovado_em="2026-10-19T22:03:19+00:00")]
    escolhido, restantes = fila.escolher(prontos, [], AGORA, CFG)
    assert escolhido["numero"] == 7 and [r["numero"] for r in restantes] == [8]


def test_duas_datas_fixas_vencidas_sai_a_mais_antiga():
    prontos = [pronto(9, agendado="2026-10-20T19:00:00-03:00"), pronto(7, agendado="2026-10-09T19:00:00-03:00")]
    assert fila.escolher(prontos, [], AGORA, CFG)[0]["numero"] == 7


def test_empate_no_carimbo_sai_o_menor_numero():
    prontos = [pronto(9), pronto(8)]
    assert fila.escolher(prontos, [], AGORA, CFG)[0]["numero"] == 8


def test_semana_ja_servida_nada_sai():
    """Algo publicado em S ou depois (ledger) → a semana está servida, mesmo com fila cheia."""
    publicados = [utc("2026-10-21T18:05:00-03:00")]
    escolhido, restantes = fila.escolher([pronto(8), pronto(9)], publicados, AGORA, CFG)
    assert escolhido is None and [r["numero"] for r in restantes] == [8, 9]


def test_publicacao_antes_do_horario_nao_conta():
    publicados = [utc("2026-10-14T21:30:00-03:00")]          # o post da semana passada
    assert fila.escolher([pronto(8)], publicados, AGORA, CFG)[0]["numero"] == 8


def test_quinta_sem_publicacao_na_quarta_ainda_sai():
    """O portão roda todo dia: se a quarta falhou, a quinta recupera (a semana segue não servida),
    mas só com quem já estava aprovado até a hora da quarta."""
    quinta = utc("2026-10-22T18:00:30-03:00")
    assert fila.escolher([pronto(8, aprovado_em="2026-10-21T20:00:00+00:00")], [], quinta, CFG)[0]["numero"] == 8


def test_aprovado_depois_do_horario_espera_a_proxima_quarta():
    quinta = utc("2026-10-22T18:00:30-03:00")
    tarde = pronto(8, aprovado_em="2026-10-21T22:00:00+00:00")      # quinta 19h em Brasília... não: quarta 19h
    assert fila.escolher([tarde], [], quinta, CFG) == (None, [tarde])
    # data fixa vencida, mas aprovada depois da quarta (caso do post 7 em 19/10): espera a quarta 21/10
    terca = utc("2026-10-20T18:00:30-03:00")
    p7 = pronto(7, agendado="2026-10-09T19:00:00-03:00", aprovado_em="2026-10-19T22:03:19+00:00")
    assert fila.escolher([p7], [], terca, CFG) == (None, [p7])
    assert fila.escolher([p7], [], AGORA, CFG)[0]["numero"] == 7


def test_data_fixa_depois_do_horario_espera():
    quinta = utc("2026-10-22T18:00:30-03:00")
    p = pronto(8, agendado="2026-10-22T10:00:00-03:00")
    assert fila.escolher([p], [], quinta, CFG) == (None, [p])


def test_fila_vazia():
    assert fila.escolher([], [], AGORA, CFG) == (None, [])


# ---------- alertas ----------

def test_alerta_fila_vazia_no_dia():
    """Quarta sem nada aprovado e sem nada publicado: alerta no próprio dia (até 24 h depois do horário)."""
    assert fila.alerta([], [], AGORA, CFG) == "fila vazia: nenhuma publicação aprovada para quarta-feira, 21/10/2026, 18:00"
    tarde = pronto(8, aprovado_em="2026-10-21T22:00:00+00:00")        # aprovado depois das 18h: não serve hoje
    assert fila.alerta([tarde], [], AGORA, CFG) == "fila vazia: nenhuma publicação aprovada para quarta-feira, 21/10/2026, 18:00"
    sexta = utc("2026-10-23T18:00:30-03:00")
    assert fila.alerta([], [], sexta, CFG) is None


def test_alerta_na_vespera_sem_nada_aprovado():
    terca = utc("2026-10-20T18:00:30-03:00")
    assert fila.alerta([], [], terca, CFG) == "nada aprovado para a próxima quarta-feira, 21/10/2026, 18:00"
    assert fila.alerta([pronto(8)], [], terca, CFG) is None
    segunda = utc("2026-10-19T18:00:30-03:00")        # 48 h antes: ainda não
    assert fila.alerta([], [], segunda, CFG) is None


def test_sem_alerta_quando_a_semana_foi_servida():
    assert fila.alerta([], [utc("2026-10-21T18:05:00-03:00")], AGORA, CFG) is None


def test_fila_so_usa_a_biblioteca_padrao():
    """O portão roda no publicar.yml só com PyYAML instalado: fila.py não pode puxar pauta/calendario (dateutil)."""
    import ast
    from pathlib import Path
    arvore = ast.parse((Path(fila.__file__)).read_text(encoding="utf-8"))
    modulos = {n.module.split(".")[0] for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom) and n.module}
    modulos |= {a.name.split(".")[0] for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert "pastoral" not in modulos and "dateutil" not in modulos, modulos
