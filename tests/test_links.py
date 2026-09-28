"""ADR-013 — página de links da bio e formulários de escuta: dados (paróquias e campos) e página gerada."""
import re
from pathlib import Path

import yaml

from pastoral import lint

RAIZ = Path(__file__).resolve().parent.parent
PAROQUIAS = RAIZ / "content" / "paroquias.yaml"
FORMULARIOS = RAIZ / "content" / "formularios.yaml"

# Spec 3.3: temas tirados do Doc. CNBB 106, Cap. II (fichamento docs/pesquisa/07)
TEMAS_SPEC = [
    "Sentido do dízimo e motivação da comunidade",
    "Implantação ou retomada do dízimo na paróquia",
    "Organização e funcionamento da equipe",
    "Formação dos agentes: espiritual, humana e técnico-organizativa",
    "Acolhida e visitas missionárias",
    "Cadastro e comunicação com os fiéis",
    "Registro, recibo e aspectos legais",
    "Prestação de contas e transparência",
    "Relação com os Conselhos Econômico e Pastoral",
    "Participação do clero",
    "Dízimo na catequese e na preparação dos noivos",
    "Linguagem sobre o dízimo",
    "Outro",
]


def ler(caminho):
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def textos(no):
    """Todas as strings de um YAML (recursivo)."""
    if isinstance(no, str):
        yield no
    elif isinstance(no, dict):
        for v in no.values():
            yield from textos(v)
    elif isinstance(no, list):
        for v in no:
            yield from textos(v)


def problemas_de_texto(texto):
    erros = [rotulo for rotulo, padrao in lint.TERMOS_PROIBIDOS if re.search(padrao, texto, re.IGNORECASE)]
    if "%" in texto:
        erros.append("%")
    for palavra in ("voluntári", "dizimista"):
        if palavra in texto.lower():
            erros.append(palavra)
    return erros


# ---------- dados ----------

def test_paroquias_da_fonte_oficial():
    dados = ler(PAROQUIAS)
    assert dados["fonte"] == "https://arquifln.org.br/paroquias"
    assert dados["consultado_em"] == "2026-09-28"
    lista = dados["paroquias"]
    assert len(lista) == 82
    assert len(set(lista)) == len(lista)
    for item in lista:
        assert re.fullmatch(r"[^()]+? - [^()]+( \([^()]+\))?", item), item


def test_formularios_coerentes():
    f = ler(FORMULARIOS)
    assert f["versao"] == 1
    assert f["agente"]["temas"] == TEMAS_SPEC
    assert set(f["agente"]["pedidos_com_contato"]) <= set(f["agente"]["pedidos"])
    assert f["agente"]["pedidos_com_contato"] == ["Pedido de capacitação", "Pedido de material"]
    assert f["limites"] == {"texto_curto": 120, "texto_longo": 2000}
    assert "pastoraldodizimo.arquifln@gmail.com" in f["consentimento"]


def test_textos_dos_formularios_seguem_o_cartao():
    for texto in textos(ler(FORMULARIOS)):
        assert problemas_de_texto(texto) == [], texto
