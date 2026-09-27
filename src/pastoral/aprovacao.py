"""Regras comuns da aprovação por e-mail (ADR-009). Determinístico, sem LLM.

O Worker (worker/src/nucleo.js) reproduz exatamente estas funções; os vetores gerados aqui
(`python -m pastoral.aprovacao --vetores tests/fixtures/vetores-python.json`) são verificados no JS.

- agenda.json da semana: para cada post, `agendado_para` (ISO com fuso) e a lista das artes em
  site/midia/<semana>/ — escrito por preview.py, lido pelo Worker.
- itens: exatamente os `posts[]` do aprovacao.json do ADR-008 (numero, agendado_para, legenda_sha256,
  alt_text_sha256, artes[{arquivo, sha256}]).
- versão: sha256 (32 hex) do JSON canônico {semana, posts: itens}. Vai assinada no link; se o conteúdo
  mudar depois do e-mail, o Worker recusa o link antigo.
- link: HMAC-SHA256 (LINK_HMAC_SECRET) sobre "pastoral-link-v1\\n" + s, a, p, e, n, v (um por linha).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from pastoral.publicar import assinar, canonico, sha256, texto_alt, texto_legenda

ACOES = ("aprovar_tudo", "aprovar_post", "ajustar_post")
PREFIXO_LINK = "pastoral-link-v1"
CAMPOS_LINK = ("s", "a", "p", "e", "n", "v")
FORMATOS = {
    "s": r"\d{4}-W\d{2}",
    "a": "|".join(ACOES),
    "p": r"\d{1,4}",
    "e": r"\d{1,12}",
    "n": r"[0-9a-f]{16,64}",
    "v": r"[0-9a-f]{32}",
    "h": r"[0-9a-f]{64}",
}


# ---------- agenda ----------

def agendado_para(item: dict) -> str:
    """'2026-10-06' + '19:00' + 'America/Sao_Paulo' → '2026-10-06T19:00:00-03:00'."""
    ingenua = datetime.fromisoformat(f"{item['data']}T{item['hora']}")
    return ingenua.replace(tzinfo=ZoneInfo(item["fuso"])).isoformat(timespec="seconds")


def montar_agenda(semana: str, posts_dados: dict, briefing: dict) -> dict:
    """Liga cada post (numero) ao briefing (indice = posição global = numero) e lista as artes."""
    por_indice = {b["indice"]: b for b in briefing.get("posts", [])}
    posts = []
    for post in sorted(posts_dados["posts"], key=lambda p: p["numero"]):
        n = post["numero"]
        if n not in por_indice:
            raise ValueError(f"post {n} sem data no briefing.json")
        posts.append({
            "numero": n,
            "agendado_para": agendado_para(por_indice[n]),
            "artes": [f"post-{n}-{i:02d}.jpg" for i in range(1, len(post["slides"]) + 1)],
        })
    return {"semana": semana, "posts": posts}


# ---------- itens e versão ----------

def itens_semana(agenda: dict, posts_dados: dict, ler_arte: Callable[[str], bytes]) -> list[dict]:
    """Os itens que irão para aprovacao.json, com os sha256 calculados sobre o conteúdo atual."""
    por_numero = {p["numero"]: p for p in posts_dados["posts"]}
    itens = []
    for entrada in sorted(agenda["posts"], key=lambda p: p["numero"]):
        n = entrada["numero"]
        post = por_numero.get(n)
        if post is None:
            raise ValueError(f"post {n} da agenda não existe em posts.json")
        if len(entrada["artes"]) != len(post["slides"]):
            raise ValueError(f"post {n}: número de artes não bate com os slides")
        itens.append({
            "numero": n,
            "agendado_para": entrada["agendado_para"],
            "legenda_sha256": sha256(texto_legenda(post).encode("utf-8")),
            "alt_text_sha256": sha256(texto_alt(post).encode("utf-8")),
            "artes": [{"arquivo": a, "sha256": sha256(ler_arte(a))} for a in entrada["artes"]],
        })
    return itens


def versao(semana: str, itens: list[dict]) -> str:
    return sha256(canonico({"semana": semana, "posts": itens}))[:32]


def versao_post(semana: str, item: dict) -> str:
    """Versão de UM post (painel, ADR-011): 32 hex do sha256 do JSON canônico {semana, post: item}.
    Muda se legenda, alt-texts, artes ou data mudarem; a aprovação no painel vale só para ela."""
    return sha256(canonico({"semana": semana, "post": item}))[:32]


# ---------- links assinados ----------

def mensagem_link(params: dict) -> bytes:
    return "\n".join([PREFIXO_LINK] + [str(params.get(c, "")) for c in CAMPOS_LINK]).encode("utf-8")


def assinar_link(segredo: str, params: dict) -> str:
    if not segredo:
        raise ValueError("LINK_HMAC_SECRET vazio")
    return hmac.new(segredo.encode("utf-8"), mensagem_link(params), hashlib.sha256).hexdigest()


def motivo_link_invalido(segredo: str, params: dict, agora_epoch: int) -> str | None:
    """None se o link vale; senão o motivo (o Worker usa as mesmas frases)."""
    if not segredo:
        return "segredo ausente"
    for campo, formato in FORMATOS.items():
        valor = params.get(campo)
        if campo == "p" and params.get("a") == "aprovar_tudo":
            if valor != "":
                return "link malformado"
            continue
        if not isinstance(valor, str) or not re.fullmatch(formato, valor, flags=re.ASCII):
            return "link malformado"
    if not hmac.compare_digest(assinar_link(segredo, params), params["h"]):
        return "assinatura inválida"
    if int(params["e"]) <= agora_epoch:
        return "link expirado"
    return None


def url_link(worker_url: str, segredo: str, semana: str, acao: str, post: int | None,
             expira: int, nonce: str, ver: str) -> str:
    params = {"s": semana, "a": acao, "p": "" if post is None else str(post), "e": str(expira),
              "n": nonce, "v": ver}
    params["h"] = assinar_link(segredo, params)
    return f"{worker_url.rstrip('/')}/a?{urlencode(params)}"


# ---------- aprovacao.json ----------

def montar_aprovacao(existente: dict | None, semana: str, itens: list[dict], alvo: list[int], nonce: str,
                     aprovado_por: str, aprovado_em: str, segredo: str) -> tuple[dict | None, bool]:
    """Junta os posts `alvo` à aprovação existente. Devolve (dados, mudou). Idempotente:
    link já usado (mesmo nonce) ou posts já aprovados com o mesmo conteúdo → (existente, False)."""
    disponiveis = {i["numero"]: i for i in itens}
    faltando = [n for n in alvo if n not in disponiveis]
    if faltando or not alvo:
        raise ValueError(f"post(s) fora da semana: {faltando or alvo}")
    aprovados = {i["numero"]: i for i in (existente or {}).get("posts", [])}
    if existente and existente.get("nonce") == nonce:
        return existente, False
    if all(aprovados.get(n) == disponiveis[n] for n in alvo):
        return existente, False
    for n in alvo:
        aprovados[n] = disponiveis[n]
    dados = {"semana": semana, "aprovado_por": aprovado_por, "aprovado_em": aprovado_em, "nonce": nonce,
             "posts": [aprovados[n] for n in sorted(aprovados)]}
    dados["assinatura"] = assinar(dados, segredo)
    return dados, True


def remover_da_aprovacao(existente: dict | None, semana: str, numero: int, nonce: str, aprovado_por: str,
                         aprovado_em: str, segredo: str) -> tuple[dict | None, bool]:
    """Tira o post `numero` da aprovação e reassina (desfazer no painel, ADR-011). Devolve (dados, mudou);
    se o post não estava aprovado, (existente, False). Sem o post no arquivo, o portão não o publica."""
    if not existente or all(i["numero"] != numero for i in existente.get("posts", [])):
        return existente, False
    dados = {"semana": semana, "aprovado_por": aprovado_por, "aprovado_em": aprovado_em, "nonce": nonce,
             "posts": [i for i in existente["posts"] if i["numero"] != numero]}
    dados["assinatura"] = assinar(dados, segredo)
    return dados, True


# ---------- vetores para o teste cruzado ----------

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "semana-exemplo"


def gerar_vetores(fixture: Path = FIXTURE) -> dict:
    """Casos que o JS precisa reproduzir byte a byte."""
    semana = "2026-W41"
    pasta = fixture / "content" / "semanas" / semana
    posts = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
    agenda = json.loads((pasta / "agenda.json").read_text(encoding="utf-8"))

    def ler_arte(arquivo):
        return (fixture / "site" / "midia" / semana / arquivo).read_bytes()

    objetos = [
        {"b": 1, "a": [3, {"z": None, "é": True, "e": False}], "Z": "maiúscula antes"},
        {"texto": "aspas \" barra \\ nova\nlinha tab\t ctrl\u0001 del\u007f acento ção emoji 🙏 / ok"},
        {"\U0001F600": "astral", "￿": "bmp alto", "ä": "latin", "": "vazia"},
        {"lista": [], "obj": {}, "zero": 0, "neg": -42, "grande": 9007199254740991},
    ]
    legendas = [
        {"legenda": "  espaço antes e depois \n", "hashtags": ["#a", "#b"]},
        {"legenda": "  nbsp e em space　", "hashtags": []},
        {"legenda": "\x1c\x1f separadores python \x85", "hashtags": ["#x"]},
        {"legenda": "﻿BOM não é espaço no Python﻿"},
    ]
    itens = itens_semana(agenda, posts, ler_arte)
    ver = versao(semana, itens)
    links = []
    for acao, post in (("aprovar_tudo", None), ("aprovar_post", 12), ("ajustar_post", 13)):
        params = {"s": semana, "a": acao, "p": "" if post is None else str(post), "e": "1791000000",
                  "n": "0123456789abcdef", "v": ver}
        params["h"] = assinar_link("segredo-link-de-teste", params)
        links.append(params)
    aprov, _ = montar_aprovacao(None, semana, itens, [12, 13], "0123456789abcdef", "Diogo",
                                "2026-10-02T13:00:00+00:00", "segredo-aprovacao-de-teste")
    remocao, _ = remover_da_aprovacao(aprov, semana, 12, "fedcba9876543210", "Aprovador",
                                      "2026-10-03T10:00:00+00:00", "segredo-aprovacao-de-teste")
    return {
        "gerado_por": "python -m pastoral.aprovacao --vetores (não editar à mão)",
        "canonico": [{"entrada": o, "saida": canonico(o).decode("utf-8"),
                      "sha256": sha256(canonico(o))} for o in objetos],
        "assinar": [{"segredo": "segredo-aprovacao-de-teste", "dados": o,
                     "assinatura": assinar(o, "segredo-aprovacao-de-teste")} for o in objetos],
        "legendas": [{"post": p, "texto": texto_legenda(p)} for p in legendas],
        "semana": {"semana": semana, "itens": itens, "versao": ver,
                   "artes_base64": {a: base64.b64encode(ler_arte(a)).decode("ascii")
                                    for e in agenda["posts"] for a in e["artes"]}},
        "links": {"segredo": "segredo-link-de-teste", "agora": 1790000000, "validos": links},
        "aprovacao": aprov,
        "versao_post": {str(i["numero"]): versao_post(semana, i) for i in itens},
        "remocao": remocao,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Utilitários da aprovação (vetores do teste cruzado)")
    ap.add_argument("--vetores", type=Path, required=True, help="grava os vetores em JSON")
    args = ap.parse_args(argv)
    texto = json.dumps(gerar_vetores(), ensure_ascii=False, indent=2) + "\n"
    args.vetores.write_text(texto, encoding="utf-8", newline="\n")
    print(args.vetores)
    return 0


if __name__ == "__main__":
    sys.exit(main())
