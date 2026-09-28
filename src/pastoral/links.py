"""Página de links da bio e formulários de escuta (ADR-013).

Fonte única: content/formularios.yaml + content/paroquias.yaml (+ paleta do config.yaml). Gera:
- links/public/index.html  — a página (templates/links.html com os dados embutidos);
- links/lib/campos.js       — as listas que o servidor usa para validar (mesmas da página);
- links/public/avatar.jpg   — cópia de site/midia/perfil/avatar.jpg.

Uso: python -m pastoral.links   (com PYTHONPATH=src)
"""
import html
import json
import shutil
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]

CSP = ("default-src 'none'; img-src 'self'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; script-src 'unsafe-inline'; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'")


def _ler(caminho: Path) -> dict:
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def carregar(raiz: Path = RAIZ) -> dict:
    """Junta os YAML num dicionário: formulários, paróquias e paleta."""
    form = _ler(raiz / "content" / "formularios.yaml")
    paroquias = _ler(raiz / "content" / "paroquias.yaml")["paroquias"]
    paleta = _ler(raiz / "config.yaml")["marca"]["paleta"]
    return {"form": form, "paroquias": paroquias, "paleta": paleta}


def campos(dados: dict) -> dict:
    """As listas fechadas que página e servidor compartilham."""
    f = dados["form"]
    return {
        "versao": f["versao"],
        "limites": f["limites"],
        "paroquias": dados["paroquias"],
        "outra": f["textos"]["outra_paroquia"],
        "prefiro_nao_dizer": f["textos"]["prefiro_nao_dizer"],
        "agente": {k: f["agente"][k] for k in ("funcoes", "pedidos", "pedidos_com_contato", "temas")},
        "fiel": {"assuntos": f["fiel"]["assuntos"]},
    }


def montar_campos_js(dados: dict) -> str:
    corpo = json.dumps(campos(dados), ensure_ascii=False, indent=2)
    return ("// GERADO por `python -m pastoral.links` a partir de content/formularios.yaml e content/paroquias.yaml.\n"
            "// Não edite à mão.\n"
            f"export const CAMPOS = {corpo};\n")


def montar_pagina(dados: dict) -> str:
    f = dados["form"]
    embutido = {
        "textos": f["textos"],
        "consentimento": " ".join(f["consentimento"].split()),
        "agente": {"titulo": f["agente"]["titulo"], "rotulos": f["agente"]["rotulos"]},
        "fiel": {"titulo": f["fiel"]["titulo"], "rotulos": f["fiel"]["rotulos"]},
        "campos": campos(dados),
    }
    # JSON dentro de <script>: "</" vira "<\/" para não fechar a tag
    json_seguro = json.dumps(embutido, ensure_ascii=False).replace("</", "<\\/")
    pagina = (RAIZ / "templates" / "links.html").read_text(encoding="utf-8")
    trocas = {"csp": html.escape(CSP), "dados": json_seguro}
    trocas.update(dados["paleta"])
    for chave, valor in trocas.items():
        pagina = pagina.replace("{{" + chave + "}}", valor)
    if "{{" in pagina:
        raise ValueError("marcador sem valor no templates/links.html")
    return pagina


def main(argv: list[str] | None = None) -> int:
    dados = carregar(RAIZ)
    publico = RAIZ / "links" / "public"
    publico.mkdir(parents=True, exist_ok=True)
    (publico / "index.html").write_text(montar_pagina(dados), encoding="utf-8", newline="\n")
    (RAIZ / "links" / "lib" / "campos.js").write_text(montar_campos_js(dados), encoding="utf-8", newline="\n")
    shutil.copyfile(RAIZ / "site" / "midia" / "perfil" / "avatar.jpg", publico / "avatar.jpg")
    print("gerados: links/public/index.html, links/lib/campos.js, links/public/avatar.jpg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
