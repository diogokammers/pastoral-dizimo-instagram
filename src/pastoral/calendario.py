"""Calendário litúrgico calculado (sem LLM, sem internet).

Base: Páscoa por `dateutil.easter` (método 3 = gregoriano/ocidental) e derivações fixas.
Datas conferidas em docs/pesquisa.md (Advento 29/11/2026, Cinzas 10/02/2027, Páscoa 28/03/2027,
Pentecostes 16/05/2027, Corpus Christi 27/05/2027).

Ressalva (docs/pesquisa/04 §5): as cores por tempo seguem o padrão geral da Igreja Latina e não foram
conferidas em fonte oficial da CNBB; as transferências para domingo no Brasil (Epifania, Ascensão) seguem
a regra litúrgica geral e ficam marcadas [a confirmar na Agenda Litúrgica e Pastoral da CNBB].
"""
from __future__ import annotations

from datetime import date, timedelta

from dateutil.easter import EASTER_WESTERN, easter

# Campanha da Fraternidade: só o que está verificado na pesquisa (04 §5).
CAMPANHAS_FRATERNIDADE = {
    2027: {"tema": "Fraternidade e o Cuidado das Crianças",
           "lema": '"Quem recebe uma criança em meu nome, a mim recebe" (Mt 18,5)'},
}

# Datas fixas relevantes: (mês, dia, nome, cor ou None). Cor None = não muda a cor do tempo.
DATAS_FIXAS = [
    (1, 1, "Santa Maria, Mãe de Deus", "branco"),
    (3, 19, "São José", "branco"),
    (3, 25, "Anunciação do Senhor", "branco"),
    (8, 15, "Assunção de Nossa Senhora", "branco"),
    (10, 1, "Santa Teresinha do Menino Jesus, padroeira das missões", None),
    (10, 12, "Nossa Senhora Aparecida", "branco"),
    (11, 1, "Todos os Santos", "branco"),
    (11, 2, "Comemoração dos Fiéis Defuntos", "roxo"),
    (11, 25, "Santa Catarina de Alexandria, padroeira da Arquidiocese", "vermelho"),
    (12, 8, "Imaculada Conceição", "branco"),
    (12, 25, "Natal do Senhor", "branco"),
]

# Meses temáticos citados na pesquisa (04 §5).
MESES_TEMATICOS = {10: "Mês Missionário"}


def pascoa(ano: int) -> date:
    """Domingo da Páscoa (método ocidental, dateutil method=3)."""
    return easter(ano, method=EASTER_WESTERN)


def primeiro_domingo_advento(ano: int) -> date:
    """4º domingo antes do Natal (o domingo entre 27/11 e 03/12)."""
    natal = date(ano, 12, 25)
    dias_desde_domingo = (natal.weekday() - 6) % 7 or 7   # se o Natal é domingo, o 4º do Advento é 18/12
    return natal - timedelta(days=dias_desde_domingo + 21)


def _epifania(ano: int) -> date:
    """No Brasil, domingo entre 2 e 8 de janeiro [a confirmar]."""
    dia = date(ano, 1, 2)
    return dia + timedelta(days=(6 - dia.weekday()) % 7)


def _batismo(ano: int) -> date:
    """Domingo após a Epifania; se a Epifania cai em 7 ou 8/01, segunda-feira seguinte."""
    epifania = _epifania(ano)
    return epifania + timedelta(days=1 if epifania.day >= 7 else 7)


def datas_moveis(ano: int) -> dict[str, date]:
    """Todas as datas móveis do ano civil, derivadas da Páscoa e do Natal."""
    p = pascoa(ano)
    advento = primeiro_domingo_advento(ano)
    return {
        "epifania": _epifania(ano),
        "batismo": _batismo(ano),
        "cinzas": p - timedelta(days=46),
        "ramos": p - timedelta(days=7),
        "quinta_santa": p - timedelta(days=3),
        "sexta_santa": p - timedelta(days=2),
        "sabado_santo": p - timedelta(days=1),
        "pascoa": p,
        "ascensao": p + timedelta(days=42),        # no Brasil, transferida para o domingo [a confirmar]
        "pentecostes": p + timedelta(days=49),
        "trindade": p + timedelta(days=56),
        "corpus_christi": p + timedelta(days=60),
        "sagrado_coracao": p + timedelta(days=68),
        "cristo_rei": advento - timedelta(days=7),
        "advento": advento,
    }


