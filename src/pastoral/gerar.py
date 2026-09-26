"""Geração dos posts da semana por LLM (arquitetura §1.1; ADR-001: `claude -p` no plano Max).

Esqueleto testado com LLM mockado: o CLI desta máquina está sem login (ADR-004). Fluxo:
1. monta um prompt com o cartão de marca, o briefing e o JSON Schema;
2. chama `claude -p --output-format json` uma vez;
3. valida schema + lint; se reprovar, faz UMA regeneração mandando os erros de volta;
4. devolve os dados, os erros restantes (para o aprovador) e o uso de tokens de cada chamada.

Uso (quando houver login): python -m pastoral.gerar content/semanas/2026-W41/briefing.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from pastoral import lint

RAIZ = Path(__file__).resolve().parents[2]


class ErroGeracao(RuntimeError):
    """O CLI falhou ou devolveu algo que não é JSON."""


def montar_prompt(briefing: dict, cartao: str, schema: dict, erros: list[str] | None = None) -> str:
    partes = [
        "Você escreve os posts do Instagram da Pastoral do Dízimo. Siga SOMENTE o cartão de marca abaixo.",
        "Nada é inventado: dado que não está no briefing ou no cartão vira item em `a_conferir`.",
        "Inclua em cada post `autocritica` com nota 0–2 por critério (T1–T8) e revise o que tiver nota < 2.",
        "Responda apenas com um JSON válido segundo o schema, dentro de um bloco ```json.",
        "## Cartão de marca\n" + cartao,
        "## Briefing\n" + json.dumps(briefing, ensure_ascii=False, indent=1),
        "## JSON Schema\n" + json.dumps(schema, ensure_ascii=False),
    ]
    if erros:
        partes.append("## Corrija estes erros do lint da tentativa anterior\n" + "\n".join(f"- {e}" for e in erros))
    return "\n\n".join(partes)


def executar_claude(prompt: str, modelo: str) -> str:
    """Roda o CLI em modo headless e devolve o stdout (envelope JSON)."""
    proc = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--model", modelo, "--max-turns", "1"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=600,
    )
    return proc.stdout


def extrair_json(texto: str) -> dict:
    """Pega o JSON de um bloco ```json ou do primeiro '{' ao último '}'."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.DOTALL)
    bruto = m.group(1) if m else texto[texto.find("{"): texto.rfind("}") + 1]
    try:
        return json.loads(bruto)
    except ValueError as erro:
        raise ErroGeracao(f"resposta sem JSON válido: {erro}") from erro


def gerar(briefing: dict, cartao: str, caminho_schema: Path, config: dict,
          executar: Callable[[str, str], str] = executar_claude, max_tentativas: int = 2) -> dict:
    """Gera, valida e (se preciso) regenera uma vez. Nunca publica nada."""
    schema = json.loads(Path(caminho_schema).read_text(encoding="utf-8"))
    modelo = config["geracao"]["modelo"]
    erros: list[str] = []
    uso: list[dict] = []
    dados: dict = {}
    for tentativa in range(1, max_tentativas + 1):
        try:
            envelope = json.loads(executar(montar_prompt(briefing, cartao, schema, erros or None), modelo))
        except ValueError as erro:
            raise ErroGeracao(f"stdout do CLI não é JSON: {erro}") from erro
        if envelope.get("is_error"):
            raise ErroGeracao(str(envelope.get("result", "erro sem mensagem")))
        uso.append({**(envelope.get("usage") or {}), "custo_usd": envelope.get("total_cost_usd")})
        dados = extrair_json(envelope.get("result", ""))
        erros = lint.validar_schema(dados, caminho_schema) or lint.verificar_lote(dados, config)
        if not erros:
            break
    return {"dados": dados, "erros": erros, "tentativas": tentativa, "uso": uso}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gera posts.json a partir do briefing (claude -p)")
    ap.add_argument("briefing", type=Path)
    ap.add_argument("--saida", type=Path, help="padrão: posts.json ao lado do briefing")
    args = ap.parse_args(argv)

    config = lint.carregar_config(RAIZ / "config.yaml")
    briefing = json.loads(args.briefing.read_text(encoding="utf-8"))
    cartao = (RAIZ / "cartao-marca.md").read_text(encoding="utf-8")
    r = gerar(briefing, cartao, RAIZ / "schemas" / "posts.schema.json", config)
    saida = args.saida or args.briefing.with_name("posts.json")
    saida.write_text(json.dumps(r["dados"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for e in r["erros"]:
        print(e)
    print(f"{saida} — {r['tentativas']} tentativa(s), {len(r['erros'])} erro(s) restante(s)")
    return 1 if r["erros"] else 0


if __name__ == "__main__":
    sys.exit(main())
