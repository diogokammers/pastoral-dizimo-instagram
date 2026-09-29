"""ADR-013 — exportador das respostas do D1 para o repositório PRIVADO de dados (nunca para este, que é público)."""
import csv
import json
import subprocess

import pytest

from pastoral import formularios

RESPOSTAS_D1 = [
    {"id": "b", "criado_em": "2026-10-02T10:00:00.000Z", "tipo": "fiel", "versao_form": 1,
     "dados": json.dumps({"paroquia": "", "assunto": "Sugestão", "mensagem": "=HYPERLINK(\"x\")", "nome": "", "contato": ""})},
    {"id": "a", "criado_em": "2026-10-01T10:00:00.000Z", "tipo": "agente", "versao_form": 1,
     "dados": json.dumps({"paroquia": "Tijucas - São Sebastião", "funcao": "Coordenador(a)",
                          "pedido": "Pedido de material", "temas": ["Linguagem sobre o dízimo", "Outro"],
                          "descricao": "Linha 1\nLinha 2", "nome": "Ana", "contato": "ana@exemplo.test"},
                         ensure_ascii=False)},
]


def saida_wrangler(sql):
    """Imita `wrangler d1 execute --json`: lista com um bloco de resultados."""
    assert sql.startswith("SELECT")
    return [{"results": RESPOSTAS_D1, "success": True, "meta": {}}]


def repo_git(pasta):
    subprocess.run(["git", "init", "-q", str(pasta)], check=True)
    for chave, valor in (("user.name", "Teste"), ("user.email", "teste@exemplo.test")):
        subprocess.run(["git", "-C", str(pasta), "config", chave, valor], check=True)
    return pasta


def test_buscar_ordena_e_abre_os_dados():
    r = formularios.buscar_respostas(saida_wrangler)
    assert [x["id"] for x in r] == ["a", "b"]
    assert r[0]["dados"]["temas"] == ["Linguagem sobre o dízimo", "Outro"]


def test_escrever_jsonl_e_csv(tmp_path):
    formularios.escrever(formularios.buscar_respostas(saida_wrangler), tmp_path)
    linhas = (tmp_path / "respostas.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["id"] for l in linhas] == ["a", "b"]
    assert json.loads(linhas[0])["dados"]["nome"] == "Ana"

    bruto = (tmp_path / "respostas.csv").read_bytes()
    assert bruto.startswith(b"\xef\xbb\xbf")  # BOM: o Excel abre com acentos certos
    with open(tmp_path / "respostas.csv", encoding="utf-8-sig", newline="") as f:
        tabela = list(csv.DictReader(f))
    assert list(tabela[0].keys()) == formularios.COLUNAS
    assert tabela[0]["temas"] == "Linguagem sobre o dízimo | Outro"
    assert tabela[0]["descricao"] == "Linha 1\nLinha 2"
    assert tabela[1]["funcao"] == ""
    # texto que começa com "=" não vira fórmula na planilha
    assert tabela[1]["mensagem"] == "'=HYPERLINK(\"x\")"


def test_sem_respostas_gera_arquivos_validos(tmp_path):
    formularios.escrever([], tmp_path)
    assert (tmp_path / "respostas.jsonl").read_text(encoding="utf-8") == ""
    with open(tmp_path / "respostas.csv", encoding="utf-8-sig", newline="") as f:
        assert next(csv.reader(f)) == formularios.COLUNAS


def test_recusa_pasta_dentro_do_repositorio_publico(tmp_path):
    assert formularios.dentro_do_repo(formularios.RAIZ / "content")
    assert formularios.dentro_do_repo(formularios.RAIZ)
    assert not formularios.dentro_do_repo(tmp_path)
    with pytest.raises(SystemExit, match="público"):
        formularios.exportar(formularios.RAIZ / "dados", saida_wrangler)


def test_recusa_pasta_que_nao_e_repositorio_git(tmp_path):
    with pytest.raises(SystemExit, match="git"):
        formularios.exportar(tmp_path, saida_wrangler)


def test_exportar_faz_commit_sem_push(tmp_path):
    repo = repo_git(tmp_path / "dados")
    empurrou = []
    n = formularios.exportar(repo, saida_wrangler, push=False, empurrar=lambda p: empurrou.append(p))
    assert n == 2
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True).stdout
    assert "2 resposta(s)" in log
    assert empurrou == []
    # de novo sem mudança: não cria commit vazio
    formularios.exportar(repo, saida_wrangler)
    log2 = subprocess.run(["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True).stdout
    assert log2 == log


def test_exportar_com_push(tmp_path):
    repo = repo_git(tmp_path / "dados")
    empurrou = []
    formularios.exportar(repo, saida_wrangler, push=True, empurrar=lambda p: empurrou.append(p))
    assert empurrou == [repo]


def test_gitignore_do_publico_bloqueia_respostas():
    texto = (formularios.RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "respostas*.jsonl" in texto and "respostas*.csv" in texto
