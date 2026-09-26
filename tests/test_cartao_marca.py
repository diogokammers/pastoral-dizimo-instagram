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


def test_cartao_tem_escopo_das_quatro_fontes(cartao):
    """Regra do Diogo (2026-09-27): só Doc. 106, CIC, CDC e Bíblia."""
    assert re.search(r"^##\s.*Escopo de fontes", cartao, re.MULTILINE)
    for fonte in ["Doc. CNBB 106", "Catecismo", "Direito Canônico", "Bíblia"]:
        assert fonte in cartao


def test_cartao_registra_dimensoes_no_doc_106(cartao):
    """Revogada a regra antiga: as dimensões estão no Doc. 106, n. 29–32."""
    assert "n. 29" in cartao and "n. 32" in cartao
    assert "síntese pastoral" not in cartao


def test_cartao_agente_sem_voluntario(cartao):
    """Agente: serviço à comunidade (CIC 910); "voluntário" só aparece como termo vetado."""
    assert "CIC 910" in cartao
    for linha in cartao.splitlines():
        if re.search(r"volunt[áa]ri", linha, re.IGNORECASE):
            assert re.search(r"nunca|proibid|fora", linha, re.IGNORECASE), linha


def test_cartao_oferta_ancorada(cartao):
    assert "n. 51" in cartao and "CIC 1351" in cartao


def test_cartao_cita_doc_106_verificado(cartao):
    assert "n. 6" in cartao and "n. 12" in cartao
    assert "Conselho Permanente" in cartao


def test_cartao_compacto(cartao):
    # meta da arquitetura: ≤ 3k tokens; chars/4 como teto grosseiro
    assert len(cartao) / 4 <= 3000
