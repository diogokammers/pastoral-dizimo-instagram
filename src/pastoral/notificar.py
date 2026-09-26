"""E-mail semanal de aprovação (fatia 5, ADR-009). Determinístico, sem LLM.

Envia pela API HTTP da Resend (urllib, sem SDK) um resumo de cada post da semana, o link da prévia no
GitHub Pages e links assinados para o Worker: aprovar_tudo, aprovar_post N e ajustar_post N.
Cada link: HMAC-SHA256 (LINK_HMAC_SECRET) sobre semana, ação, post, expiração (7 dias), nonce próprio e
a versão do conteúdo (aprovacao.versao) — se o conteúdo mudar depois do e-mail, o Worker recusa o link.

Sem domínio próprio: remetente onboarding@resend.dev, e a Resend só entrega ao e-mail dono da conta
(config.yaml `aprovacao.email`). Segredos só por ambiente: RESEND_API_KEY e LINK_HMAC_SECRET; a chave
nunca aparece em mensagens de erro.

Os links são credenciais de aprovação: o HTML do e-mail nunca é gravado dentro do repositório (público).

Uso: python -m pastoral.notificar 2026-W41 [--dry-run [--saida arquivo.html]]
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

from pastoral import aprovacao, meta
from pastoral.preview import data_por_extenso

RAIZ = Path(__file__).resolve().parents[2]
URL_RESEND = "https://api.resend.com/emails"
PLACEHOLDER = "SEU-SUBDOMINIO"


class ErroNotificacao(RuntimeError):
    """Falha ao montar ou enviar o e-mail (mensagem já mascarada)."""


def e(texto) -> str:
    return escape(str(texto), quote=True)


# ---------- links ----------

def gerar_links(worker_url: str, segredo: str, semana: str, numeros: list[int], ver: str, agora_epoch: int,
                validade_dias: int = 7) -> dict:
    """Um link por ação, cada um com nonce próprio."""
    expira = agora_epoch + validade_dias * 86400

    def link(acao, post=None):
        return aprovacao.url_link(worker_url, segredo, semana, acao, post, expira, secrets.token_hex(8), ver)

    return {"aprovar_tudo": link("aprovar_tudo"),
            "posts": {n: {"aprovar": link("aprovar_post", n), "ajustar": link("ajustar_post", n)} for n in numeros}}


# ---------- corpo ----------

ESTILO_BOTAO = ("display:inline-block;padding:10px 16px;border-radius:6px;text-decoration:none;"
                "font-weight:600;margin:4px 6px 4px 0;")


def _botao(url: str, rotulo: str, principal: bool = False) -> str:
    cores = "background:#A3121C;color:#ffffff;" if principal else "background:#F3F2EE;color:#7E0F17;border:1px solid #A3121C;"
    return f'<a href="{e(url)}" style="{ESTILO_BOTAO}{cores}">{e(rotulo)}</a>'


def montar_email(semana: str, dados: dict, agenda: dict, links: dict, previa_url: str, validade_dias: int) -> dict:
    quando = {p["numero"]: data_por_extenso(p["agendado_para"]) for p in agenda["posts"]}
    blocos, linhas = [], []
    for post in sorted(dados["posts"], key=lambda p: p["numero"]):
        n = post["numero"]
        primeira = (post.get("legenda", "").strip().splitlines() or [""])[0]
        conferir = "".join(f"<li>{e(c)}</li>" for c in post.get("a_conferir", []))
        blocos.append(f"""
<div style="border:1px solid #ddd;border-radius:8px;padding:14px 16px;margin:14px 0">
  <p style="margin:0 0 4px;color:#5F5A57;font-size:13px">Post {n} · {e(post['pilar'])} · {e(quando[n])}</p>
  <p style="margin:0 0 6px;font-size:17px;font-weight:600">{e(post['titulo'])}</p>
  <p style="margin:0 0 6px">{e(primeira)}</p>
  <p style="margin:0 0 6px;color:#5F5A57;font-size:13px">{len(post['slides'])} imagem(ns) · CTA: {e(post['cta'])}</p>
  {f'<p style="margin:6px 0 2px;font-size:13px"><b>A conferir:</b></p><ul style="margin:0;font-size:13px">{conferir}</ul>' if conferir else ''}
  <p style="margin:10px 0 0">{_botao(links['posts'][n]['aprovar'], f'Aprovar post {n}')}{_botao(links['posts'][n]['ajustar'], f'Pedir ajuste no post {n}')}</p>
</div>""")
        linhas += [f"Post {n} — {post['titulo']} ({quando[n]})", f"  {primeira}",
                   f"  Aprovar: {links['posts'][n]['aprovar']}", f"  Pedir ajuste: {links['posts'][n]['ajustar']}", ""]
    html = f"""<!doctype html><html lang="pt-BR"><body style="margin:0;background:#F3F2EE">
