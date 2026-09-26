"""Configuração comum dos testes: caminho da raiz do repositório."""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def raiz() -> Path:
    return RAIZ
