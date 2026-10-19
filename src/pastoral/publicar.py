"""Portão de publicação (arquitetura §1.1 e §5, ADR-008). Determinístico, sem LLM.

Um post só vai ao ar se TODAS as condições valem:
1. existe `content/semanas/<semana>/aprovacao.json`;
2. a assinatura HMAC-SHA256 (segredo `APROVACAO_HMAC_SECRET`) sobre o JSON canônico confere;
3. a `semana` assinada é a da pasta;
4. o sha256 de cada arte em `site/midia/<semana>/`, da legenda final e dos alt-texts é igual ao aprovado;
5. `agora` ≥ `agendado_para` (data com fuso obrigatório);
6. o número do post não consta em nenhum ledger (`content/semanas/*/publicado.json`, `content/estreia/publicado.json`);
7. (só na publicação real) a arte servida na URL pública tem o mesmo sha256 do aprovado.

Alerta (2026-10-13): post da agenda com data a menos de 30 h (antes ou depois de agora) que não está em
nenhum aprovacao.json nem no ledger sai como "SEM APROVAÇÃO" e o comando termina com erro — o job fica
vermelho e o GitHub avisa por e-mail. Antes, uma aprovação que ficou como rascunho no aparelho fazia o post
simplesmente não sair, sem aviso nenhum.

Fila (ADR-015, `publicacao.fila: true`): item aprovado sem `agendado_para` (null) entra na fila; a cada
execução sai no máximo UMA publicação por semana (horários de `publicacao.dias`), na ordem do `aprovado_em`
de cada item (data fixa vencida primeiro). Regras e alertas em fila.py.

Modo `--dry-run` é o padrão: publica de verdade só com a variável de ambiente `PUBLICAR=1`
(e sem `--dry-run`). Em dry-run o cliente da Meta nem é criado.

JSON canônico (o Worker precisa gerar igual): chaves ordenadas, separadores "," e ":" sem espaço,
UTF-8 sem escapar acentos, sem o campo "assinatura". Assinatura = hex minúsculo.

Uso: python -m pastoral.publicar [--semana 2026-W41] [--dry-run] [--agora ISO]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pastoral import fila, meta

RAIZ = Path(__file__).resolve().parents[2]


# ---------- assinatura e hashes ----------

def canonico(dados: dict) -> bytes:
    return json.dumps(dados, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def assinar(dados: dict, segredo: str) -> str:
    """HMAC-SHA256 do JSON canônico, sem o campo `assinatura`."""
    sem = {k: v for k, v in dados.items() if k != "assinatura"}
    return hmac.new(segredo.encode("utf-8"), canonico(sem), hashlib.sha256).hexdigest()


def assinatura_valida(dados: dict, segredo: str) -> bool:
    if not segredo or not isinstance(dados.get("assinatura"), str):
        return False
    return hmac.compare_digest(assinar(dados, segredo), dados["assinatura"])


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def texto_legenda(post: dict) -> str:
    """Legenda que vai ao ar: texto + hashtags numa linha própria (se houver)."""
    legenda = post.get("legenda", "").strip()
    hashtags = " ".join(post.get("hashtags") or [])
    return f"{legenda}\n\n{hashtags}" if hashtags else legenda


def texto_alt(post: dict) -> str:
    """Alt-texts dos slides, na ordem, um por linha (entra no hash aprovado)."""
    return "\n".join(s.get("alt_text", "") for s in post.get("slides", []))


def url_publica(base_url: str, semana: str, arquivo: str) -> str:
    return f"{base_url.rstrip('/')}/midia/{semana}/{arquivo}"


def baixar_urllib(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resposta:
        return resposta.read()


# ---------- ledger ----------

def _ler_json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def numeros_publicados(raiz: Path) -> set[int]:
    """Números de post que já saíram, em qualquer ledger (a numeração é global)."""
    caminhos = list((raiz / "content" / "semanas").glob("*/publicado.json"))
    caminhos.append(raiz / "content" / "estreia" / "publicado.json")
    numeros = set()
    for c in caminhos:
        if c.exists():
            numeros |= {int(p["numero"]) for p in _ler_json(c).get("posts", []) if "numero" in p}
    return numeros


def datas_publicadas(raiz: Path) -> list[datetime]:
    """Quando cada post saiu (ledgers das semanas): a fila usa isso para saber se a semana já foi servida."""
    datas = []
    for c in (raiz / "content" / "semanas").glob("*/publicado.json"):
        for p in _ler_json(c).get("posts", []):
            try:
                d = datetime.fromisoformat(p["publicado_em"])
            except (KeyError, TypeError, ValueError):
                continue
            if d.tzinfo is not None:
                datas.append(d)
    return datas


def registrar(raiz: Path, semana: str, entrada: dict) -> None:
    caminho = raiz / "content" / "semanas" / semana / "publicado.json"
    ledger = _ler_json(caminho) if caminho.exists() else {"semana": semana, "posts": []}
    ledger["posts"].append(entrada)
    caminho.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- portão ----------

def _recusa(semana, numero, motivo, grave):
    return {"semana": semana, "numero": numero, "motivo": motivo, "grave": grave}


def avaliar_semana(raiz: Path, pasta_midia: Path, semana: str, segredo: str, agora: datetime,
                   publicados: set[int], fila_ligada: bool = False) -> tuple[list[dict], list[dict]]:
    """Devolve (prontos, recusados). Cada pronto traz o post e o item aprovado (com `agendado_para` e o
    carimbo `aprovado_em` do item, ou do arquivo). Com a fila ligada, item sem data é aceito (quem decide a
    semana é fila.escolher); sem fila, data ausente é recusa grave."""
    pasta = raiz / "content" / "semanas" / semana
    arq_aprov = pasta / "aprovacao.json"
    if not arq_aprov.exists():
        return [], [_recusa(semana, None, "sem aprovacao.json", False)]
    try:
        aprov = _ler_json(arq_aprov)
    except ValueError:
        return [], [_recusa(semana, None, "aprovacao.json ilegível", True)]
    if not segredo:
        return [], [_recusa(semana, None, "APROVACAO_HMAC_SECRET ausente: assinatura não verificável", True)]
    if not assinatura_valida(aprov, segredo):
        return [], [_recusa(semana, None, "assinatura inválida em aprovacao.json", True)]
    if aprov.get("semana") != semana:
        return [], [_recusa(semana, None, f"aprovação assinada para {aprov.get('semana')!r}, não {semana}", True)]
    arq_posts = pasta / "posts.json"
    if not arq_posts.exists():
        return [], [_recusa(semana, None, "posts.json ausente", True)]
    posts = {p["numero"]: p for p in _ler_json(arq_posts).get("posts", [])}

    prontos, recusados = [], []
    for item in aprov.get("posts", []):
        n = item.get("numero")
        post = posts.get(n)
        if post is None:
            recusados.append(_recusa(semana, n, "post aprovado não existe em posts.json", True))
            continue
        if n in publicados:
            recusados.append(_recusa(semana, n, "já publicado (consta no ledger)", False))
            continue
        if item.get("agendado_para") is None and fila_ligada:
            pass                                 # fila: a data é decidida na hora de publicar (fila.escolher)
        else:
            try:
                agendado = datetime.fromisoformat(item["agendado_para"])
            except (KeyError, TypeError, ValueError):
                recusados.append(_recusa(semana, n, "agendado_para ausente ou inválido", True))
                continue
            if agendado.tzinfo is None:
                recusados.append(_recusa(semana, n, "agendado_para sem fuso horário", True))
                continue
            if agora < agendado:
                recusados.append(_recusa(semana, n, f"ainda não chegou a data agendada ({item['agendado_para']})", False))
                continue
        if item.get("legenda_sha256") != sha256(texto_legenda(post).encode("utf-8")):
            recusados.append(_recusa(semana, n, "legenda difere da aprovada", True))
            continue
        if item.get("alt_text_sha256") != sha256(texto_alt(post).encode("utf-8")):
            recusados.append(_recusa(semana, n, "alt-text difere do aprovado", True))
            continue
        artes = item.get("artes") or []
        if len(artes) != len(post.get("slides", [])) or not 1 <= len(artes) <= 10:
            recusados.append(_recusa(semana, n, "número de artes não bate com os slides (ou fora de 1–10)", True))
            continue
        problema = None
        for arte in artes:
            caminho = pasta_midia / semana / arte.get("arquivo", "")
            if not arte.get("arquivo") or not caminho.is_file():
                problema = f"arte ausente: {arte.get('arquivo')}"
                break
            if sha256(caminho.read_bytes()) != arte.get("sha256"):
                problema = f"arte difere da aprovada: {arte['arquivo']}"
                break
        if problema:
            recusados.append(_recusa(semana, n, problema, True))
            continue
        prontos.append({"semana": semana, "numero": n, "post": post, "item": item,
                        "agendado_para": item.get("agendado_para"),
                        "aprovado_em": item.get("aprovado_em") or aprov.get("aprovado_em")})
    return prontos, recusados


def conferir_urls(pronto: dict, base_url: str, baixar) -> str | None:
    """Confere que o Pages serve exatamente as artes aprovadas. Devolve o problema, ou None."""
    for arte in pronto["item"]["artes"]:
        url = url_publica(base_url, pronto["semana"], arte["arquivo"])
        try:
            conteudo = baixar(url)
        except Exception as erro:
            return f"URL pública inacessível ({url}): {erro}"
        if sha256(conteudo) != arte["sha256"]:
            return f"URL pública serve arte diferente da aprovada ({url})"
    return None


def publicar_post(cliente, pronto: dict, base_url: str, intervalo: float, maximo: float,
                  agora: datetime | None = None) -> dict:
    """Cria contêineres, espera FINISHED e chama media_publish. Só é chamada para posts aprovados.
    `agora` vai para o ledger (publicado_em): é o relógio do portão, para a fila ser coerente com ele."""
    post, item, semana = pronto["post"], pronto["item"], pronto["semana"]
    legenda = texto_legenda(post)
    urls = [url_publica(base_url, semana, a["arquivo"]) for a in item["artes"]]
    alts = [s.get("alt_text") for s in post["slides"]]
    if len(urls) == 1:
        conteiner = cliente.criar_imagem(urls[0], legenda, alt_text=alts[0])
    else:
        filhos = [cliente.criar_item_carrossel(u, alt_text=a) for u, a in zip(urls, alts)]
        for f in filhos:
            cliente.aguardar(f, intervalo=intervalo, maximo=maximo)
        conteiner = cliente.criar_carrossel(filhos, legenda)
    cliente.aguardar(conteiner, intervalo=intervalo, maximo=maximo)
    media_id = cliente.media_publish(conteiner)
    try:
        permalink = cliente.permalink(media_id)
    except meta.ErroMeta:
        permalink = None          # já está no ar: o ledger é gravado mesmo assim
    return {"numero": pronto["numero"], "ig_media_id": media_id, "permalink": permalink,
            "publicado_em": (agora or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
            "metodo": "api", "artes": len(urls)}


JANELA_ALERTA_H = 30      # cobre a véspera (o portão roda às 19h) e o próprio dia, depois da hora


def _aprovados(pasta: Path) -> set[int]:
    """Números listados no aprovacao.json da semana (a validade completa é do avaliar_semana)."""
    arq = pasta / "aprovacao.json"
    try:
        return {int(i["numero"]) for i in _ler_json(arq).get("posts", [])} if arq.exists() else set()
    except (ValueError, KeyError, TypeError):
        return set()


def sem_aprovacao(raiz: Path, semana: str, agora: datetime, publicados: set[int]) -> list[dict]:
    """Posts da agenda.json da semana com data perto de agora que ninguém aprovou e que não saíram."""
    pasta = raiz / "content" / "semanas" / semana
    arq = pasta / "agenda.json"
    if not arq.exists():
        return []
    aprovados = _aprovados(pasta)
    alertas = []
    for entrada in _ler_json(arq).get("posts", []):
        n = entrada.get("numero")
        try:
            agendado = datetime.fromisoformat(entrada["agendado_para"])
        except (KeyError, TypeError, ValueError):
            continue
        if agendado.tzinfo is None or n in publicados or n in aprovados:
            continue
        if abs((agendado - agora).total_seconds()) <= JANELA_ALERTA_H * 3600:
            alertas.append({"semana": semana, "numero": n, "agendado_para": entrada["agendado_para"]})
    return alertas


def semanas_existentes(raiz: Path) -> list[str]:
    pasta = raiz / "content" / "semanas"
    return sorted(p.name for p in pasta.iterdir() if p.is_dir()) if pasta.exists() else []


def executar(raiz: Path, config: dict, segredo: str, agora: datetime, cliente=None, dry_run: bool = True,
             semanas: list[str] | None = None, baixar=baixar_urllib) -> dict:
    """Roda o portão em todas as semanas (ou nas pedidas). Em dry-run não chama a Meta nem grava ledger.
    Com `publicacao.fila` ligada (ADR-015), sai no máximo uma publicação por semana, em ordem de aprovação."""
    raiz = Path(raiz)
    midia = config.get("midia", {})
    base_url = midia.get("base_url", "")
    pasta_midia = raiz / midia.get("pasta", "site/midia")
    m = config.get("meta", {})
    intervalo, maximo = m.get("poll_intervalo_s", 60), m.get("poll_max_s", 300)
    pub = config.get("publicacao", {})
    fila_ligada = bool(pub.get("fila"))
    publicados_antes = numeros_publicados(raiz)

    resultado = {"prontos": [], "recusados": [], "publicados": [], "erros": [], "sem_aprovacao": [], "alerta_fila": None}
    candidatos = []
    for semana in semanas or semanas_existentes(raiz):
        resultado["sem_aprovacao"] += sem_aprovacao(raiz, semana, agora, publicados_antes)
        prontos, recusados = avaliar_semana(raiz, pasta_midia, semana, segredo, agora, publicados_antes, fila_ligada)
        resultado["recusados"] += recusados
        candidatos += prontos

    if fila_ligada:
        publicados_em = datas_publicadas(raiz)
        escolhido, restantes = fila.escolher(candidatos, publicados_em, agora, pub)
        resultado["alerta_fila"] = fila.alerta(candidatos, publicados_em, agora, pub)
        primeira = 2 if escolhido else 1          # posição na fila contando quem sai agora
        for k, r in enumerate(restantes, start=primeira):
            resultado["recusados"].append(_recusa(r["semana"], r["numero"],
                                                  f"aguarda o próximo horário (fila, posição {k})", False))
        candidatos = [escolhido] if escolhido else []

    for pronto in candidatos:
        semana = pronto["semana"]
        resumo = {"semana": semana, "numero": pronto["numero"], "artes": len(pronto["item"]["artes"])}
        if dry_run:
            resultado["prontos"].append(resumo)
            continue
        problema = conferir_urls(pronto, base_url, baixar)
        if problema:
            resultado["recusados"].append(_recusa(semana, pronto["numero"], problema, True))
            continue
        resultado["prontos"].append(resumo)
        try:
            entrada = publicar_post(cliente, pronto, base_url, intervalo, maximo, agora)
        except meta.ErroMeta as erro:
            resultado["erros"].append({"semana": semana, "numero": pronto["numero"], "erro": str(erro)})
            continue
        registrar(raiz, semana, entrada)
        publicados_antes.add(pronto["numero"])
        resultado["publicados"].append({"semana": semana, **entrada})
    return resultado


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Portão de publicação (dry-run por padrão).")
    ap.add_argument("--semana", action="append", help="AAAA-Www (repetível); padrão: todas")
    ap.add_argument("--dry-run", action="store_true", help="força dry-run mesmo com PUBLICAR=1")
    ap.add_argument("--agora", help="data/hora ISO com fuso (testes e simulação)")
    ap.add_argument("--raiz", default=str(RAIZ))
    ap.add_argument("--config", default=str(RAIZ / "config.yaml"))
    args = ap.parse_args(argv)

    config = meta.carregar_config(Path(args.config))
    agora = datetime.fromisoformat(args.agora) if args.agora else datetime.now(timezone.utc)
    dry_run = args.dry_run or os.environ.get("PUBLICAR") != "1"
    segredo = os.environ.get("APROVACAO_HMAC_SECRET", "").strip()   # Enter colado no secret não conta (ADR-009)
    cliente = None
    if not dry_run:
        try:
            cliente = meta.ClienteMeta.do_ambiente(config)
        except meta.ErroMeta as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 1

    modo = "dry-run" if dry_run else "PUBLICAÇÃO REAL"
    print(f"Portão de publicação — modo {modo} — agora {agora.isoformat(timespec='minutes')}")
    r = executar(Path(args.raiz), config, segredo, agora, cliente=cliente, dry_run=dry_run, semanas=args.semana)
    for d in r["recusados"]:
        marca = "ALERTA" if d["grave"] else "aguarda"
        print(f"  [{marca}] {d['semana']} post {d['numero']}: {d['motivo']}")
    for d in r["prontos"]:
        verbo = "publicaria" if dry_run else "aprovado para publicar"
        print(f"  [ok] {d['semana']} post {d['numero']}: {verbo} ({d['artes']} artes)")
    for d in r["publicados"]:
        print(f"  [publicado] {d['semana']} post {d['numero']}: {d['permalink'] or d['ig_media_id']}")
    for d in r["erros"]:
        print(f"  [ERRO] {d['semana']} post {d['numero']}: {d['erro']}")
    for d in r["sem_aprovacao"]:
        print(f"  [ALERTA] {d['semana']} post {d['numero']}: SEM APROVAÇÃO para {d['agendado_para']} — "
              "abra o painel e toque em \"Enviar respostas\" (rascunho no aparelho não vale)")
    if r["alerta_fila"]:
        print(f"  [ALERTA] {r['alerta_fila']} — abra o painel, aprove e toque em \"Enviar respostas\"")
    if dry_run:
        print("dry-run: nada foi enviado à Meta nem gravado no ledger.")
    grave = any(d["grave"] for d in r["recusados"]) or r["erros"] or r["sem_aprovacao"] or r["alerta_fila"]
    return 1 if grave else 0


if __name__ == "__main__":
    sys.exit(main())
