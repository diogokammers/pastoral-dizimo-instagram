"""Fatia 3 — lint determinístico dos posts (arquitetura §1.1 e §6) e JSON Schema de posts.json."""
import copy

import pytest

from pastoral import lint

EDICAO = "Bíblia Sagrada — Tradução Oficial da CNBB"
ASSINATURA = "Pastoral do Dízimo — Arquidiocese de Florianópolis"


@pytest.fixture
def config(raiz):
    return lint.carregar_config(raiz / "config.yaml")


def post_valido() -> dict:
    """Post mínimo que passa em todas as regras."""
    return {
        "numero": 2,
        "titulo": "O que é o dízimo?",
        "pilar": "Formação",
        "formato": "carrossel",
        "publico": "Dizimistas e interessados",
        "cta": "salvar",
        "slides": [
            {"template": "capa", "eyebrow": "Formação", "titulo": "O que é o dízimo?",
             "alt_text": "Capa em fundo vermelho com o título O que é o dízimo?"},
            {"template": "citacao", "texto": "Deus ama quem dá com alegria.", "referencia": "2Cor 9,7",
             "alt_text": "Versículo: Deus ama quem dá com alegria, 2Cor 9,7."},
            {"template": "cta", "titulo": "Salve este post", "texto": "Para rever quando precisar.",
             "alt_text": "Convite para salvar o post."},
        ],
        "legenda": f"O dízimo é gesto de fé e gratidão.\n\nSalve este post.\n\n{ASSINATURA}",
        "hashtags": [],
        "fontes": [{"tipo": "biblia", "referencia": "2Cor 9,7", "edicao": EDICAO}],
    }


def erros_de(post, config):
    return lint.verificar_post(post, config)


def test_post_valido_passa(config):
    assert erros_de(post_valido(), config) == []


@pytest.mark.parametrize("termo", [
    "taxa", "mensalidade", "cobrança", "imposto", "tributo", "prosperidade", "retorno",
    "percentual fixo", "urgente", "última chance", "culpa", "pecado", "contribua", "doe",
])
def test_termo_proibido_reprova(config, termo):
    post = post_valido()
    post["slides"][0]["titulo"] = f"Sobre {termo} hoje"
    assert any("proibido" in e for e in erros_de(post, config))


def test_termo_proibido_na_legenda_reprova(config):
    post = post_valido()
    post["legenda"] = "Não é mensalidade.\n\n" + ASSINATURA
    assert any("mensalidade" in e for e in erros_de(post, config))


def test_termo_proibido_nao_casa_dentro_de_outra_palavra(config):
    post = post_valido()
    # "doença" contém "doe" só como prefixo; "retornar" não é "retorno"
    post["slides"][0]["titulo"] = "Doença e esperança"
    assert erros_de(post, config) == []


