"""Validação da página PUBLICADA no GitHub Pages com Playwright (ADR-012).

--modo teste   página de teste (site/aprovacao-teste/, Worker de TESTE, semana 2099-W01): rascunho não grava
               nada; código errado é recusado; código certo grava (conferido no ramo teste-aprovacao);
               desfazer por rascunho + envio; 5 códigos errados bloqueiam. Depois, no celular (WebKit e
               Chromium — iPhone 13 e Pixel 7, com viewport/isMobile/hasTouch/userAgent reais): botão "Aprovações"
               leva ao painel e o fluxo inteiro (rascunho → Enviar → código → gravação) funciona por toque.
--modo fumaca  página real (site/aprovacao/, Worker de produção), pelo link curto e pela URL direta, no
               computador e no celular: estado carregado sem código, painel alcançável, rascunho e diálogo
               do código funcionam — e NADA é enviado (o diálogo é cancelado; o rascunho é descartado).

O código (só no modo teste) é lido de um arquivo e nunca é impresso. Capturas vão para --capturas.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

MOTORES = [("webkit", "iPhone 13"), ("chromium", "Pixel 7")]


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modo", choices=["teste", "fumaca"], required=True)
    ap.add_argument("--pagina", required=True, help="URL direta da página")
    ap.add_argument("--link-curto", help="link curto que redireciona para a página (modo fumaça)")
    ap.add_argument("--codigo-arquivo", help="arquivo com o código do Worker de TESTE (modo teste)")
    ap.add_argument("--checkout", help="checkout do ramo teste-aprovacao (modo teste)")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--capturas", required=True)
    ap.add_argument("--so-celular", action="store_true", help="pula a parte do computador (já validada)")
    a = ap.parse_args(argv)
    codigo = Path(a.codigo_arquivo).read_text(encoding="utf-8").strip() if a.codigo_arquivo else None
    if a.modo == "teste" and ("teste" not in a.pagina or not codigo or not a.checkout):
        raise SystemExit("modo teste: use a página de teste, --codigo-arquivo e --checkout")
    capt = Path(a.capturas)
    capt.mkdir(parents=True, exist_ok=True)
    passos = []

    def mascarar(t):
        return str(t).replace(codigo, "<CODIGO>") if codigo else str(t)

    def registrar(nome, ok, **ev):
        passos.append(json.loads(mascarar(json.dumps({"passo": nome, "ok": bool(ok), **ev}, ensure_ascii=False))))
        print(("OK   " if ok else "FALHA") + " " + nome, flush=True)

    def git(*args):
        return subprocess.run(["git", "-C", a.checkout, *args], capture_output=True, text=True, encoding="utf-8",
                              check=True, stdin=subprocess.DEVNULL, timeout=120).stdout.strip()

    def no_ramo():
        """(posts no aprovacao.json, texto do ajuste-902.json) no ramo de teste, relidos do GitHub."""
        git("fetch", "-q", "origin", "teste-aprovacao")
        git("reset", "-q", "--hard", "origin/teste-aprovacao")
        pasta = Path(a.checkout) / "content" / "semanas" / "2099-W01"
        aprov = pasta / "aprovacao.json"
        ajuste = pasta / "ajuste-902.json"
        return ([p["numero"] for p in json.loads(aprov.read_text(encoding="utf-8"))["posts"]] if aprov.exists() else None,
                json.loads(ajuste.read_text(encoding="utf-8"))["texto"] if ajuste.exists() else None)

    with sync_playwright() as pw:
        def contexto(motor="chromium", aparelho=None, tamanho=None):
            nav = getattr(pw, motor).launch()
            opcoes = dict(pw.devices[aparelho]) if aparelho else {"viewport": {"width": 1280, "height": 900}}
            if tamanho:
                opcoes["viewport"] = {"width": tamanho[0], "height": tamanho[1]}
                opcoes["screen"] = {"width": tamanho[0], "height": tamanho[1]}
            opcoes["locale"] = "pt-BR"
            ctx = nav.new_context(**opcoes)
            api = []
            erros = []
            pg = ctx.new_page()
            pg.on("request", lambda r: api.append({
                "metodo": r.method, "url": mascarar(r.url),
                "auth": None if not r.headers.get("authorization") else
                ("Bearer <CODIGO>" if codigo and r.headers.get("authorization") == f"Bearer {codigo}" else "Bearer <outro>"),
                "corpo": mascarar(r.post_data) if r.post_data else None}) if "/api/" in r.url else None)
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
            return nav, ctx, pg, api, erros

        def ids(pg, lista):
            return pg.eval_on_selector_all(f"#lista-{lista} > li", "els => els.map(e => e.dataset.n)")

        def agendadas(pg):
            return pg.eval_on_selector_all("#lista-agendadas > li:not([hidden])", "els => els.map(e => e.dataset.n)")

        def abrir_blocos(pg, tocar=False):
            for b in pg.locator(".bloco-botao").all():
                if b.get_attribute("aria-expanded") == "false":
                    b.tap() if tocar else b.click()

        def posts(api):
            return [c for c in api if c["metodo"] == "POST"]

        def enviar_codigo(pg, cod, tocar=False, esperar="#envio-resultado:not([hidden])"):
            (pg.tap if tocar else pg.click)("#enviar")
            pg.fill("#codigo", cod)
            (pg.tap if tocar else pg.click)("#confirmar")
            pg.wait_for_selector(esperar, timeout=90000)

        # ------------------------------------------------------------------ computador
        if not a.so_celular:
            nav, ctx, pg, api, erros = contexto()
            pg.goto(a.pagina)
            pg.wait_for_load_state("networkidle")
            abrir_blocos(pg)
            pend = ids(pg, "pendentes")
            publicadas = pg.eval_on_selector_all("#bloco-publicadas .item-titulo", "els => els.map(e => e.dataset.abrir)")
            texto = pg.inner_text("#painel")
            registrar("abre sem código: estado pelo GET público, publicados fora de Pendentes, sem menção a padre",
                      api and api[0]["url"].endswith("/api/estado") and api[0]["auth"] is None and not posts(api)
                      and not {"1", "2", "3"} & set(pend) and publicadas == ["1", "2", "3"]
                      and "padre" not in pg.content().lower() and "nada disso foi publicado" not in texto
                      and pg.is_disabled("#enviar") and not erros,
                      pendentes=pend, publicadas=publicadas, aprovadas=ids(pg, "aprovadas"), agendadas=agendadas(pg),
                      acesso=pg.inner_text("#acesso"), erros=erros)

            if a.modo == "teste":
                antes = no_ramo()
                pg.click("#item-901 .btn-aprovar")
                pg.click("#item-902 [data-acao=ajuste]")
                pg.fill("#item-902 textarea", "[TESTE Playwright] Trocar a foto da capa.")
                pg.click("#item-902 [data-acao=salvar]")
                rasc = json.loads(pg.evaluate("localStorage.getItem('pastoral-painel-rascunho-v1')"))
                depois = no_ramo()
                registrar("rascunho: 901 em Aprovadas e 902 em Em ajuste como 'a enviar'; nada chegou ao servidor",
                          not posts(api) and depois == antes and "901" in ids(pg, "aprovadas") and "902" in ids(pg, "ajuste")
                          and "A enviar" in pg.inner_text("#item-901 .item-status") and agendadas(pg) == []
                          and sorted(rasc) == ["901", "902"],
                          rascunho={k: v["acao"] for k, v in rasc.items()}, ramo_antes=antes, ramo_depois=depois,
                          resumo=pg.inner_text("#envio-resumo"))

                pg.reload()
                pg.wait_for_load_state("networkidle")
                abrir_blocos(pg)
                registrar("recarregar mantém o rascunho", "901" in ids(pg, "aprovadas") and "902" in ids(pg, "ajuste")
                          and pg.inner_text("#envio-resumo") == "2 respostas a enviar.", resumo=pg.inner_text("#envio-resumo"))

                enviar_codigo(pg, codigo.swapcase(), esperar="#dialogo-aviso:has-text('Código errado')")
                registrar("Enviar com o código errado (maiúsculas trocadas) → recusado; nada gravado; rascunho mantido",
                          no_ramo() == antes and pg.inner_text("#envio-resumo") == "2 respostas a enviar."
                          and posts(api)[-1]["auth"] == "Bearer <outro>",
                          aviso=pg.inner_text("#dialogo-aviso"), ramo=no_ramo())
                pg.click("#cancelar-envio")

                enviar_codigo(pg, codigo)
                ramo = no_ramo()
                registrar("Enviar com o código certo → 901 aprovado (aprovacao.json no ramo) e 902 com ajuste-902.json",
                          ramo == ([901], "[TESTE Playwright] Trocar a foto da capa.") and agendadas(pg) == ["901"]
                          and "Aprovado por Aprovador" in pg.inner_text("#item-901 .item-status")
                          and pg.inner_text("#envio-resumo") == "Nenhuma resposta a enviar."
                          and all(c["auth"] == "Bearer <CODIGO>" and "<CODIGO>" not in c["url"] for c in posts(api)[-2:]),
                          resultado=pg.inner_text("#envio-resultado"), ramo=ramo, agendadas=agendadas(pg))

                pg.click("#item-901 [data-acao=desfazer]")
                pg.click("#item-902 [data-acao=desfazer]")
                registrar("Desfazer vira rascunho: 901 e 902 em Pendentes 'a enviar'; Agendadas continua com 901 (servidor)",
                          set(["901", "902"]) <= set(ids(pg, "pendentes")) and agendadas(pg) == ["901"] and no_ramo()[0] == [901],
                          status_901=pg.inner_text("#item-901 .item-status"))
                enviar_codigo(pg, codigo)
                ramo = no_ramo()
                registrar("Enviar o desfazer → 901 sai do aprovacao.json; Agendadas vazia", ramo[0] == [] and agendadas(pg) == [],
                          resultado=pg.inner_text("#envio-resultado"), ramo=ramo)

                pg.click("#item-901 .btn-aprovar")
                for i in range(5):
                    pg.click("#enviar") if not pg.is_visible("#dialogo-codigo") else None
                    pg.fill("#codigo", f"errado{i}")
                    pg.click("#confirmar")
                    pg.wait_for_selector("#confirmar:not([disabled])")
                    pg.wait_for_timeout(300)
                aviso = pg.inner_text("#dialogo-aviso")
                pg.fill("#codigo", codigo)
                pg.click("#confirmar")
                pg.wait_for_selector("#confirmar:not([disabled])")
                pg.wait_for_timeout(300)
                aviso2 = pg.inner_text("#dialogo-aviso")
                registrar("5 códigos errados → bloqueio de 15 min com mensagem clara; nem o código certo passa; nada gravado",
                          "bloqueado" in aviso and "Tente de novo depois" in aviso2 and no_ramo()[0] == [],
                          aviso_5=aviso, aviso_codigo_certo=aviso2)
                pg.click("#cancelar-envio")
                pg.click("#item-901 [data-acao=desfazer]")            # rascunho de aprovação: Desfazer o descarta
            ctx.close()
            nav.close()

        # ------------------------------------------------------------------ celular
        if a.modo == "teste" and not a.so_celular:
            # o bloqueio de propósito acima também valeria para o celular (mesmo IP): limpa as falhas no D1 de TESTE
            env = {k: v for k, v in os.environ.items() if k not in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")}
            env.update(XDG_CONFIG_HOME="C:/Users/odnac/.config-pastoral-dizimo", CI="1")
            r = subprocess.run(["npx", "wrangler", "d1", "execute", "pastoral-aprovacoes-teste", "--remote", "--env", "teste",
                                "--command", "DELETE FROM falhas_acesso"], cwd=Path(__file__).resolve().parents[1] / "worker",
                               capture_output=True, text=True, encoding="utf-8", env=env, shell=(os.name == "nt"),
                               stdin=subprocess.DEVNULL, timeout=180)
            registrar("falhas do teste apagadas no D1 de teste (libera o IP)", r.returncode == 0)
        for motor, aparelho in MOTORES:
            for tam in [None]:                                   # viewport real do aparelho
                rotulo = f"{motor}-{aparelho.replace(' ', '')}"
                nav, ctx, pg, api, erros = contexto(motor, aparelho, tam)
                entrada = a.link_curto if (a.modo == "fumaca" and a.link_curto and motor == "webkit") else a.pagina
                resp = pg.goto(entrada)
                pg.wait_for_load_state("networkidle")
                ua = pg.evaluate("navigator.userAgent")
                movel = pg.evaluate("matchMedia('(pointer: coarse)').matches")
                fora = pg.evaluate("document.getElementById('painel').getBoundingClientRect().top > innerHeight")
                visivel = pg.is_visible("#ir-painel")
                if visivel:                     # página longa: o botão fixo leva ao painel e abre Pendentes
                    pg.tap("#ir-painel")
                    pg.wait_for_timeout(400)
                    topo = pg.evaluate("Math.round(document.getElementById('painel').getBoundingClientRect().top)")
                    alcancavel = fora and abs(topo) <= 2
                else:                           # página curta (teste): o painel já está na tela e o botão some
                    topo = None
                    alcancavel = not fora
                    pg.locator("#bloco-pendentes .bloco-botao").tap()
                n = "901" if a.modo == "teste" else pg.eval_on_selector_all("#lista-pendentes > li", "e => e.map(x => x.dataset.n)")[0]
                pg.tap(f"#item-{n} .btn-aprovar")
                pg.locator("#enviar").scroll_into_view_if_needed()
                enviar_visivel = pg.is_visible("#enviar") and pg.is_enabled("#enviar")
                pg.tap("#enviar")
                pg.wait_for_selector("#dialogo-codigo[open]")
                pg.tap("#codigo")
                if a.modo == "teste":
                    pg.fill("#codigo", codigo)
                    pg.tap("#confirmar")
                    pg.wait_for_selector("#envio-resultado:not([hidden])", timeout=90000)
                    gravado = no_ramo()[0] == [901] and agendadas(pg) == ["901"]
                    pg.screenshot(path=str(capt / f"{a.modo}-{rotulo}.png"))       # 1 captura por cenário
                    if pg.get_attribute("#bloco-aprovadas .bloco-botao", "aria-expanded") == "false":
                        pg.locator("#bloco-aprovadas .bloco-botao").tap()
                    pg.tap("#item-901 [data-acao=desfazer]")          # volta ao ponto de partida (desfazer + enviar)
                    enviar_codigo(pg, codigo, tocar=True)
                    desfeito = no_ramo()[0] == []
                else:
                    pg.screenshot(path=str(capt / f"{a.modo}-{rotulo}.png"))       # 1 captura por cenário
                    pg.tap("#cancelar-envio")
                    if pg.get_attribute("#bloco-aprovadas .bloco-botao", "aria-expanded") == "false":
                        pg.locator("#bloco-aprovadas .bloco-botao").tap()
                    pg.tap(f"#item-{n} [data-acao=desfazer]")          # descarta o rascunho: nada foi enviado
                    gravado = desfeito = not posts(api)
                registrar(f"celular {motor} {aparelho} ({pg.viewport_size['width']}×{pg.viewport_size['height']}): painel alcançável pelo botão e fluxo por toque"
                          + (" com gravação" if a.modo == "teste" else " sem enviar nada"),
                          alcancavel and enviar_visivel and gravado and desfeito and not erros,
                          entrada="link curto" if entrada != a.pagina else "URL direta", status=resp.status if resp else None,
                          url_final=pg.url, ua=ua[:70], ponteiro_grosso=movel, painel_fora_da_tela_no_inicio=fora,
                          botao_visivel=visivel, topo_do_painel_apos_toque=topo, enviar_alcancavel=enviar_visivel,
                          gravado=gravado, desfeito=desfeito, posts_enviados=len(posts(api)), erros=erros)
                ctx.close()
                nav.close()

    resultado = {"modo": a.modo, "pagina": a.pagina, "passos": passos, "ok": all(p["ok"] for p in passos)}
    Path(a.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TUDO OK" if resultado["ok"] else "HOUVE FALHAS", "→", a.saida)
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
