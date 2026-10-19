"""Pauta semanal: escolhe os N posts da semana, sem LLM e de forma determinística.

Regras (docs/arquitetura.md §1.1, ADR-004):
- Os posts são numerados globalmente a partir de `pauta.semana_inicial` (N por semana).
- Os primeiros posts são os fixados (`pauta.fixados`: temas 1, 2 e 3).
- Depois, cada posição i segue `ciclo_pilares[i % 10]` (7 Formação · 2 Vida pastoral · 1 Convite)
  e pega o próximo tema ainda não usado daquele pilar, na ordem numérica da estratégia.
- Se o pilar esgotou, usa o próximo tema não usado de qualquer pilar; se todos esgotaram, começa
  uma nova rodada (campo `rodada`).
- `pauta.fixados_publicados: true` (content/estreia/publicado.json): os fixados já saíram antes da
  semana inicial, então a série semanal começa no post seguinte (ex.: post 4), sem repeti-los.
- `pauta.pular_pendencias: true`: temas com `pendencia` (dado real inexistente) ficam fora da fila;
  a vaga do pilar dele cai no próximo tema livre (rotação 70/20/10 "o melhor possível").
- `pauta.ritmos_anteriores` (ADR-015): [{ate, posts_por_semana, dias}] — semanas até `ate` usam aquele ritmo;
  as seguintes usam `publicacao`. A numeração soma os posts de todas as semanas anteriores.
Como o resultado depende só da semana e dos arquivos de configuração, rodar de novo dá o mesmo JSON.

Uso: python -m pastoral.pauta 2026-W41
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

import yaml

from pastoral import calendario

PILARES = ("Formação", "Vida pastoral", "Convite institucional")
DIAS_DA_SEMANA = {"segunda": 1, "terca": 2, "quarta": 3, "quinta": 4, "sexta": 5, "sabado": 6, "domingo": 7}
RAIZ = Path(__file__).resolve().parents[2]


def carregar_yaml(caminho: Path) -> dict:
    return yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))


def carregar_temas(caminho: Path) -> list[dict]:
    """Lista de temas em ordem numérica."""
    return sorted(carregar_yaml(caminho)["temas"], key=lambda t: t["numero"])


def sequencia(temas: list[dict], ciclo: list[str], fixados: list[int], total: int,
              pular_pendencia: bool = False) -> list[dict]:
    """Os `total` primeiros posts da série, cada um = tema + campo `rodada`."""
    por_numero = {t["numero"]: t for t in temas}
    if pular_pendencia:                          # fixados continuam valendo mesmo se tiverem pendência
        temas = [t for t in temas if "pendencia" not in t or t["numero"] in fixados]
    usados: set[int] = set()
    rodada = 1
    saida = []
    for i in range(total):
        if i < len(fixados):
            tema = por_numero[fixados[i]]
        else:
            if len(usados) == len(temas):          # tudo usado: nova rodada
                usados.clear()
                rodada += 1
            livres = [t for t in temas if t["numero"] not in usados]
            do_pilar = [t for t in livres if t["pilar"] == ciclo[i % len(ciclo)]]
            tema = (do_pilar or livres)[0]
        usados.add(tema["numero"])
        saida.append({**tema, "rodada": rodada})
    return saida


def _ler_semana(texto: str) -> tuple[int, int]:
    """'2026-W41' → (2026, 41)."""
    m = re.fullmatch(r"(\d{4})-W(\d{2})", texto)
    if not m:
        raise ValueError(f"semana inválida: {texto!r} (use AAAA-Www, ex.: 2026-W41)")
    return int(m.group(1)), int(m.group(2))


def _indice_da_semana(semana: str, inicial: str) -> int:
    """Quantas semanas se passaram desde a semana inicial."""
    a, s = _ler_semana(semana)
    a0, s0 = _ler_semana(inicial)
    dias = (date.fromisocalendar(a, s, 1) - date.fromisocalendar(a0, s0, 1)).days
    if dias < 0:
        raise ValueError(f"{semana} é anterior à semana inicial {inicial}")
    return dias // 7


def _semana_mais(semana: str, semanas: int) -> str:
    a, s = _ler_semana(semana)
    d = date.fromisocalendar(a, s, 1) + timedelta(weeks=semanas)
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def ritmo_da_semana(semana: str, config: dict) -> dict:
    """{posts_por_semana, dias} que valem para a semana: o primeiro ritmo anterior cujo `ate` ainda não
    passou; senão o de `publicacao` (ADR-015)."""
    pub = config["publicacao"]
    for r in config["pauta"].get("ritmos_anteriores") or []:
        if _nao_antes(semana, r["ate"]):
            return {"posts_por_semana": r["posts_por_semana"], "dias": r["dias"]}
    return {"posts_por_semana": pub["posts_por_semana"], "dias": pub["dias"]}


def _nao_antes(semana: str, limite: str) -> bool:
    """True se `semana` <= `limite`."""
    a, s = _ler_semana(semana)
    b, t = _ler_semana(limite)
    return (a, s) <= (b, t)


def montar_briefing(semana: str, config: dict, temas: list[dict]) -> dict:
    """Briefing da semana: posts escolhidos + gancho litúrgico."""
    cfg_pauta, pub = config["pauta"], config["publicacao"]
    if not cfg_pauta.get("semana_inicial"):
        raise ValueError("pauta.semana_inicial não definida: sem data de estreia (ADR-005)")
    ritmo = ritmo_da_semana(semana, config)
    n = ritmo["posts_por_semana"]
    # Fixados já publicados (estreia): a série semanal começa depois deles, sem colidir na numeração.
    deslocamento = len(cfg_pauta["fixados"]) if cfg_pauta.get("fixados_publicados") else 0
    # Soma os posts de cada semana anterior (o ritmo pode ter mudado no caminho, ADR-015).
    inicial = cfg_pauta["semana_inicial"]
    primeiro = deslocamento + sum(ritmo_da_semana(_semana_mais(inicial, k), config)["posts_por_semana"]
                                  for k in range(_indice_da_semana(semana, inicial)))
    serie = sequencia(temas, cfg_pauta["ciclo_pilares"], cfg_pauta["fixados"], primeiro + n,
                      pular_pendencia=bool(cfg_pauta.get("pular_pendencias")))
    ano, num = _ler_semana(semana)

    posts = []
    for i, (tema, horario) in enumerate(zip(serie[primeiro:], ritmo["dias"])):
        dia = date.fromisocalendar(ano, num, DIAS_DA_SEMANA[horario["dia"]])
        post = {
            "indice": primeiro + i + 1,              # posição na série (1 = primeiro post do perfil)
            "tema": tema["numero"],
            "titulo": tema["titulo"],
            "pilar": tema["pilar"],
            "formato": tema["formato"],
            "resumo": tema["resumo"],
            "cta": tema["cta"],
            "publico": tema["publico"],
            "fixado": tema["numero"] in cfg_pauta["fixados"] and tema["rodada"] == 1,
            "rodada": tema["rodada"],
            "data": dia.isoformat(),
            "hora": horario["hora"],
            "fuso": pub["fuso"],
            "tempo_liturgico": calendario.tempo_liturgico(dia),
            "cor_liturgica": calendario.cor_liturgica(dia),
        }
        for opcional in ("pilar_original", "pendencia", "a_validar", "importante"):
            if opcional in tema:
                post[opcional] = tema[opcional]
        posts.append(post)

    return {
        "semana": semana,
        "posts": posts,
        "gancho_liturgico": calendario.gancho_semana(ano, num),
    }


def salvar_briefing(briefing: dict, pasta_semanas: Path) -> Path:
    """Grava `<pasta>/AAAA-Www/briefing.json` (UTF-8, chaves ordenadas → bytes estáveis)."""
    destino = Path(pasta_semanas) / briefing["semana"] / "briefing.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(briefing, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    destino.write_text(texto, encoding="utf-8", newline="\n")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera content/semanas/AAAA-Www/briefing.json")
    parser.add_argument("semana", help="semana ISO, ex.: 2026-W41")
    parser.add_argument("--config", default=str(RAIZ / "config.yaml"))
    args = parser.parse_args()
    config = carregar_yaml(Path(args.config))
    temas = carregar_temas(RAIZ / config["pauta"]["temas"])
    caminho = salvar_briefing(montar_briefing(args.semana, config, temas), RAIZ / config["pauta"]["saida"])
    print(caminho)


if __name__ == "__main__":
    main()