def test_porcentagem_reprova(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Nem 10% nem nada."
    assert any("%" in e for e in erros_de(post, config))


def test_dez_por_cento_por_extenso_reprova(config):
    post = post_valido()
    post["legenda"] = "Não são dez por cento.\n\n" + ASSINATURA
    assert any("proibido" in e for e in erros_de(post, config))


def test_legenda_longa_reprova(config):
    post = post_valido()
    post["legenda"] = "a" * 1400 + "\n\n" + ASSINATURA + " " + "b" * 100
    assert any("legenda" in e for e in erros_de(post, config))


def test_legenda_sem_assinatura_reprova(config):
    post = post_valido()
    post["legenda"] = "Texto sem assinatura."
    assert any("assinatura" in e for e in erros_de(post, config))


def test_mais_de_8_hashtags_reprova(config):
    post = post_valido()
    post["hashtags"] = [f"#tag{i}" for i in range(9)]
    assert any("hashtag" in e for e in erros_de(post, config))


def test_hashtags_escritas_na_legenda_contam(config):
    post = post_valido()
    post["legenda"] += " " + " ".join(f"#t{i}" for i in range(9))
    assert any("hashtag" in e for e in erros_de(post, config))


def test_slide_com_mais_de_25_palavras_reprova(config):
    post = post_valido()
    post["slides"][2]["texto"] = " ".join(["palavra"] * 26)
    assert any("25 palavras" in e for e in erros_de(post, config))


def test_contagem_de_palavras_inclui_titulo_e_fonte():
    slide = {"template": "conteudo", "titulo": "Um dois", "texto": "três quatro", "fonte": "cinco",
             "alt_text": "não conta nada aqui", "numero": "2/6"}
    assert lint.palavras_do_slide(slide) == 5


def test_cta_fora_da_lista_reprova(config):
    post = post_valido()
    post["cta"] = "contribuir"
    assert any("CTA" in e for e in erros_de(post, config))


def test_cta_aceita_maiusculas(config):
    post = post_valido()
    post["cta"] = "Seguir o perfil"
    assert erros_de(post, config) == []


@pytest.mark.parametrize("n", [1, 11])
def test_carrossel_fora_de_2_a_10_reprova(config, n):
    post = post_valido()
    post["slides"] = [copy.deepcopy(post["slides"][0]) for _ in range(n)]
    assert any("slides" in e for e in erros_de(post, config))


def test_imagem_unica_com_dois_slides_reprova(config):
    post = post_valido()
    post["formato"] = "imagem_unica"
    post["slides"] = post["slides"][:2]
    assert any("imagem_unica" in e for e in erros_de(post, config))


def test_alt_text_vazio_ou_longo_reprova(config):
    post = post_valido()
    post["slides"][0]["alt_text"] = ""
    post["slides"][1]["alt_text"] = "x" * 1001
    erros = erros_de(post, config)
    assert sum("alt_text" in e for e in erros) == 2


def test_referencia_biblica_sem_fonte_com_edicao_reprova(config):
    post = post_valido()
    post["fontes"] = []
    assert any("edição" in e for e in erros_de(post, config))


def test_referencia_biblica_no_texto_precisa_estar_nas_fontes(config):
    post = post_valido()
    post["legenda"] = "Leia Mt 6,1-4.\n\n" + ASSINATURA
    assert any("Mt 6,1-4" in e for e in erros_de(post, config))


def test_citacao_sem_referencia_valida_reprova(config):
    post = post_valido()
    post["slides"][1]["referencia"] = "Coríntios"
    post["fontes"][0]["referencia"] = "Coríntios"
    assert any("referência" in e for e in erros_de(post, config))


def test_extrai_referencias_biblicas():
    texto = "Leia 2Cor 9,7 e cf. Rm 15,26-27; também At 2,42-47 e Lc 21,1."
    assert lint.referencias_biblicas(texto) == ["2Cor 9,7", "Rm 15,26-27", "At 2,42-47", "Lc 21,1"]


def test_canone_nao_e_referencia_biblica():
    assert lint.referencias_biblicas("cân. 222 §1 e CIC 2043") == []


def test_doc106_so_com_paragrafo_verificado(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Como diz o Doc. CNBB 106, n. 40."
    assert any("106" in e for e in erros_de(post, config))


def test_doc106_paragrafo_verificado_passa(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Doc. CNBB 106, n. 12."
    assert erros_de(post, config) == []


def test_doc106_por_extenso_no_alt_text_passa(config):
    post = post_valido()
    post["slides"][2]["alt_text"] = "Fonte: Documento 106 da CNBB, número 9."
    assert erros_de(post, config) == []


def test_quatro_dimensoes_podem_ser_atribuidas_ao_doc106(config):
    """Revogado em 2026-09-27: as dimensões estão no Doc. 106, seção 3, n. 29–32."""
    post = post_valido()
    post["legenda"] = ("As quatro dimensões do dízimo (Doc. CNBB 106, n. 29-32).\n\n" + ASSINATURA)
    assert erros_de(post, config) == []


@pytest.mark.parametrize("n", [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 51, 52, 63, 64, 65, 66])
def test_doc106_segunda_leitura_aceita(config, n):
    post = post_valido()
    post["slides"][2]["texto"] = f"Doc. CNBB 106, n. {n}."
    assert erros_de(post, config) == []


# ---------- CIC e CDC: sempre com número válido ----------

def test_cic_com_numero_passa(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Serviço da comunidade (cf. CIC 910)."
    assert erros_de(post, config) == []


def test_cic_sem_numero_reprova(config):
    post = post_valido()
    post["legenda"] = "Como ensina o CIC, o dízimo é gesto de fé.\n\n" + ASSINATURA
    assert any("CIC" in e for e in erros_de(post, config))


def test_cic_fora_do_intervalo_reprova(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Veja CIC 3000."
    assert any("CIC" in e for e in erros_de(post, config))


def test_canone_com_numero_passa(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Os fiéis proveem às necessidades da Igreja (cân. 222 §1)."
    post["slides"][2]["alt_text"] = "Fonte: Código de Direito Canônico, cânon 222, parágrafo 1."
    assert erros_de(post, config) == []


def test_canone_sem_numero_reprova(config):
    post = post_valido()
    post["legenda"] = "Diz o cân. que os fiéis proveem.\n\n" + ASSINATURA
    assert any("cân" in e for e in erros_de(post, config))


def test_canone_fora_do_intervalo_reprova(config):
    post = post_valido()
    post["slides"][2]["texto"] = "Veja cân. 1800."
    assert any("cân" in e for e in erros_de(post, config))


# ---------- escopo das 4 fontes (Doc. 106, CIC, CDC, Bíblia) ----------

@pytest.mark.parametrize("texto", [
    "Neste Mês Missionário, partilhe.",
    "O agente atua como voluntário.",
    "Serviço voluntário na paróquia.",
    "Uma agente voluntária.",
    "Hoje é dia de Santa Teresinha.",
])
def test_termo_fora_de_escopo_reprova(config, texto):
    post = post_valido()
    post["legenda"] = texto + "\n\n" + ASSINATURA
    assert any("fora do escopo" in e for e in erros_de(post, config))


def test_verificar_lote_prefixa_numero_do_post(config):
    post = post_valido()
    post["cta"] = "doar"
    erros = lint.verificar_lote({"lote": "t", "posts": [post]}, config)
    assert erros and all(e.startswith("post 2:") for e in erros)


# ---------- JSON Schema ----------

def test_schema_aceita_post_valido(raiz):
    assert lint.validar_schema({"lote": "t", "posts": [post_valido()]}, raiz / "schemas/posts.schema.json") == []


def test_schema_rejeita_template_desconhecido(raiz):
    post = post_valido()
    post["slides"][0]["template"] = "banner"
    erros = lint.validar_schema({"lote": "t", "posts": [post]}, raiz / "schemas/posts.schema.json")
    assert erros


def test_schema_rejeita_campo_obrigatorio_ausente(raiz):
    post = post_valido()
    del post["legenda"]
    assert lint.validar_schema({"lote": "t", "posts": [post]}, raiz / "schemas/posts.schema.json")


def test_schema_rejeita_campo_extra(raiz):
    post = post_valido()
    post["preco"] = "x"
    assert lint.validar_schema({"lote": "t", "posts": [post]}, raiz / "schemas/posts.schema.json")


def test_main_devolve_1_com_erros(tmp_path, raiz):
    import json
    ruim = post_valido()
    ruim["cta"] = "doar"
    arq = tmp_path / "posts.json"
    arq.write_text(json.dumps({"lote": "t", "posts": [ruim]}, ensure_ascii=False), encoding="utf-8")
    assert lint.main([str(arq), "--config", str(raiz / "config.yaml")]) == 1



def test_doc106_capitulo_por_extenso_e_n7_aceitos():
    assert lint.RE_DOC106.search("Doc. CNBB 106, Capítulo II").group(2)
    assert 7 in lint.PARAGRAFOS_DOC106 and 4 in lint.PARAGRAFOS_DOC106
