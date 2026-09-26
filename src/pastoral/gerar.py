"""Geração dos posts da semana por LLM (arquitetura §1.1; ADR-001: `claude -p` no plano Max).

Testado com LLM mockado (o CLI desta máquina está sem login); roda de verdade no GitHub Actions com
CLAUDE_CODE_OAUTH_TOKEN (gerar-reserva.yml, semanal.yml). Fluxo:
1. monta um prompt com o cartão de marca, o briefing e o JSON Schema;
2. chama `claude -p --output-format json` (sem ferramentas, 1 turno). O stdout é um objeto
   {"type": "result", "is_error": ..., "result": "<texto>", "usage": {...}, "total_cost_usd": ...,
   "duration_ms": ...}; o JSON dos posts vem no bloco de código json do `result`.
   Se o CLI não reconhecer `geracao.modelo`, tenta de novo com `geracao.alias`;
3. impõe o briefing: `numero` = `indice` global, `fixado` do briefing (creme), `importante` só se marcado;
4. valida schema + lint; se reprovar, regenera (até 2 vezes) mandando os erros de volta;
5. devolve os dados, os erros restantes (para o aprovador) e o uso de tokens de cada chamada.
O main grava posts.json e metricas-geracao.json (tokens, custo, tempo) ao lado do briefing.

Uso: python -m pastoral.gerar content/semanas/2026-W41/briefing.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
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
        "Um post por item do briefing, na mesma ordem, com `numero` = `indice` do briefing e `fixado` "
        "igual ao do briefing.",
        "Limite de palavras: cada slide deve ter NO MÁXIMO 20 palavras somando todos os campos visíveis "
        "(eyebrow, título, texto, referência/fonte). O limite duro do lint é 25; conte as palavras de cada "
        "slide antes de responder e divida em mais slides se preciso.",
        "Cite o Doc. CNBB 106 SEMPRE com o parágrafo, no formato \"Doc. CNBB 106, n. X\" (um número por citação) "
        "ou \"Doc. CNBB 106, Cap. II\"; nunca \"Doc. CNBB 106\" sozinho, em nenhum campo (slides, alt-text, legenda).",
        "Escopo de fontes: afirme SOMENTE o que estiver no Doc. CNBB 106, no Catecismo (\"CIC 910\"), no Código "
        "de Direito Canônico (\"cân. 222 §1\") ou na Bíblia, sempre com o número; nada de datas comemorativas, "
        "santos do dia, \"Mês Missionário\", estatísticas ou promessas de prazo. O agente presta um serviço à "
        "comunidade (CIC 910); nunca escreva \"voluntário\".",
        "Responda apenas com um JSON válido segundo o schema, dentro de um bloco ```json.",
        "## Cartão de marca\n" + cartao,
        "## Briefing\n" + json.dumps(briefing, ensure_ascii=False, indent=1),
        "## JSON Schema\n" + json.dumps(schema, ensure_ascii=False),
    ]
    if erros:
        partes.append("## Corrija estes erros do lint da tentativa anterior\n" + "\n".join(f"- {e}" for e in erros))
    return "\n\n".join(partes)


def executar_claude(prompt: str, modelo: str) -> str:
    """Roda o CLI em modo headless (sem ferramentas, 1 turno) e devolve o stdout (envelope JSON).

    Se o CLI falhar sem imprimir nada, devolve um envelope de erro com o stderr, para a mensagem
    aparecer no log do workflow.
    """
    proc = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--model", modelo, "--max-turns", "1", "--tools", ""],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900,
    )
    if not (proc.stdout or "").strip():
        motivo = (proc.stderr or "").strip() or f"CLI terminou com código {proc.returncode} e sem saída"
        return json.dumps({"type": "result", "is_error": True, "result": motivo})
    return proc.stdout


def ler_envelope(stdout: str) -> dict:
    """Objeto `type: result` do stdout (com --verbose o CLI devolve a lista de mensagens)."""
    try:
        envelope = json.loads(stdout)
    except ValueError as erro:
        raise ErroGeracao(f"stdout do CLI não é JSON: {erro}") from erro
    if isinstance(envelope, list):
        resultados = [m for m in envelope if isinstance(m, dict) and m.get("type") == "result"]
        if not resultados:
            raise ErroGeracao("stdout do CLI sem mensagem `type: result`")
        envelope = resultados[-1]
    return envelope


def erro_de_modelo(mensagem: str) -> bool:
    """O CLI/API recusou o nome do modelo (inexistente ou sem acesso)?"""
    m = mensagem.lower()
    return "model" in m and bool(re.search(r"not.?found|not exist|invalid|unknown|404|issue with the selected", m))


def extrair_json(texto: str) -> dict:
    """Pega o JSON de um bloco ```json ou do primeiro '{' ao último '}'."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.DOTALL)
    bruto = m.group(1) if m else texto[texto.find("{"): texto.rfind("}") + 1]
    try:
        return json.loads(bruto)
    except ValueError as erro:
        raise ErroGeracao(f"resposta sem JSON válido: {erro}") from erro


def aplicar_briefing(dados: dict, briefing: dict) -> dict:
    """Impõe o que o briefing decide: numeração global e fundo (ADR-007: creme salvo fixado/importante).

    Casa por posição (o prompt pede a mesma ordem). Briefing sem `indice` (testes antigos) fica como está.
    """
    alvos = [b for b in briefing.get("posts", []) if "indice" in b]
    for post, alvo in zip(dados.get("posts", []), alvos):
        post["numero"] = alvo["indice"]
        post["fixado"] = bool(alvo.get("fixado"))
        if alvo.get("importante"):
            post["importante"] = True
        else:
            post.pop("importante", None)
    return dados


def gerar(briefing: dict, cartao: str, caminho_schema: Path, config: dict,
          executar: Callable[[str, str], str] | None = None, max_tentativas: int = 3) -> dict:
    """Gera, valida e (se preciso) regenera uma vez. Nunca publica nada."""
    executar = executar or executar_claude
    schema = json.loads(Path(caminho_schema).read_text(encoding="utf-8"))
    modelo = config["geracao"]["modelo"]
    alias = config["geracao"].get("alias")
    erros: list[str] = []
    uso: list[dict] = []
    dados: dict = {}
    for tentativa in range(1, max_tentativas + 1):
        prompt = montar_prompt(briefing, cartao, schema, erros or None)
        envelope = ler_envelope(executar(prompt, modelo))
        if (envelope.get("is_error") and alias and modelo != alias
                and erro_de_modelo(str(envelope.get("result", "")))):
            print(f"modelo {modelo!r} recusado pelo CLI; usando o alias {alias!r}", file=sys.stderr)
            modelo = alias
            envelope = ler_envelope(executar(prompt, modelo))
        if envelope.get("is_error"):
            raise ErroGeracao(str(envelope.get("result", "erro sem mensagem")))
        uso.append({**(envelope.get("usage") or {}), "custo_usd": envelope.get("total_cost_usd"),
                    "duracao_ms": envelope.get("duration_ms"), "modelo": modelo})
        dados = aplicar_briefing(extrair_json(envelope.get("result") or ""), briefing)
        erros = lint.validar_schema(dados, caminho_schema) or lint.verificar_lote(dados, config)
        if not erros:
            break
    return {"dados": dados, "erros": erros, "tentativas": tentativa, "uso": uso, "modelo": modelo}


def metricas(semana: str, r: dict, duracao_s: float) -> dict:
    """Resumo de tokens, custo e tempo de uma geração (content/semanas/<semana>/metricas-geracao.json)."""
    chaves = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    total = {c: sum(u.get(c) or 0 for u in r["uso"]) for c in chaves}
    total["custo_usd"] = round(sum(u.get("custo_usd") or 0 for u in r["uso"]), 6)
    total["duracao_cli_s"] = round(sum(u.get("duracao_ms") or 0 for u in r["uso"]) / 1000, 1)
    return {
        "semana": semana,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modelo": r["modelo"],
        "tentativas": r["tentativas"],
        "erros": len(r["erros"]),
        "duracao_s": round(duracao_s, 1),
        "total": total,
        "chamadas": r["uso"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gera posts.json a partir do briefing (claude -p)")
    ap.add_argument("briefing", type=Path)
    ap.add_argument("--saida", type=Path, help="padrão: posts.json ao lado do briefing")
    args = ap.parse_args(argv)

    config = lint.carregar_config(RAIZ / "config.yaml")
    briefing = json.loads(args.briefing.read_text(encoding="utf-8"))
    cartao = (RAIZ / "cartao-marca.md").read_text(encoding="utf-8")
    inicio = time.monotonic()
    r = gerar(briefing, cartao, RAIZ / "schemas" / "posts.schema.json", config)
    duracao = time.monotonic() - inicio
    saida = args.saida or args.briefing.with_name("posts.json")
    saida.write_text(json.dumps(r["dados"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = metricas(briefing.get("semana", ""), r, duracao)
    args.briefing.with_name("metricas-geracao.json").write_text(
        json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tokens: {m['total']['input_tokens']} entrada / {m['total']['output_tokens']} saída · "
          f"{m['duracao_s']} s · modelo {m['modelo']}")
    for e in r["erros"]:
        print(e)
    print(f"{saida} — {r['tentativas']} tentativa(s), {len(r['erros'])} erro(s) restante(s)")
    return 1 if r["erros"] else 0


if __name__ == "__main__":
    sys.exit(main())
