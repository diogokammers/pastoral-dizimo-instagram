"""Validação ponta a ponta do painel (ADR-011) contra o Worker de TESTE, o D1 de teste e o ramo teste-aprovacao.

Nunca aponte para produção: o script recusa o Worker de produção e ramos diferentes de teste-aprovacao.
Chamadas HTTP reais; depois de cada passo relê o ramo (git pull num checkout dele) e roda o portão
(publicar.avaliar_semana) localmente com o segredo de TESTE. Consulta o D1 de teste pelo wrangler.
O código de acesso e os segredos são lidos de arquivos e nunca aparecem na saída (o código é mascarado).

Uso (PYTHONPATH=src, da raiz do repositório):
  python scripts/e2e_painel.py --api https://pastoral-dizimo-aprovacao-teste.<sub>.workers.dev \\
      --checkout <checkout do ramo teste-aprovacao> --codigo-arquivo <arq> --segredo-arquivo <arq> \\
      --saida <evidencias.json fora do repositório>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pastoral import aprovacao, publicar

ORIGEM = "https://diogokammers.github.io"
SEMANA = "2099-W01"
RAMO = "teste-aprovacao"
BANCO = "pastoral-aprovacoes-teste"
DEPOIS_DA_DATA = datetime(2099, 2, 1, tzinfo=timezone.utc)
WORKER = Path(__file__).resolve().parents[1] / "worker"


class E2E:
    def __init__(self, api, checkout, codigo, segredo):
        if "teste" not in api:
            raise SystemExit("recusado: use só o Worker de TESTE")
        self.api, self.checkout, self.codigo, self.segredo = api.rstrip("/"), Path(checkout), codigo, segredo
        ramo = self.git("rev-parse", "--abbrev-ref", "HEAD")
        if ramo != RAMO:
            raise SystemExit(f"recusado: o checkout está no ramo {ramo!r}, não {RAMO}")
        self.passos = []

    # ---------- utilitários ----------
    def mascarar(self, texto):
        return str(texto).replace(self.codigo, "<CODIGO>")

    def git(self, *args):
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        return subprocess.run(["git", "-C", str(self.checkout), *args], capture_output=True, text=True, encoding="utf-8",
                              check=True, stdin=subprocess.DEVNULL, timeout=120, env=env).stdout.strip()

    def atualizar(self):
        """Traz o ramo e devolve o último commit que mexeu na SEMANA (decisões). Os commits de backup
        (content/aprovacoes/eventos.jsonl) chegam depois, em segundo plano, e não contam aqui."""
        self.git("fetch", "-q", "origin", RAMO)
        self.git("reset", "-q", "--hard", f"origin/{RAMO}")
        return self.git("log", "-1", "--format=%H", "--", f"content/semanas/{SEMANA}")

    def empurrar(self):
        for _ in range(5):              # o backup do Worker pode commitar no meio: rebase e tenta de novo
            try:
                self.git("pull", "-q", "--rebase", "origin", RAMO)
                # push sem janela do gerenciador de credenciais: usa o login do gh (o token não aparece)
                self.git("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                         "push", "-q", "origin", f"HEAD:{RAMO}")
                return
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                time.sleep(3)
        raise SystemExit("não consegui enviar o commit de teste ao ramo")

    def http(self, metodo, caminho, corpo=None, codigo="certo", origem=ORIGEM, redirecionar=True):
        headers = {"User-Agent": "pastoral-e2e-painel"}
        if origem:
            headers["Origin"] = origem
        if codigo:
            headers["Authorization"] = f"Bearer {self.codigo if codigo == 'certo' else codigo}"
        dados = None
        if corpo is not None:
            dados = json.dumps(corpo).encode("utf-8")
            headers["Content-Type"] = "application/json"
        pedido = urllib.request.Request(self.api + caminho, data=dados, method=metodo, headers=headers)
        abridor = urllib.request.build_opener() if redirecionar else urllib.request.build_opener(SemRedirecionar)
        try:
            with abridor.open(pedido, timeout=60) as r:
                return r.status, dict(r.headers), r.read().decode("utf-8")
        except urllib.error.HTTPError as erro:
            return erro.code, dict(erro.headers), erro.read().decode("utf-8")

    def d1(self, sql):
        env = {k: v for k, v in os.environ.items() if k not in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")}
        env["XDG_CONFIG_HOME"] = "C:/Users/odnac/.config-pastoral-dizimo"
        env["CI"] = "1"
        r = subprocess.run(["npx", "wrangler", "d1", "execute", BANCO, "--remote", "--env", "teste", "--json",
                            "--command", sql], cwd=WORKER, capture_output=True, text=True, encoding="utf-8",
                           env=env, shell=(os.name == "nt"), stdin=subprocess.DEVNULL, timeout=180)
        if r.returncode != 0:
            return {"erro": (r.stdout + r.stderr)[-400:]}
        return json.loads(r.stdout)[0]["results"]

    def total_eventos(self):
        return self.d1("SELECT COUNT(*) AS n FROM eventos")[0]["n"]

    def versao_atual(self, post):
        pasta = self.checkout / "content" / "semanas" / SEMANA
        agenda = json.loads((pasta / "agenda.json").read_text(encoding="utf-8"))
        lote = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
        midia = self.checkout / "site" / "midia" / SEMANA
        agenda["posts"] = [e for e in agenda["posts"] if e["numero"] == post]
        [item] = aprovacao.itens_semana(agenda, lote, lambda a: (midia / a).read_bytes())
        return aprovacao.versao_post(SEMANA, item)

    def aprovacao_json(self):
        caminho = self.checkout / "content" / "semanas" / SEMANA / "aprovacao.json"
        return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None

    def portao(self):
        raiz = self.checkout
        prontos, recusados = publicar.avaliar_semana(raiz, raiz / "site" / "midia", SEMANA, self.segredo,
                                                     DEPOIS_DA_DATA, publicar.numeros_publicados(raiz))
        return {"prontos": [p["numero"] for p in prontos],
                "recusados": [{"numero": r["numero"], "motivo": r["motivo"]} for r in recusados]}

    def registrar(self, nome, ok, **evidencias):
        passo = {"passo": nome, "ok": bool(ok), **evidencias}
        self.passos.append(json.loads(self.mascarar(json.dumps(passo, ensure_ascii=False))))
        print(("OK   " if ok else "FALHA") + " " + nome, flush=True)
        return ok

    def decidir(self, post, acao, versao=None, comentario=None, **kw):
        corpo = {"semana": SEMANA, "post": post, "acao": acao}
        if versao:
            corpo["versao"] = versao
        if comentario is not None:
            corpo["comentario"] = comentario
        status, _, texto = self.http("POST", "/api/decisao", corpo, **kw)
        try:
            return status, json.loads(texto)
        except ValueError:
            return status, {"bruto": texto[:300]}

    # ---------- roteiro ----------
    def rodar(self):
        head0 = self.atualizar()
        self.base = self.git("rev-parse", "HEAD")
        n0 = self.total_eventos()
        v901, v902 = self.versao_atual(901), self.versao_atual(902)
        self.registrar("estado inicial", True, head=head0, eventos_d1=n0, versao_901=v901, versao_902=v902)

        s, h, _ = self.http("OPTIONS", "/api/decisao", codigo=None)
        self.registrar("preflight CORS do origin permitido → 204", s == 204 and h.get("Access-Control-Allow-Origin") == ORIGEM,
                       status=s, allow_origin=h.get("Access-Control-Allow-Origin"))

        s, _, _ = self.http("GET", "/api/estado", codigo="X" * 43)
        s2, b2 = self.decidir(901, "aprovar", v901, codigo="X" * 43)
        s3, b3 = self.decidir(901, "aprovar", v901, codigo=None)
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("código errado ou ausente → 401 sem gravar", s == 401 and s2 == 401 and s3 == 401 and head == head0 and n == n0,
                       status_estado=s, status_decisao=s2, status_sem_codigo=s3, resposta=b2, head=head, eventos_d1=n)

        s, h, _ = self.http("GET", "/api/estado", origem="https://evil.example")
        s2, b2 = self.decidir(901, "aprovar", v901, origem="https://evil.example")
        s3, b3 = self.decidir(901, "aprovar", v901, origem=None)
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("origin errado ou ausente (com código válido) → 403 sem gravar",
                       s == 403 and s2 == 403 and s3 == 403 and "Access-Control-Allow-Origin" not in h and head == head0 and n == n0,
                       status_estado=s, status_decisao=s2, status_sem_origin=s3, resposta=b2, head=head, eventos_d1=n)

        s, h, texto = self.http("GET", "/api/estado")
        corpo = json.loads(texto)
        self.registrar("GET /api/estado com código → 200 (autor Padre)", s == 200 and corpo.get("autor") == "Padre",
                       status=s, autor=corpo.get("autor"), posts=list(corpo.get("posts", {})),
                       allow_origin=h.get("Access-Control-Allow-Origin"), cache=h.get("Cache-Control"))

        s, b = self.decidir(901, "aprovar", v901)
        head1 = self.atualizar()
        aprov = self.aprovacao_json()
        port = self.portao()
        linhas = self.d1("SELECT id, post, semana, acao, versao_conteudo, autor, criado_em, origem, commit_sha, "
                         "ip_hash IS NOT NULL AS tem_ip_hash FROM eventos ORDER BY id DESC LIMIT 1")
        self.registrar("aprovar 901 → evento no D1 + aprovacao.json assinado no ramo + portão aceita",
                       s == 200 and b.get("commit") and head1 != head0 and publicar.assinatura_valida(aprov, self.segredo)
                       and [p["numero"] for p in aprov["posts"]] == [901] and port["prontos"] == [901]
                       and linhas[0]["commit_sha"] == b["commit"] and linhas[0]["versao_conteudo"] == v901,
                       status=s, resposta=b, head=head1, aprovado_por=aprov["aprovado_por"],
                       assinatura_valida=publicar.assinatura_valida(aprov, self.segredo), portao=port, d1=linhas)

        n1 = self.total_eventos()
        s, b = self.decidir(901, "aprovar", v901)
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("aprovar 901 de novo → idempotente (sem commit, sem evento)",
                       s == 200 and b.get("idempotente") is True and head == head1 and n == n1,
                       status=s, resposta=b, head=head, eventos_d1=n)

        s, b = self.decidir(902, "aprovar", "0" * 32)
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("aprovar 902 com versão velha → 409 sem gravar", s == 409 and head == head1 and n == n1,
                       status=s, resposta=b, head=head, eventos_d1=n)

        s, b = self.decidir(902, "aprovar", v902)
        head2 = self.atualizar()
        aprov, port = self.aprovacao_json(), self.portao()
        self.registrar("aprovar 902 → acumula no aprovacao.json; portão aceita 901 e 902",
                       s == 200 and [p["numero"] for p in aprov["posts"]] == [901, 902] and port["prontos"] == [901, 902],
                       status=s, commit=b.get("commit"), head=head2, portao=port)

        s, b = self.decidir(901, "desfazer")
        head3 = self.atualizar()
        aprov, port = self.aprovacao_json(), self.portao()
        self.registrar("desfazer 901 → sai do aprovacao.json (reassinado); portão não o publica",
                       s == 200 and b.get("estado", {}).get("acao") == "desfazer"
                       and [p["numero"] for p in aprov["posts"]] == [902] and publicar.assinatura_valida(aprov, self.segredo)
                       and 901 not in port["prontos"] and port["prontos"] == [902],
                       status=s, commit=b.get("commit"), head=head3, posts_aprovados=[p["numero"] for p in aprov["posts"]],
                       assinatura_valida=publicar.assinatura_valida(aprov, self.segredo), portao=port)

        n3 = self.total_eventos()
        s, b = self.decidir(901, "desfazer")
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("desfazer 901 de novo → idempotente", s == 200 and b.get("idempotente") is True and head == head3 and n == n3,
                       status=s, head=head, eventos_d1=n)

        texto_ajuste = "[TESTE E2E] Trocar a imagem da capa."
        s, b = self.decidir(902, "ajustar", comentario=texto_ajuste)
        head4 = self.atualizar()
        ajuste_arq = self.checkout / "content" / "semanas" / SEMANA / "ajuste-902.json"
        ajuste = json.loads(ajuste_arq.read_text(encoding="utf-8")) if ajuste_arq.exists() else None
        aprov, port = self.aprovacao_json(), self.portao()
        self.registrar("pedir ajuste 902 → ajuste-902.json + repository_dispatch (ajustar_post_teste) + sai da aprovação",
                       s == 200 and ajuste and ajuste["texto"] == texto_ajuste and aprov["posts"] == [] and port["prontos"] == [],
                       status=s, commit=b.get("commit"), head=head4, ajuste=ajuste, posts_aprovados=aprov["posts"], portao=port,
                       nota="o Worker só responde 200 depois do POST /dispatches ter devolvido 204 (senão seria 502)")

        n4 = self.total_eventos()
        s, b = self.decidir(902, "ajustar", comentario=texto_ajuste)
        head, n = self.atualizar(), self.total_eventos()
        self.registrar("mesmo ajuste de novo → idempotente (sem novo arquivo nem dispatch)",
                       s == 200 and b.get("idempotente") is True and head == head4 and n == n4, status=s, head=head, eventos_d1=n)

        # conteúdo muda depois da aprovação
        s, b = self.decidir(901, "aprovar", v901)
        self.atualizar()
        pasta = self.checkout / "content" / "semanas" / SEMANA
        lote = json.loads((pasta / "posts.json").read_text(encoding="utf-8"))
        p901 = next(p for p in lote["posts"] if p["numero"] == 901)
        p901["legenda"] = p901["legenda"] + "\n\n[TESTE E2E] legenda revisada depois da aprovação."
        (pasta / "posts.json").write_text(json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.git("add", "content/semanas/2099-W01/posts.json")
        self.git("commit", "-q", "-m", "teste(painel): muda a legenda do 901 depois da aprovação (E2E)")
        self.empurrar()
        head5 = self.atualizar()
        v901_nova = self.versao_atual(901)
        _, _, texto = self.http("GET", "/api/estado")
        ev901 = json.loads(texto)["posts"]["901"]
        port = self.portao()
        s2, b2 = self.decidir(901, "aprovar", v901)
        self.registrar("conteúdo muda depois da aprovação → versão guardada ≠ atual (página volta a pendente); portão recusa; aprovar com versão velha → 409",
                       s == 200 and ev901["acao"] == "aprovar" and ev901["versao_conteudo"] == v901 and v901_nova != v901
                       and any(r["numero"] == 901 and "legenda" in r["motivo"] for r in port["recusados"]) and s2 == 409,
                       status_aprovar=s, head=head5, versao_aprovada=ev901["versao_conteudo"], versao_atual=v901_nova,
                       portao=port, status_reaprovar_velha=s2, resposta=b2)
        s, b = self.decidir(901, "aprovar", v901_nova)
        self.atualizar()
        port = self.portao()
        self.registrar("aprovar 901 na versão nova → portão aceita de novo", s == 200 and port["prontos"] == [901],
                       status=s, commit=b.get("commit"), portao=port)

        # backup
        time.sleep(8)
        self.atualizar()
        backup = self.checkout / "content" / "aprovacoes" / "eventos.jsonl"
        linhas = backup.read_text(encoding="utf-8").strip().splitlines() if backup.exists() else []
        total = self.total_eventos()
        ids_d1 = [r["id"] for r in self.d1("SELECT id FROM eventos ORDER BY id")]
        ids_bkp = [json.loads(x)["id"] for x in linhas]
        self.registrar("backup: content/aprovacoes/eventos.jsonl no ramo = todos os eventos do D1 (sem ip_hash)",
                       ids_bkp == ids_d1 and all("ip_hash" not in json.loads(x) for x in linhas),
                       eventos_d1=total, linhas_backup=len(linhas), ids=ids_d1)

        # append-only no D1 de verdade
        upd = self.d1("UPDATE eventos SET autor = 'x' WHERE id = 1")
        dele = self.d1("DELETE FROM eventos WHERE id = 1")
        self.registrar("D1 recusa UPDATE e DELETE (append-only)",
                       "append-only" in json.dumps(upd) and "append-only" in json.dumps(dele) and self.total_eventos() == total,
                       update=str(upd)[:200], delete=str(dele)[:200])

        s, h, _ = self.http("GET", f"/p/{self.codigo}", codigo=None, origem=None, redirecionar=False)
        destino = h.get("Location", "")
        self.registrar("link curto /p/<código> → 302 para a página de teste com o código só no fragmento",
                       s == 302 and destino.startswith("https://diogokammers.github.io/") and f"#c={self.codigo}" in destino
                       and "?" not in destino, status=s, location=self.mascarar(destino),
                       referrer=h.get("Referrer-Policy"), cache=h.get("Cache-Control"))

        todos = self.d1("SELECT id, post, semana, acao, comentario, versao_conteudo, autor, criado_em, origem, commit_sha "
                        "FROM eventos ORDER BY id")
        self.atualizar()
        historico = self.git("log", "--format=%H %s", f"{self.base}..HEAD").splitlines()
        return {"api": self.api, "ramo": RAMO, "semana": SEMANA, "passos": self.passos, "eventos_d1": todos,
                "commits_no_ramo": historico,
                "ok": all(p["ok"] for p in self.passos)}


class SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--api", required=True)
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--codigo-arquivo", required=True)
    ap.add_argument("--segredo-arquivo", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args(argv)
    e2e = E2E(a.api, a.checkout, Path(a.codigo_arquivo).read_text(encoding="ascii").strip(),
              Path(a.segredo_arquivo).read_text(encoding="ascii").strip())
    resultado = e2e.rodar()
    Path(a.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TUDO OK" if resultado["ok"] else "HOUVE FALHAS", "→", a.saida)
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