# Nome e cor de cada data móvel que vira celebração.
_CELEBRACOES_MOVEIS = {
    "epifania": ("Epifania do Senhor", "branco"),
    "batismo": ("Batismo do Senhor", "branco"),
    "cinzas": ("Quarta-feira de Cinzas", "roxo"),
    "ramos": ("Domingo de Ramos", "vermelho"),
    "quinta_santa": ("Quinta-feira Santa (Ceia do Senhor)", "branco"),
    "sexta_santa": ("Sexta-feira da Paixão", "vermelho"),
    "sabado_santo": ("Sábado Santo", None),
    "pascoa": ("Domingo da Páscoa", "branco"),
    "ascensao": ("Ascensão do Senhor", "branco"),
    "pentecostes": ("Pentecostes", "vermelho"),
    "trindade": ("Santíssima Trindade", "branco"),
    "corpus_christi": ("Corpus Christi", "branco"),
    "sagrado_coracao": ("Sagrado Coração de Jesus", "branco"),
    "cristo_rei": ("Cristo Rei", "branco"),
    "advento": ("1º Domingo do Advento", "roxo"),
}


def celebracoes(ano: int) -> list[dict]:
    """Celebrações do ano civil, ordenadas por data: [{'data': date, 'nome', 'cor'}]."""
    lista = [{"data": date(ano, m, d), "nome": nome, "cor": cor} for m, d, nome, cor in DATAS_FIXAS]
    for chave, dia in datas_moveis(ano).items():
        nome, cor = _CELEBRACOES_MOVEIS[chave]
        lista.append({"data": dia, "nome": nome, "cor": cor})
    return sorted(lista, key=lambda c: (c["data"], c["nome"]))


def celebracoes_entre(inicio: date, fim: date) -> list[dict]:
    """Celebrações com data entre `inicio` e `fim` (inclusive)."""
    anos = range(inicio.year, fim.year + 1)
    return [c for a in anos for c in celebracoes(a) if inicio <= c["data"] <= fim]


def _tempo_e_cor(dia: date) -> tuple[str, str]:
    """Tempo litúrgico do dia e a cor própria do tempo."""
    m = datas_moveis(dia.year)
    if dia >= m["advento"]:
        return ("Natal", "branco") if dia >= date(dia.year, 12, 25) else ("Advento", "roxo")
    if dia <= m["batismo"]:
        return "Natal", "branco"
    if dia < m["cinzas"]:
        return "Tempo Comum", "verde"
    if dia < m["quinta_santa"]:
        return "Quaresma", "roxo"
    if dia < m["pascoa"]:
        return "Tríduo Pascal", "branco"
    if dia <= m["pentecostes"]:
        return "Tempo Pascal", "branco"
    return "Tempo Comum", "verde"


def tempo_liturgico(dia: date) -> str:
    return _tempo_e_cor(dia)[0]


def cor_liturgica(dia: date) -> str:
    """Cor do dia: a da celebração (se tiver cor própria) ou a do tempo."""
    for c in celebracoes_entre(dia, dia):
        if c["cor"]:
            return c["cor"]
    return _tempo_e_cor(dia)[1]


def campanha_fraternidade(ano: int) -> dict:
    """Tema e lema da CF do ano; 'a confirmar' quando não verificado."""
    return CAMPANHAS_FRATERNIDADE.get(ano, {"tema": "a confirmar", "lema": "a confirmar"})


def gancho_semana(ano: int, semana: int) -> dict:
    """Gancho litúrgico de uma semana ISO (segunda a domingo)."""
    inicio = date.fromisocalendar(ano, semana, 1)
    fim = inicio + timedelta(days=6)
    tempo = tempo_liturgico(inicio)
    gancho = {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "tempo": tempo,
        "cor": cor_liturgica(inicio),
        "celebracoes": [{"data": c["data"].isoformat(), "nome": c["nome"], "cor": c["cor"]}
                        for c in celebracoes_entre(inicio, fim)],
        "mes_tematico": MESES_TEMATICOS.get(inicio.month),
    }
    if tempo == "Quaresma":
        gancho["campanha_fraternidade"] = campanha_fraternidade(inicio.year)
    return gancho
