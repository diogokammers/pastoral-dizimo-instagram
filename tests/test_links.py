"""ADR-013 — página de links da bio e formulários de escuta: dados (paróquias e campos) e página gerada."""
import re
import unicodedata
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
    # ordem alfabética (cidade na frente), sem considerar acentos nem maiúsculas
    chave = lambda t: unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().casefold()
    assert lista == sorted(lista, key=chave)


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


# ---------- página e campos gerados (python -m pastoral.links) ----------

def gerados():
    from pastoral import links
    dados = links.carregar(RAIZ)
    return dados, links.montar_pagina(dados), links.montar_campos_js(dados)


def test_arquivos_gerados_estao_atualizados():
    _, pagina, campos = gerados()
    assert (RAIZ / "links" / "public" / "index.html").read_text(encoding="utf-8") == pagina, \
        "rode: python -m pastoral.links"
    assert (RAIZ / "links" / "lib" / "campos.js").read_text(encoding="utf-8") == campos, \
        "rode: python -m pastoral.links"
    assert (RAIZ / "links" / "public" / "avatar.jpg").read_bytes() == \
        (RAIZ / "site" / "midia" / "perfil" / "avatar.jpg").read_bytes()


def test_campos_js_espelha_os_yaml():
    import json
    dados, _, campos = gerados()
    assert campos.startswith("// GERADO")
    objeto = json.loads(campos.split("export const CAMPOS = ", 1)[1].rstrip().rstrip(";"))
    f = ler(FORMULARIOS)
    assert objeto == {
        "versao": f["versao"],
        "limites": f["limites"],
        "paroquias": ler(PAROQUIAS)["paroquias"],
        "outra": f["textos"]["outra_paroquia"],
        "prefiro_nao_dizer": f["textos"]["prefiro_nao_dizer"],
        "agente": {k: f["agente"][k] for k in ("funcoes", "pedidos", "pedidos_com_contato", "temas")},
        "fiel": {"assuntos": f["fiel"]["assuntos"]},
    }


def test_pagina_tem_dados_marca_e_seguranca():
    import html
    import json
    _, pagina, _ = gerados()
    dados_pagina = json.loads(re.search(r'<script id="dados" type="application/json">(.*?)</script>', pagina, re.S).group(1))
    assert dados_pagina["campos"]["paroquias"] == ler(PAROQUIAS)["paroquias"]
    assert dados_pagina["campos"]["agente"]["temas"] == TEMAS_SPEC
    csp = html.unescape(re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', pagina).group(1))
    assert "unsafe-eval" not in csp and "connect-src 'self'" in csp and "form-action 'none'" in csp
    config = ler(RAIZ / "config.yaml")
    for cor in ("vermelho", "creme", "grafite", "cinza", "dourado"):
        assert config["marca"]["paleta"][cor] in pagina
    assert "Cormorant+Garamond" in pagina and "Source+Sans+3" in pagina
    assert 'name="site"' in pagina  # campo invisível contra robôs


def test_texto_fixo_da_pagina_segue_o_cartao():
    _, pagina, _ = gerados()
    visivel = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", pagina, flags=re.S)
    assert problemas_de_texto(visivel) == []