<div style="max-width:600px;margin:0 auto;padding:20px 16px;font:15px/1.5 Arial,Helvetica,sans-serif;color:#1E1B1B;background:#ffffff">
<p style="margin:0 0 4px;font-size:20px;font-weight:600;color:#7E0F17">Posts da semana {e(semana)}</p>
<p style="margin:0 0 12px">Nada foi publicado. Veja a <a href="{e(previa_url)}" style="color:#A3121C">prévia da semana</a>
(imagens, legendas e textos alternativos) e aprove ou peça ajuste. Cada botão abre uma página de confirmação.</p>
<p style="margin:0 0 12px">{_botao(links['aprovar_tudo'], 'Aprovar tudo', principal=True)}</p>
{''.join(blocos)}
<p style="color:#5F5A57;font-size:12px">Os links valem {validade_dias} dias e só funcionam para o conteúdo desta prévia.
Se um post for refeito, chegará um e-mail novo. Não encaminhe este e-mail: os botões aprovam a publicação.</p>
</div></body></html>"""
    texto = "\n".join([f"Posts da semana {semana} — nada foi publicado.", f"Prévia: {previa_url}", "",
                       f"Aprovar tudo: {links['aprovar_tudo']}", ""] + linhas +
                      [f"Os links valem {validade_dias} dias. Não encaminhe este e-mail."])
    return {"assunto": f"Aprovação dos posts da semana {semana}", "html": html, "texto": texto}


def preparar(raiz: Path, semana: str, config: dict, segredo: str, agora_epoch: int) -> dict:
    """Lê posts.json, agenda.json e as artes publicadas; calcula a versão e monta links e e-mail."""
    raiz = Path(raiz)
    pasta = raiz / "content" / "semanas" / semana
    dados = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
    agenda = json.loads((pasta / "agenda.json").read_text(encoding="utf-8"))
    midia = raiz / config.get("midia", {}).get("pasta", "site/midia") / semana
    itens = aprovacao.itens_semana(agenda, dados, lambda a: (midia / a).read_bytes())
    ver = aprovacao.versao(semana, itens)
    cfg = config["aprovacao"]
    validade = int(cfg.get("validade_dias", 7))
    links = gerar_links(cfg["worker_url"], segredo, semana, [i["numero"] for i in itens], ver, agora_epoch, validade)
    previa = f"{config['midia']['base_url'].rstrip('/')}/semanas/{semana}/"
    return {"versao": ver, "links": links, "email": montar_email(semana, dados, agenda, links, previa, validade)}


# ---------- envio ----------

def transporte_urllib(url: str, corpo: bytes, headers: dict) -> tuple[int, bytes]:
    pedido = urllib.request.Request(url, data=corpo, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


def enviar_resend(api_key: str, cfg: dict, email: dict, transporte=None) -> str:
    """POST /emails (uma tentativa só, sem reenvio automático). Devolve o id do e-mail."""
    transporte = transporte or transporte_urllib
    corpo = {"from": cfg["remetente"], "to": [cfg["email"]], "subject": email["assunto"],
             "html": email["html"], "text": email["texto"]}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "User-Agent": "pastoral-dizimo-notificar/1.0"}
    try:
        status, resposta = transporte(URL_RESEND, json.dumps(corpo, ensure_ascii=False).encode("utf-8"), headers)
    except Exception as erro:       # rede: a mensagem pode conter a URL, nunca a chave, mas mascaramos igual
        raise ErroNotificacao(meta.mascarar(f"falha de rede na Resend: {erro}", api_key)) from None
    texto = resposta.decode("utf-8", errors="replace")
    if not 200 <= status < 300:
        raise ErroNotificacao(meta.mascarar(f"Resend respondeu {status}: {texto[:300]}", api_key))
    try:
        return json.loads(texto)["id"]
    except (ValueError, KeyError):
        raise ErroNotificacao(meta.mascarar(f"resposta inesperada da Resend: {texto[:300]}", api_key)) from None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Envia o e-mail de aprovação da semana (Resend)")
    ap.add_argument("semana", help="AAAA-Www")
    ap.add_argument("--dry-run", action="store_true", help="grava o HTML em arquivo e não envia")
    ap.add_argument("--saida", type=Path, help="arquivo do HTML no dry-run (padrão: pasta temporária)")
    ap.add_argument("--raiz", type=Path, default=RAIZ)
    ap.add_argument("--config", type=Path, default=RAIZ / "config.yaml")
    args = ap.parse_args(argv)

    config = meta.carregar_config(args.config)
    segredo = os.environ.get("LINK_HMAC_SECRET", "").strip()
    chave = os.environ.get("RESEND_API_KEY", "").strip()
    if args.dry_run:
        if not segredo:
            print("aviso: LINK_HMAC_SECRET ausente; links assinados com segredo fictício (não valem no Worker).")
            segredo = "dry-run-sem-segredo"
    else:
        faltando = [n for n, v in (("RESEND_API_KEY", chave), ("LINK_HMAC_SECRET", segredo)) if not v]
        if faltando:
            print(f"Erro: {', '.join(faltando)} ausente(s) no ambiente (GitHub Secrets). Nada foi enviado.", file=sys.stderr)
            return 1
        if PLACEHOLDER in config["aprovacao"]["worker_url"]:
            print("Erro: aprovacao.worker_url ainda é o placeholder; faça o deploy do Worker (ADR-009) "
                  "e troque a URL no config.yaml. Nada foi enviado.", file=sys.stderr)
            return 1

    try:
        prep = preparar(args.raiz, args.semana, config, segredo, int(time.time()))
    except (OSError, ValueError, KeyError) as erro:
        print(f"Erro ao montar o e-mail: {erro}", file=sys.stderr)
        return 1

    if args.dry_run:
        saida = args.saida or Path(tempfile.gettempdir()) / f"pastoral-email-{args.semana}.html"
        saida.write_text(prep["email"]["html"], encoding="utf-8")
        print(f"dry-run: e-mail gravado em {saida} (não enviado). Versão {prep['versao']}.")
        return 0

    try:
        email_id = enviar_resend(chave, config["aprovacao"], prep["email"])
    except ErroNotificacao as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    print(f"E-mail da semana {args.semana} enviado (id {email_id}, versão {prep['versao']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
