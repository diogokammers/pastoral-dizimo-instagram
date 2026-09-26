"""Fatia 1 — o cartão de marca contém as regras destiladas de docs/marca/ e nada proibido."""
import re

import pytest


@pytest.fixture
def cartao(raiz) -> str:
    return (raiz / "cartao-marca.md").read_text(encoding="utf-8")


SECOES = [
    "Propósito",
    "Objetivos",
    "Público",
    "Tom de voz",
    "Termos",
    "Pilares",
    "CTAs permitidos",
    "Citação bíblica",
    "Formato",
]


@pytest.mark.parametrize("secao", SECOES)
def test_cartao_tem_secao(cartao, secao):
    assert re.search(rf"^##\s.*{secao}", cartao, re.MULTILINE | re.IGNORECASE), secao


def test_cartao_tem_cinco_objetivos(cartao):
    for objetivo in ["Evangelização", "Formação", "Comunicação institucional",
                     "Fortalecimento das equipes", "Aproximação dos dizimistas"]:
        assert objetivo in cartao


def test_cartao_rotacao_70_20_10(cartao):
    assert "7 Formação" in cartao and "2 Vida pastoral" in cartao and "1 Convite" in cartao


def test_cartao_regras_de_formato(cartao):
    assert "1.500" in cartao          # legenda
    assert "8 hashtags" in cartao
    assert "25 palavras" in cartao    # por slide
    assert "%" in cartao              # a regra "sem %" precisa ser citada


def test_cartao_termos_proibidos(cartao):
    for termo in ["taxa", "mensalidade", "cobrança", "prosperidade", "retorno"]:
        assert termo in cartao.lower()


def test_cartao_nao_atribui_quatro_dimensoes_ao_doc_106(cartao):
    """As '4 dimensões' não foram verificadas no Doc. 106 (06-cnbb-doc-106.md)."""
    for linha in cartao.splitlines():
        if "dimens" in linha.lower() and "106" in linha:
            assert re.search(r"não|nunca", linha, re.IGNORECASE), linha


def test_cartao_cita_doc_106_verificado(cartao):
    assert "n. 6" in cartao and "n. 12" in cartao
    assert "Conselho Permanente" in cartao


def test_cartao_compacto(cartao):
    # meta da arquitetura: ≤ 3k tokens; chars/4 como teto grosseiro
    assert len(cartao) / 4 <= 3000
