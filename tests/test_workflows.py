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
