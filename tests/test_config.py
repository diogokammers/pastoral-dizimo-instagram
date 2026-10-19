"""Fatia 1 — config.yaml tem as chaves que o pipeline usa."""
import yaml
import pytest


@pytest.fixture
def config(raiz):
    return yaml.safe_load((raiz / "config.yaml").read_text(encoding="utf-8"))


def test_agenda(config):
    """ADR-015: uma publicação por semana, quarta às 18h, em fila por ordem de aprovação."""
    pub = config["publicacao"]
    assert pub["posts_por_semana"] == 1
    assert pub["fuso"] == "America/Sao_Paulo"
    assert pub["dias"] == [{"dia": "quarta", "hora": "18:00"}]
    assert pub["fila"] is True
    # a numeração da série continua: até 2026-W43 eram 2 por semana (posts 4–11), terça e sexta às 19h
    assert config["pauta"]["ritmos_anteriores"] == [
        {"ate": "2026-W43", "posts_por_semana": 2, "dias": [{"dia": "terca", "hora": "19:00"}, {"dia": "sexta", "hora": "19:00"}]}]


def test_marca_sem_simbolo(config):
    assert config["marca"]["simbolo"] is None


def test_paleta_aprovada(config):
    cores = config["marca"]["paleta"]
    assert cores["vermelho"] == "#A3121C"
    assert cores["vermelho_profundo"] == "#7E0F17"
    assert cores["prata"] == "#F3F2EE"
    assert cores["dourado"] == "#B08D3B"


def test_creme_para_posts_comuns_passa_aa(config):
    # ADR-007: fundo creme dos posts comuns; todo texto sobre ele ≥ 4,5:1
    from pastoral.render import contraste
    cores = config["marca"]["paleta"]
    assert cores["creme"] == "#F2E8D5"
    for texto in ["vermelho", "grafite", "cinza"]:
        assert contraste(cores[texto], cores["creme"]) >= 4.5, texto


def test_fontes_aprovadas(config):
    fontes = config["marca"]["fontes"]
    assert fontes["titulo"]["familia"] == "Cormorant Garamond"
    assert fontes["apoio"]["familia"] == "Source Sans 3"


def test_ctas_e_hashtags(config):
    assert "salvar" in config["ctas_permitidos"]
    assert isinstance(config["hashtags_fixas"], list)
    assert len(config["hashtags_fixas"]) <= 8


def test_modelo_e_limites(config):
    assert config["geracao"]["modelo"]
    lim = config["limites"]
    assert lim["legenda_max_caracteres"] == 1500
    assert lim["hashtags_max"] == 8
    assert lim["palavras_por_slide_max"] == 25


def test_ciclo_de_pilares_tem_10(config):
    ciclo = config["pauta"]["ciclo_pilares"]
    assert len(ciclo) == 10
    assert ciclo.count("Formação") == 7
    assert ciclo.count("Vida pastoral") == 2
    assert ciclo.count("Convite institucional") == 1


def test_claude_md_curto(raiz):
    linhas = (raiz / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert len(linhas) <= 40


def test_linguagem_simples(config):
    """ADR-010: frase até 30 palavras na legenda e termos formais proibidos fora de aspas."""
    ling = config["linguagem"]
    assert ling["frase_max_palavras"] == 30
    for termo in ["corresponsavelmente", "outrossim", "destarte", "hodierno", "mister", "sustentação"]:
        assert termo in ling["termos_formais"]
