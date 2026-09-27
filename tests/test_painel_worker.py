"""ADR-011 — o aprovacao.json que a API do painel (Worker) grava é aceito pelo portão; o desfazer tira o post.

Roda worker/scripts/vetor-painel.mjs (Worker de verdade, GitHub falso, D1 falso sobre node:sqlite com as
migrations reais): aprova 12 e 13 da semana de exemplo e depois desfaz 12.
"""
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pastoral import publicar

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "semana-exemplo"
SEMANA = "2026-W41"
SEGREDO_APROV = "segredo-aprovacao-de-teste"


@pytest.fixture(scope="module")
def vetor(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node indisponível")
    saida = tmp_path_factory.mktemp("painel") / "vetor.json"
    proc = subprocess.run([node, "--disable-warning=ExperimentalWarning", str(RAIZ / "worker" / "scripts" / "vetor-painel.mjs"),
                           str(saida)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(saida.read_text(encoding="utf-8"))


def avaliar(tmp_path, aprov):
    raiz = tmp_path / "repo"
    shutil.copytree(FIXTURE, raiz)
    (raiz / "content" / "semanas" / SEMANA / "aprovacao.json").write_text(
        json.dumps(aprov, ensure_ascii=False), encoding="utf-8")
    agora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    return publicar.avaliar_semana(raiz, raiz / "site" / "midia", SEMANA, SEGREDO_APROV, agora, set())


def test_aprovacao_do_painel_passa_no_portao(vetor, tmp_path):
    aprov = vetor["apos_aprovar"]
    assert aprov["aprovado_por"] == "Aprovador"
    assert publicar.assinatura_valida(aprov, SEGREDO_APROV)
    prontos, recusados = avaliar(tmp_path, aprov)
    assert recusados == [] and [p["numero"] for p in prontos] == [12, 13]


def test_desfazer_no_painel_tira_o_post_do_portao(vetor, tmp_path):
    aprov = vetor["apos_desfazer"]
    assert publicar.assinatura_valida(aprov, SEGREDO_APROV)
    assert [p["numero"] for p in aprov["posts"]] == [13]
    prontos, recusados = avaliar(tmp_path, aprov)
    assert [p["numero"] for p in prontos] == [13] and recusados == []
