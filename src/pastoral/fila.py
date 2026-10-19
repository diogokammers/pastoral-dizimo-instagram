"""Fila de publicação (ADR-015): uma publicação por semana, nos horários de `publicacao.dias`
(hoje: quarta às 18h, America/Sao_Paulo), em ordem de aprovação. Determinístico, sem LLM.

- `ultimo_horario(agora)`: o horário de publicação mais recente que já chegou (S).
- `proximo_horario(agora)`: o próximo horário depois de agora.
- `horario_a_partir(data)`: o primeiro horário em ou depois de uma data fixa ("não antes de").
- `escolher(prontos, publicados_em, agora)`: quem sai agora. Se algo foi publicado em S ou depois, a semana
  está servida e nada sai. Senão sai um só: a data fixa vencida mais antiga; sem data fixa, o `aprovado_em`
  mais antigo (empate: menor número).
- `alerta(...)`: texto do alerta quando não há nada para publicar (dia da quarta ou véspera), ou None.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pastoral.pauta import DIAS_DA_SEMANA

NOMES = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
VESPERA_H = 30          # mesma janela do alerta "sem aprovação" (ADR-014)
DIA_H = 24


def _horarios(cfg: dict) -> list[tuple[int, int, int]]:
    """[(weekday 0=segunda, hora, minuto)] de publicacao.dias."""
    saida = []
    for d in cfg["dias"]:
        if d.get("dia") not in DIAS_DA_SEMANA:
            raise ValueError(f"publicacao.dias: dia inválido {d.get('dia')!r}")
        h, m = (int(x) for x in str(d["hora"]).split(":"))
        saida.append((DIAS_DA_SEMANA[d["dia"]] - 1, h, m))
    if not saida:
        raise ValueError("publicacao.dias vazio")
    return saida


def _candidatos(ponto: datetime, cfg: dict) -> list[datetime]:
    """Todos os horários de publicação nas duas semanas em volta de `ponto` (no fuso configurado)."""
    fuso = ZoneInfo(cfg["fuso"])
    local = ponto.astimezone(fuso)
    base = local.replace(hour=0, minute=0, second=0, microsecond=0)
    saida = []
    for dias in range(-7, 8):
        dia = base + timedelta(days=dias)
        for weekday, h, m in _horarios(cfg):
            if dia.weekday() == weekday:
                saida.append(dia.replace(hour=h, minute=m))
    return sorted(saida)


def ultimo_horario(agora: datetime, cfg: dict) -> datetime:
    return max(c for c in _candidatos(agora, cfg) if c <= agora)


def proximo_horario(agora: datetime, cfg: dict) -> datetime:
    return min(c for c in _candidatos(agora, cfg) if c > agora)


def horario_a_partir(data: datetime, cfg: dict) -> datetime:
    return min(c for c in _candidatos(data, cfg) if c >= data)


def _data(texto):
    return datetime.fromisoformat(texto) if texto else None


def _servida(publicados_em: list[datetime], horario: datetime) -> bool:
    return any(p >= horario for p in publicados_em)


def _ordenar(prontos: list[dict]) -> list[dict]:
    """Data fixa (já vencida, pois só chega aqui o que o portão aceitou) primeiro, da mais antiga; depois a
    fila por carimbo de aprovação; empate pelo número."""
    fixos = sorted((p for p in prontos if p.get("agendado_para")), key=lambda p: (_data(p["agendado_para"]), p["numero"]))
    fila = sorted((p for p in prontos if not p.get("agendado_para")),
                  key=lambda p: (_data(p.get("aprovado_em")) or datetime.max.replace(tzinfo=ZoneInfo("UTC")), p["numero"]))
    return fixos + fila


def _elegivel(p: dict, horario: datetime) -> bool:
    """Serve para o horário S quem já estava aprovado até S e cuja data fixa (se houver) é até S.
    Aprovado depois de S espera o próximo horário (um post aprovado na quinta não sai na quinta)."""
    aprovado = _data(p.get("aprovado_em"))
    fixo = _data(p.get("agendado_para"))
    return (aprovado is None or aprovado <= horario) and (fixo is None or fixo <= horario)


def escolher(prontos: list[dict], publicados_em: list[datetime], agora: datetime, cfg: dict) -> tuple[dict | None, list[dict]]:
    ordem = _ordenar(prontos)
    horario = ultimo_horario(agora, cfg)
    if _servida(publicados_em, horario):
        return None, ordem
    elegiveis = [p for p in ordem if _elegivel(p, horario)]
    if not elegiveis:
        return None, ordem
    return elegiveis[0], [p for p in ordem if p is not elegiveis[0]]


def por_extenso(d: datetime) -> str:
    return f"{NOMES[d.weekday()]}, {d:%d/%m/%Y, %H:%M}"


def alerta(prontos: list[dict], publicados_em: list[datetime], agora: datetime, cfg: dict) -> str | None:
    """No dia do horário (até 24 h depois), sem nada publicado nem elegível: "fila vazia". Na véspera (até 30 h
    antes do próximo horário), sem nada aprovado: "nada aprovado". Senão None."""
    ultimo = ultimo_horario(agora, cfg)
    if (not _servida(publicados_em, ultimo) and agora - ultimo <= timedelta(hours=DIA_H)
            and not any(_elegivel(p, ultimo) for p in prontos)):
        return f"fila vazia: nenhuma publicação aprovada para {por_extenso(ultimo)}"
    proximo = proximo_horario(agora, cfg)
    if not prontos and proximo - agora <= timedelta(hours=VESPERA_H):
        return f"nada aprovado para a próxima {por_extenso(proximo)}"
    return None
