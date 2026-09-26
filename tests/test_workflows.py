"""Fatia 7 — workflows de publicação e de token têm as travas combinadas (ADR-008)."""
import yaml


def carregar(raiz, nome):
    return yaml.safe_load((raiz / ".github" / "workflows" / nome).read_text(encoding="utf-8"))


def test_publicar_yml(raiz):
    wf = carregar(raiz, "publicar.yml")
    gatilhos = wf[True]                   # PyYAML lê a chave "on" como True
    assert "schedule" in gatilhos and "workflow_dispatch" in gatilhos
    assert wf["concurrency"]["group"] == "publicar"
    passo = next(p for p in wf["jobs"]["portao"]["steps"] if p.get("name") == "Portão de publicação")
    assert passo["run"] == "python -m pastoral.publicar"
    assert "vars.PUBLICAR_ATIVO == '1'" in passo["env"]["PUBLICAR"]
    assert passo["env"]["APROVACAO_HMAC_SECRET"] == "${{ secrets.APROVACAO_HMAC_SECRET }}"
    assert passo["env"]["IG_ACCESS_TOKEN"] == "${{ secrets.IG_ACCESS_TOKEN }}"


def test_token_yml(raiz):
    wf = carregar(raiz, "token.yml")
    assert "schedule" in wf[True]
    passos = wf["jobs"]["renovar"]["steps"]
    texto = "\n".join(str(p.get("run", "")) for p in passos)
    assert "python -m pastoral.meta --renovar --saida" in texto
    assert "GH_PAT_SECRETS" in str(passos)
    assert "::warning::" in texto        # sem PAT, só alerta


def test_semanal_yml(raiz):
    """Fatia 5 (ADR-009): cron de segunda + manual, desligado até SEMANAL_ATIVO = 1."""
    wf = carregar(raiz, "semanal.yml")
    gatilhos = wf[True]
    assert gatilhos["schedule"] == [{"cron": "0 9 * * 1"}] and "workflow_dispatch" in gatilhos
    assert wf["concurrency"]["group"] == "semanal"
    job = wf["jobs"]["semana"]
    assert job["if"] == "vars.SEMANAL_ATIVO == '1'"
    passos = job["steps"]
    nomes = [p.get("name") for p in passos]
    ordem = ["Pauta", "Gerar", "Lint", "Render", "Prévia", "Commit e push", "Notificar"]
    assert [n for n in nomes if n in ordem] == ordem
    texto = "\n".join(str(p.get("run", "")) for p in passos)
    assert "CLAUDE_CODE_OAUTH_TOKEN" in str(passos) and "::error::" in texto
    notificar = next(p for p in passos if p.get("name") == "Notificar")
    assert notificar["env"]["RESEND_API_KEY"] == "${{ secrets.RESEND_API_KEY }}"
    assert notificar["env"]["LINK_HMAC_SECRET"] == "${{ secrets.LINK_HMAC_SECRET }}"
    commit = next(p for p in passos if p.get("name") == "Commit e push")
    assert "git add content/semanas site/semanas site/midia" in commit["run"]
    assert "gh workflow run pages.yml" in commit["run"]     # push do GITHUB_TOKEN não dispara o pages.yml
    assert wf["permissions"]["contents"] == "write" and wf["permissions"]["actions"] == "write"
    desligado = wf["jobs"]["desligado"]
    assert desligado["if"] == "vars.SEMANAL_ATIVO != '1'"


def test_gerar_reserva_yml(raiz):
    """Reserva (gordura): só manual; gera, renderiza e faz a prévia, mas NÃO notifica nem publica."""
    wf = carregar(raiz, "gerar-reserva.yml")
    gatilhos = wf[True]
    assert list(gatilhos) == ["workflow_dispatch"]
    assert gatilhos["workflow_dispatch"]["inputs"]["semanas"]["default"] == "2026-W40 2026-W41"
    assert wf["permissions"]["contents"] == "write" and wf["permissions"]["actions"] == "write"
    texto_wf = (raiz / ".github" / "workflows" / "gerar-reserva.yml").read_text(encoding="utf-8")
    passos = wf["jobs"]["reserva"]["steps"]
    texto = "\n".join(str(p.get("run", "")) for p in passos)
    for proibido in ("pastoral.notificar", "pastoral.publicar", "RESEND_API_KEY", "IG_ACCESS_TOKEN"):
        assert proibido not in texto_wf
    ordem = ["python -m pastoral.pauta", "python -m pastoral.gerar", "python -m pastoral.lint",
             "python -m pastoral.render", "python -m pastoral.preview --semana", "git commit", "git push",
             "gh workflow run pages.yml"]
    posicoes = [texto.index(c) for c in ordem]
    assert posicoes == sorted(posicoes)
    assert "npm i -g @anthropic-ai/claude-code" in texto
    assert "playwright install --with-deps chromium" in texto
    assert 'git add "content/semanas/$SEMANA" site/' in texto
    assert "metricas-geracao.json" in texto_wf
    assert "CLAUDE_CODE_OAUTH_TOKEN" in str(passos) and "::error::" in texto
