"""Mede o tamanho do cartão de marca em tokens.

Método preferido (medição real): duas chamadas `claude -p --output-format json`,
uma só com o prompt mínimo e outra com o prompt mínimo + cartão. A diferença do
total de entrada (input + cache criado + cache lido) é o custo do cartão, já sem o
overhead fixo do Claude Code (prompt de sistema e ferramentas).

Se o CLI não estiver disponível ou falhar (ex.: sessão OAuth expirada), cai para a
estimativa chars/4, marcada como hipótese [H].

Uso: python -m pastoral.medir_tokens [caminho-do-cartao] [--modelo haiku]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Callable

PROMPT_MINIMO = "Responda apenas: ok"


def estimar_tokens(texto: str) -> int:
    """Estimativa grosseira: 1 token ≈ 4 caracteres (arredonda para cima)."""
    return math.ceil(len(texto) / 4)


def total_entrada(envelope: dict) -> int | None:
    """Soma os tokens de entrada do JSON do `claude -p`. None se a chamada falhou."""
    if envelope.get("is_error"):
        return None
    u = envelope.get("usage") or {}
    return (u.get("input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
            + u.get("cache_read_input_tokens", 0))


def executar_claude(prompt: str, modelo: str) -> str:
    """Roda o CLI em modo headless e devolve o stdout (JSON)."""
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--model", modelo, "--max-turns", "1"],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    return proc.stdout


def medir(cartao: str, modelo: str,
          executar: Callable[[str, str], str] = executar_claude) -> dict:
    """Devolve {'tokens', 'metodo', 'modelo'} (+ 'motivo' quando cai na estimativa)."""
    try:
        base = json.loads(executar(PROMPT_MINIMO, modelo))
        com_cartao = json.loads(executar(f"{PROMPT_MINIMO}\n\n{cartao}", modelo))
        t_base, t_cartao = total_entrada(base), total_entrada(com_cartao)
        if t_base is not None and t_cartao is not None:
            return {"tokens": t_cartao - t_base, "metodo": "claude -p (medido)", "modelo": modelo}
        motivo = (base if t_base is None else com_cartao).get("result", "erro sem mensagem")
    except (OSError, ValueError, subprocess.SubprocessError) as erro:
        motivo = f"{type(erro).__name__}: {erro}"
    return {"tokens": estimar_tokens(cartao), "metodo": "estimativa chars/4 [H]",
            "modelo": modelo, "motivo": motivo}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cartao", nargs="?", default="cartao-marca.md")
    parser.add_argument("--modelo", default="haiku")
    args = parser.parse_args()
    texto = Path(args.cartao).read_text(encoding="utf-8")
    resultado = medir(texto, args.modelo)
    resultado["caracteres"] = len(texto)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
