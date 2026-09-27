"""Validação da página PUBLICADA no GitHub Pages com Playwright (ADR-011).

--modo teste   página de teste (site/aprovacao-teste/, Worker de TESTE): sem código = só leitura; com o link
               curto de teste, desfaz/aprova/pede ajuste nos posts da SEMANA DE TESTE e confere os blocos,
               a persistência (recarregar) e o aprovacao.json no ramo teste-aprovacao.
--modo fumaca  página real (site/aprovacao/, Worker de produção): só leitura sem código; com o link real,
               confere que entra em modo de decisão — NUNCA clica em Aprovar/Ajuste/Desfazer.

O link com o código é lido de um arquivo e nunca é impresso (a saída mascara o código).
Uso: python scripts/e2e_pagina.py --modo teste --pagina URL --link-arquivo ARQ [--checkout DIR] --saida ARQ.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTE = ("901", "902")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modo", choices=["teste", "fumaca"], required=True)
    ap.add_argument("--pagina", required=True)
    ap.add_argument("--link-arquivo", required=True)
    ap.add_argument("--checkout", help="checkout do ramo teste-aprovacao (modo teste)")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--capturas", help="pasta para as capturas de tela (fora do repositório)")
    a = ap.parse_args(argv)
    link = Path(a.link_arquivo).read_text(encoding="utf-8").strip()
    codigo = link.rsplit("/", 1)[-1]
    if a.modo == "teste" and "teste" not in link:
        raise SystemExit("recusado: no modo teste use o link do Worker de TESTE")
    passos, api = [], []

    def mascarar(t):
        return str(t).replace(codigo, "<CODIGO>")

    def registrar(nome, ok, **ev):
        passos.append(json.loads(mascarar(json.dumps({"passo": nome, "ok": bool(ok), **ev}, ensure_ascii=False))))
        print(("OK   " if ok else "FALHA") + " " + nome, flush=True)

    def git(*args):
        return subprocess.run(["git", "-C", a.checkout, *args], capture_output=True, text=True, encoding="utf-8",
                              check=True).stdout.strip()

    def aprovados_no_ramo():
        git("fetch", "-q", "origin", "teste-aprovacao")
        git("reset", "-q", "--hard", "origin/teste-aprovacao")
        arq = Path(a.checkout) / "content" / "semanas" / "2099-W01" / "aprovacao.json"
        return [p["numero"] for p in json.loads(arq.read_text(encoding="utf-8"))["posts"]] if arq.exists() else None

    capt = Path(a.capturas) if a.capturas else None
    if capt:
        capt.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        nav = pw.chromium.launch()

        def nova():
            ctx = nav.new_context(viewport={"width": 1280, "height": 900}, locale="pt-BR")
            pg = ctx.new_page()
            pg.on("request", lambda r: api.append({"metodo": r.method, "url": mascarar(r.url),
                                                   "auth": "Bearer <CODIGO>" if r.headers.get("authorization") == f"Bearer {codigo}"
                                                   else r.headers.get("authorization")})
                  if "/api/" in r.url else None)
            return ctx, pg

        def ids(pg, lista):
            return pg.eval_on_selector_all(f"#lista-{lista} > li", "els => els.map(e => e.dataset.n)")

        def agendadas(pg):
            return pg.eval_on_selector_all("#lista-agendadas > li:not([hidden])", "els => els.map(e => e.dataset.n)")

        def abrir_blocos(pg):
            for b in pg.locator(".bloco-botao").all():
                if b.get_attribute("aria-expanded") == "false":
                    b.click()

        def foto(pg, nome):
            if capt:
                pg.screenshot(path=str(capt / f"{nome}.png"), full_page=False)

        # 1) sem código: só leitura
        ctx, pg = nova()
        pg.goto(a.pagina)
        pg.wait_for_load_state("networkidle")
        abrir_blocos(pg)
        pend = ids(pg, "pendentes")
        publicadas = pg.eval_on_selector_all("#bloco-publicadas .item-titulo", "els => els.map(e => e.dataset.abrir)")
        texto = pg.inner_text("#painel")
        registrar("sem código: só leitura, sem chamar a API, publicados fora de Pendentes, frase removida",
                  "so-leitura" in pg.evaluate("document.body.className") and not api
                  and not {"1", "2", "3"} & set(pend) and publicadas == ["1", "2", "3"]
                  and "nada disso foi publicado" not in texto and "Simulação para aprovação" in texto
                  and not pg.locator(".btn-aprovar:visible").count() and agendadas(pg) == [],
                  pendentes=pend, publicadas=publicadas, chamadas_api=len(api), acesso=pg.inner_text("#acesso"))
        foto(pg, f"{a.modo}-1-so-leitura")
        ctx.close()

        # 2) pelo link curto: redireciona, tira o código da barra, entra como Padre
        ctx, pg = nova()
        resposta = pg.goto(link)
        pg.wait_for_load_state("networkidle")
        abrir_blocos(pg)
        url_final = pg.url
        registrar("link curto → página; o código sai da barra de endereço; modo de decisão como Padre",
                  codigo not in url_final and url_final.startswith(a.pagina) and "Padre" in pg.inner_text("#acesso")
                  and "so-leitura" not in pg.evaluate("document.body.className")
                  and api and api[0]["url"].endswith("/api/estado") and api[0]["auth"] == "Bearer <CODIGO>"
                  and all(codigo not in c["url"] for c in api),
                  url_final=mascarar(url_final), acesso=pg.inner_text("#acesso"), status_final=resposta.status if resposta else None,
                  chamadas_api=api[:])
        estado0 = {k: ids(pg, k) for k in ("pendentes", "aprovadas", "ajuste")}
        registrar("estado carregado do D1", True, blocos=estado0, agendadas=agendadas(pg))
        foto(pg, f"{a.modo}-2-com-codigo")

        if a.modo == "fumaca":
            registrar("fumaça: nenhum botão de decisão foi clicado", all(c["metodo"] != "POST" for c in api),
                      chamadas_api=api[:])
            ctx.close()
        else:
            def esperar_em(lista, n):
                pg.wait_for_selector(f"#lista-{lista} #item-{n}", state="attached", timeout=60000)

            def clicar(n, acao):
                pg.locator(f"#item-{n} [data-acao={acao}]").click()

            # garante um ponto de partida conhecido para 901 e 902 (pendentes)
            for n in TESTE:
                if n in ids(pg, "aprovadas") or n in ids(pg, "ajuste"):
                    clicar(n, "desfazer")
                    esperar_em("pendentes", n)
            registrar("901 e 902 em Pendentes", set(TESTE) <= set(ids(pg, "pendentes")) and agendadas(pg) == [],
                      blocos={k: ids(pg, k) for k in ("pendentes", "aprovadas", "ajuste")}, no_ramo=aprovados_no_ramo())

            clicar("901", "aprovar")
            esperar_em("aprovadas", "901")
            no_ramo = aprovados_no_ramo()
            registrar("Aprovar 901 → Aprovadas e Agendadas; 901 no aprovacao.json do ramo",
                      agendadas(pg) == ["901"] and no_ramo == [901] and "Aprovado por Padre" in pg.inner_text("#item-901"),
                      agendadas=agendadas(pg), no_ramo=no_ramo, status=pg.inner_text("#item-901 .item-status"))
            foto(pg, "teste-3-aprovado")

            clicar("902", "ajuste")
            pg.fill("#item-902 textarea", "[TESTE Playwright] Trocar a foto da capa.")
            clicar("902", "salvar")
            esperar_em("ajuste", "902")
            ajuste = json.loads((Path(a.checkout) / "content" / "semanas" / "2099-W01" / "ajuste-902.json").read_text(encoding="utf-8")) \
                if aprovados_no_ramo() is not None else None
            registrar("Pedir ajuste 902 → Em ajuste com o texto; ajuste-902.json no ramo",
                      "Trocar a foto da capa." in pg.inner_text("#item-902 .item-comentario")
                      and ajuste and ajuste["texto"] == "[TESTE Playwright] Trocar a foto da capa." and agendadas(pg) == ["901"],
                      comentario=pg.inner_text("#item-902 .item-comentario"), ajuste=ajuste)
            foto(pg, "teste-4-ajuste")

            pg.reload()
            pg.wait_for_load_state("networkidle")
            abrir_blocos(pg)
            registrar("recarregar a página mantém as decisões (vêm do D1)",
                      "901" in ids(pg, "aprovadas") and "902" in ids(pg, "ajuste") and agendadas(pg) == ["901"],
                      blocos={k: ids(pg, k) for k in ("pendentes", "aprovadas", "ajuste")}, agendadas=agendadas(pg))

            clicar("901", "desfazer")
            esperar_em("pendentes", "901")
            no_ramo = aprovados_no_ramo()
            registrar("Desfazer 901 → volta a Pendentes, sai de Agendadas e do aprovacao.json",
                      agendadas(pg) == [] and no_ramo == [], agendadas=agendadas(pg), no_ramo=no_ramo)

            clicar("902", "desfazer")
            esperar_em("pendentes", "902")
            registrar("Desfazer 902 (ajuste) → volta a Pendentes", set(TESTE) <= set(ids(pg, "pendentes")),
                      blocos={k: ids(pg, k) for k in ("pendentes", "aprovadas", "ajuste")})
            foto(pg, "teste-5-desfeito")
            posts = [c for c in api if c["metodo"] == "POST"]
            registrar("todas as decisões foram POST /api/decisao com o código só no header",
                      posts and all(c["url"].endswith("/api/decisao") and c["auth"] == "Bearer <CODIGO>" for c in posts),
                      decisoes=len(posts))
            ctx.close()
        nav.close()

    resultado = {"modo": a.modo, "pagina": a.pagina, "passos": passos, "ok": all(p["ok"] for p in passos)}
    Path(a.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TUDO OK" if resultado["ok"] else "HOUVE FALHAS", "→", a.saida)
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
