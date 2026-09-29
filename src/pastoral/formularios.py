"""Exporta as respostas dos formulários da bio (D1 pastoral-formularios) para o repositório PRIVADO de dados (ADR-013).

Grava `respostas.jsonl` (histórico completo, uma resposta por linha) e `respostas.csv` (planilha, UTF-8 com BOM)
no clone de `diogokammers/pastoral-dizimo-dados` e faz o commit lá. Nunca grava dentro deste repositório,
que é público. Push só com `--push`.

Uso: python -m pastoral.formularios --exportar [--dados-dir CAMINHO] [--push]   (com PYTHONPATH=src)
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]

COLUNAS = ["id", "criado_em", "tipo", "versao_form", "paroquia", "paroquia_outra", "funcao", "pedido", "temas",
           "descricao", "assunto", "mensagem", "nome", "contato"]

SQL = "SELECT id, criado_em, tipo, versao_form, dados FROM respostas ORDER BY criado_em, id"


def dentro_do_repo(pasta: Path, raiz: Path = RAIZ) -> bool:
    """True se `pasta` é o repositório público ou fica dentro dele."""
    pasta, raiz = Path(pasta).resolve(), raiz.resolve()
    return pasta == raiz or raiz in pasta.parents


def executar_wrangler(sql: str) -> list:
    """Roda a consulta no D1 remoto com o login da Pastoral e devolve o JSON do wrangler."""
    npx = shutil.which("npx")
    if not npx:
        raise SystemExit("npx não encontrado (instale o Node ≥ 22.13)")
    ambiente = dict(os.environ)
    ambiente.pop("CLOUDFLARE_API_TOKEN", None)
    ambiente.pop("CLOUDFLARE_ACCOUNT_ID", None)
    ambiente["XDG_CONFIG_HOME"] = "C:/Users/odnac/.config-pastoral-dizimo"
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))["formularios"]
    proc = subprocess.run([npx, "wrangler", "d1", "execute", config["d1"], "--remote", "--json", "--command", sql],
                          cwd=RAIZ / "links", env=ambiente, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"wrangler falhou:\n{proc.stderr or proc.stdout}")
    return json.loads(proc.stdout[proc.stdout.index("["):])


def buscar_respostas(executar) -> list[dict]:
    """Respostas em ordem de chegada, com `dados` já aberto (dict)."""
    linhas = []
    for bloco in executar(SQL):
        linhas.extend(bloco.get("results", []))
    saida = [dict(l, dados=json.loads(l["dados"])) for l in linhas]
    return sorted(saida, key=lambda r: (r["criado_em"], r["id"]))


def _celula(valor) -> str:
    """Texto para o CSV; o que começa com = + - @ ganha ' para não virar fórmula na planilha."""
    texto = " | ".join(valor) if isinstance(valor, list) else ("" if valor is None else str(valor))
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


def escrever(respostas: list[dict], pasta: Path) -> None:
    pasta = Path(pasta)
    with open(pasta / "respostas.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in respostas:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    with open(pasta / "respostas.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS)
        for r in respostas:
            plano = {**r["dados"], **{k: r[k] for k in ("id", "criado_em", "tipo", "versao_form")}}
            w.writerow([_celula(plano.get(c)) for c in COLUNAS])


def _git(pasta: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, encoding="utf-8")


def _push(pasta: Path) -> None:
    proc = _git(pasta, "push")
    if proc.returncode != 0:
        raise SystemExit(f"git push falhou:\n{proc.stderr}")


def exportar(pasta: Path, executar=executar_wrangler, push: bool = False, empurrar=_push) -> int:
    """Baixa, grava e faz commit no repositório de dados. Devolve o número de respostas."""
    pasta = Path(pasta)
    if dentro_do_repo(pasta):
        raise SystemExit(f"recusado: {pasta} fica dentro do repositório público; use o clone de pastoral-dizimo-dados")
    if not (pasta / ".git").exists():
        raise SystemExit(f"{pasta} não é um repositório git (clone diogokammers/pastoral-dizimo-dados)")
    respostas = buscar_respostas(executar)
    escrever(respostas, pasta)
    _git(pasta, "add", "respostas.jsonl", "respostas.csv")
    if _git(pasta, "diff", "--cached", "--quiet").returncode != 0:
        quando = datetime.now().strftime("%Y-%m-%d %H:%M")
        proc = _git(pasta, "commit", "-q", "-m", f"dados: exportação de {len(respostas)} resposta(s) ({quando})")
        if proc.returncode != 0:
            raise SystemExit(f"git commit falhou:\n{proc.stderr}")
    if push:
        empurrar(pasta)
    return len(respostas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--exportar", action="store_true", required=True, help="baixa o D1 para o repositório de dados")
    p.add_argument("--dados-dir", help="clone de pastoral-dizimo-dados (padrão: formularios.dados_dir do config.yaml)")
    p.add_argument("--push", action="store_true", help="envia o commit para o GitHub")
    args = p.parse_args(argv)
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))["formularios"]
    pasta = Path(args.dados_dir) if args.dados_dir else (RAIZ / config["dados_dir"])
    n = exportar(pasta.resolve(), push=args.push)
    print(f"{n} resposta(s) exportada(s) para {pasta.resolve()}" + (" (enviado ao GitHub)" if args.push else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
