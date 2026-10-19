"""Fatia 7 — portão de publicação (arquitetura §5 e §6). Cliente da Meta sempre falso.

Regra de ouro: em qualquer caso negativo, `media_publish` NÃO pode ser chamado.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from pastoral import publicar

SEGREDO = "segredo-de-teste"
SEMANA = "2026-W41"
AGENDADO = "2026-10-06T19:00:00-03:00"
DEPOIS = datetime(2026, 10, 6, 22, 30, tzinfo=timezone.utc)      # 19:30 em Brasília
ANTES = datetime(2026, 10, 6, 21, 0, tzinfo=timezone.utc)        # 18:00 em Brasília
CONFIG = {"midia": {"base_url": "https://exemplo.github.io/repo/", "pasta": "site/midia"},
          "meta": {"poll_intervalo_s": 60, "poll_max_s": 300}}
ARTES = {"post-12-01.jpg": b"\xff\xd8capa", "post-12-02.jpg": b"\xff\xd8conteudo"}


class MetaFalsa:
    """Cliente falso. Com `proibir_publicar`, qualquer media_publish derruba o teste."""

    def __init__(self, proibir_publicar=False):
        self.proibir = proibir_publicar
        self.chamadas = []

    def criar_item_carrossel(self, image_url, alt_text=None):
        self.chamadas.append(("item", image_url, alt_text))
        return f"item{len(self.chamadas)}"

    def criar_imagem(self, image_url, caption, alt_text=None):
        self.chamadas.append(("imagem", image_url, caption))
        return "img"

    def criar_carrossel(self, children, caption):
        self.chamadas.append(("carrossel", tuple(children), caption))
        return "car"

    def aguardar(self, container_id, intervalo=60, maximo=300):
        self.chamadas.append(("aguardar", container_id))

    def media_publish(self, creation_id):
        if self.proibir:
            pytest.fail("media_publish chamado num caso negativo")
        self.chamadas.append(("publish", creation_id))
        return "m777"

    def permalink(self, media_id):
        return "https://www.instagram.com/p/ABC/"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


POST = {"numero": 12, "titulo": "T", "legenda": "Legenda do post.", "hashtags": ["#dizimo", "#fe"],
        "slides": [{"template": "capa", "alt_text": "Alt 1"}, {"template": "conteudo", "alt_text": "Alt 2"}]}


def aprovacao_valida(**troca):
    item = {"numero": 12, "agendado_para": AGENDADO,
            "legenda_sha256": sha(publicar.texto_legenda(POST).encode("utf-8")),
            "alt_text_sha256": sha(publicar.texto_alt(POST).encode("utf-8")),
            "artes": [{"arquivo": n, "sha256": sha(b)} for n, b in ARTES.items()]}
    item.update(troca)
    dados = {"semana": SEMANA, "aprovado_por": "Diogo", "aprovado_em": "2026-10-01T10:00:00-03:00",
             "nonce": "n1", "posts": [item]}
    dados["assinatura"] = publicar.assinar(dados, SEGREDO)
    return dados


@pytest.fixture
def repo(tmp_path):
    """Repositório mínimo: posts.json da semana, artes em site/midia e aprovação válida."""
    pasta = tmp_path / "content" / "semanas" / SEMANA
    pasta.mkdir(parents=True)
    (pasta / "posts.json").write_text(json.dumps({"posts": [POST]}, ensure_ascii=False), encoding="utf-8")
    midia = tmp_path / "site" / "midia" / SEMANA
    midia.mkdir(parents=True)
    for nome, conteudo in ARTES.items():
        (midia / nome).write_bytes(conteudo)
    gravar_aprovacao(tmp_path, aprovacao_valida())
    return tmp_path


def gravar_aprovacao(raiz, dados):
    caminho = raiz / "content" / "semanas" / SEMANA / "aprovacao.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def baixar_ok(url):
    return ARTES[url.rsplit("/", 1)[1]]


def rodar(raiz, cliente, agora=DEPOIS, dry_run=False, segredo=SEGREDO, baixar=baixar_ok):
    return publicar.executar(raiz, CONFIG, segredo=segredo, agora=agora, cliente=cliente,
                             dry_run=dry_run, baixar=baixar)


# ---------- HMAC ----------

def test_assinar_e_validar():
    dados = aprovacao_valida()
    assert publicar.assinatura_valida(dados, SEGREDO)
    assert not publicar.assinatura_valida(dados, "outro")
    adulterado = json.loads(json.dumps(dados))
    adulterado["posts"][0]["agendado_para"] = "2026-10-05T19:00:00-03:00"
    assert not publicar.assinatura_valida(adulterado, SEGREDO)
    assert not publicar.assinatura_valida({k: v for k, v in dados.items() if k != "assinatura"}, SEGREDO)
    assert not publicar.assinatura_valida(dados, "")          # segredo vazio nunca vale


def test_canonico_independe_da_ordem_das_chaves():
    assert publicar.canonico({"b": 1, "a": "ç"}) == publicar.canonico({"a": "ç", "b": 1})
    assert publicar.canonico({"a": "ç"}) == '{"a":"ç"}'.encode("utf-8")


def test_texto_legenda_acrescenta_hashtags():
    assert publicar.texto_legenda(POST) == "Legenda do post.\n\n#dizimo #fe"
    assert publicar.texto_legenda({"legenda": "Só texto", "hashtags": []}) == "Só texto"


# ---------- casos negativos: media_publish nunca é chamado ----------

def test_sem_aprovacao(repo):
    (repo / "content" / "semanas" / SEMANA / "aprovacao.json").unlink()
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert meta.chamadas == []
    assert r["publicados"] == []
    assert any("aprova" in d["motivo"] for d in r["recusados"])


def test_assinatura_invalida(repo):
    dados = aprovacao_valida()
    dados["assinatura"] = "0" * 64
    gravar_aprovacao(repo, dados)
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert meta.chamadas == [] and r["publicados"] == []
    assert r["recusados"][0]["grave"]
    assert "assinatura" in r["recusados"][0]["motivo"]


def test_aprovacao_forjada_sem_segredo(repo):
    dados = aprovacao_valida()
    dados["assinatura"] = publicar.assinar(dados, "chute")
    gravar_aprovacao(repo, dados)
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_segredo_ausente(repo):
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta, segredo="")
    assert r["publicados"] == [] and meta.chamadas == []


def test_hash_da_arte_divergente(repo):
    (repo / "site" / "midia" / SEMANA / "post-12-02.jpg").write_bytes(b"\xff\xd8outra arte")
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert meta.chamadas == [] and r["publicados"] == []
    assert "post-12-02.jpg" in r["recusados"][0]["motivo"]
    assert r["recusados"][0]["grave"]


def test_arte_ausente(repo):
    (repo / "site" / "midia" / SEMANA / "post-12-01.jpg").unlink()
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_legenda_alterada_depois_da_aprovacao(repo):
    alterado = dict(POST, legenda="Legenda trocada depois.")
    (repo / "content" / "semanas" / SEMANA / "posts.json").write_text(
        json.dumps({"posts": [alterado]}), encoding="utf-8")
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert meta.chamadas == [] and "legenda" in r["recusados"][0]["motivo"]


def test_alt_text_alterado_depois_da_aprovacao(repo):
    slides = [dict(POST["slides"][0]), dict(POST["slides"][1], alt_text="Outro")]
    (repo / "content" / "semanas" / SEMANA / "posts.json").write_text(
        json.dumps({"posts": [dict(POST, slides=slides)]}), encoding="utf-8")
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_arte_publica_difere_da_aprovada(repo):
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta, baixar=lambda url: b"versao antiga do Pages")
    assert meta.chamadas == [] and r["publicados"] == []
    assert "URL" in r["recusados"][0]["motivo"]


def test_data_futura(repo):
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta, agora=ANTES)
    assert meta.chamadas == [] and r["publicados"] == []
    assert "agendad" in r["recusados"][0]["motivo"]
    assert not r["recusados"][0]["grave"]          # esperar a data é normal, não alerta


def test_data_sem_fuso_e_recusada(repo):
    gravar_aprovacao(repo, aprovacao_valida(agendado_para="2026-10-06T19:00:00"))
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_ja_publicado_no_ledger_da_semana(repo):
    ledger = {"semana": SEMANA, "posts": [{"numero": 12, "ig_media_id": "m1"}]}
    (repo / "content" / "semanas" / SEMANA / "publicado.json").write_text(json.dumps(ledger), encoding="utf-8")
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert meta.chamadas == [] and "publicado" in r["recusados"][0]["motivo"]


def test_ja_publicado_no_ledger_da_estreia(repo):
    """Numeração é global: um número que já saiu na estreia não sai de novo."""
    gravar_aprovacao(repo, aprovacao_valida(numero=2))
    dados = {"posts": [dict(POST, numero=2)]}
    (repo / "content" / "semanas" / SEMANA / "posts.json").write_text(json.dumps(dados), encoding="utf-8")
    (repo / "content" / "estreia").mkdir(parents=True)
    (repo / "content" / "estreia" / "publicado.json").write_text(
        json.dumps({"posts": [{"numero": 2, "url": "https://www.instagram.com/p/x/"}]}), encoding="utf-8")
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_semana_da_aprovacao_diferente_da_pasta(repo):
    dados = aprovacao_valida()
    dados["semana"] = "2026-W40"
    dados["assinatura"] = publicar.assinar({k: v for k, v in dados.items() if k != "assinatura"}, SEGREDO)
    gravar_aprovacao(repo, dados)
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta)["publicados"] == [] and meta.chamadas == []


def test_dry_run_nao_toca_na_meta_nem_no_ledger(repo):
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta, dry_run=True)
    assert meta.chamadas == []
    assert r["publicados"] == []
    assert [d["numero"] for d in r["prontos"]] == [12]
    assert not (repo / "content" / "semanas" / SEMANA / "publicado.json").exists()


# ---------- caso positivo ----------

def test_caso_integro_publica_e_grava_ledger(repo):
    meta = MetaFalsa()
    r = rodar(repo, meta)
    assert [p["numero"] for p in r["publicados"]] == [12]
    base = "https://exemplo.github.io/repo/midia/2026-W41/"
    assert meta.chamadas[0] == ("item", base + "post-12-01.jpg", "Alt 1")
    assert meta.chamadas[1] == ("item", base + "post-12-02.jpg", "Alt 2")
    assert ("carrossel", ("item1", "item2"), "Legenda do post.\n\n#dizimo #fe") in meta.chamadas
    assert meta.chamadas[-1] == ("publish", "car")
    assert ("aguardar", "car") in meta.chamadas
    ledger = json.loads((repo / "content" / "semanas" / SEMANA / "publicado.json").read_text(encoding="utf-8"))
    entrada = ledger["posts"][0]
    assert entrada["numero"] == 12
    assert entrada["ig_media_id"] == "m777"
    assert entrada["permalink"] == "https://www.instagram.com/p/ABC/"
    # rodar de novo não publica outra vez (idempotência)
    meta2 = MetaFalsa(proibir_publicar=True)
    assert rodar(repo, meta2)["publicados"] == []


def test_imagem_unica(repo):
    post = dict(POST, slides=[POST["slides"][0]])
    (repo / "content" / "semanas" / SEMANA / "posts.json").write_text(json.dumps({"posts": [post]}), encoding="utf-8")
    item = {"legenda_sha256": sha(publicar.texto_legenda(post).encode("utf-8")),
            "alt_text_sha256": sha(publicar.texto_alt(post).encode("utf-8")),
            "artes": [{"arquivo": "post-12-01.jpg", "sha256": sha(ARTES["post-12-01.jpg"])}]}
    gravar_aprovacao(repo, aprovacao_valida(**item))
    meta = MetaFalsa()
    assert [p["numero"] for p in rodar(repo, meta)["publicados"]] == [12]
    assert meta.chamadas[0][0] == "imagem"


def test_cli_padrao_e_dry_run(repo, monkeypatch, capsys):
    monkeypatch.delenv("PUBLICAR", raising=False)
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    chamado = []
    monkeypatch.setattr(publicar.meta.ClienteMeta, "do_ambiente", classmethod(lambda cls, c: chamado.append(1)))
    assert publicar.main(["--raiz", str(repo), "--agora", DEPOIS.isoformat()]) == 0
    assert chamado == []                               # sem PUBLICAR=1 nem cria o cliente
    assert "dry-run" in capsys.readouterr().out


def test_cli_dry_run_explicito_vence_publicar(repo, monkeypatch):
    monkeypatch.setenv("PUBLICAR", "1")
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    chamado = []
    monkeypatch.setattr(publicar.meta.ClienteMeta, "do_ambiente", classmethod(lambda cls, c: chamado.append(1)))
    assert publicar.main(["--raiz", str(repo), "--dry-run", "--agora", DEPOIS.isoformat()]) == 0
    assert chamado == []


def test_cli_falha_grave_retorna_1(repo, monkeypatch):
    monkeypatch.delenv("PUBLICAR", raising=False)
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", "segredo-errado")
    assert publicar.main(["--raiz", str(repo), "--agora", DEPOIS.isoformat()]) == 1


def test_cli_ignora_quebra_de_linha_no_segredo(repo, monkeypatch, capsys):
    """Secret colado com Enter (PowerShell/gh) continua valendo: o Worker também faz trim (ADR-009)."""
    monkeypatch.delenv("PUBLICAR", raising=False)
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO + "\r\n")
    # o config.yaml real tem a fila ligada (ADR-015): a quarta 07/10 às 18:30 é o horário em que o post sai
    quarta = datetime(2026, 10, 7, 21, 30, tzinfo=timezone.utc)
    assert publicar.main(["--raiz", str(repo), "--agora", quarta.isoformat()]) == 0
    assert "[ok]" in capsys.readouterr().out


def test_sem_semanas_nao_falha(tmp_path, monkeypatch):
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    assert publicar.main(["--raiz", str(tmp_path)]) == 0


def test_url_publica():
    assert publicar.url_publica("https://a.io/r/", "2026-W41", "post-1-01.jpg") == \
        "https://a.io/r/midia/2026-W41/post-1-01.jpg"
    assert publicar.url_publica("https://a.io/r", "2026-W41", "x.jpg") == "https://a.io/r/midia/2026-W41/x.jpg"


# ---------- alerta: post agendado sem aprovação (falha silenciosa de 2026-10-06) ----------

def gravar_agenda(raiz, posts):
    caminho = raiz / "content" / "semanas" / SEMANA / "agenda.json"
    caminho.write_text(json.dumps({"semana": SEMANA, "posts": posts}, ensure_ascii=False), encoding="utf-8")


def test_alerta_post_da_janela_sem_aprovacao(repo):
    """Post agendado a menos de 30 h (antes ou depois) sem aprovação nem publicação vira alerta."""
    gravar_agenda(repo, [{"numero": 12, "agendado_para": AGENDADO, "artes": []},
                         {"numero": 13, "agendado_para": "2026-10-07T19:00:00-03:00", "artes": []},
                         {"numero": 14, "agendado_para": "2026-10-20T19:00:00-03:00", "artes": []},
                         {"numero": 11, "agendado_para": "2026-09-29T19:00:00-03:00", "artes": []}])
    r = rodar(repo, MetaFalsa(), dry_run=True)
    # 12 está aprovado; 13 é amanhã e não tem aprovação; 14 está longe; 11 já passou há dias
    assert [(a["semana"], a["numero"]) for a in r["sem_aprovacao"]] == [(SEMANA, 13)]


def test_alerta_some_depois_de_publicado(repo):
    gravar_agenda(repo, [{"numero": 13, "agendado_para": AGENDADO, "artes": []}])
    publicar.registrar(repo, SEMANA, {"numero": 13})
    assert rodar(repo, MetaFalsa(), dry_run=True)["sem_aprovacao"] == []


def test_alerta_sem_aprovacao_json(repo):
    (repo / "content" / "semanas" / SEMANA / "aprovacao.json").unlink()
    gravar_agenda(repo, [{"numero": 12, "agendado_para": AGENDADO, "artes": []}])
    assert [a["numero"] for a in rodar(repo, MetaFalsa(), dry_run=True)["sem_aprovacao"]] == [12]


def test_cli_alerta_sem_aprovacao_retorna_1(repo, monkeypatch, capsys):
    """O job fica vermelho e o GitHub avisa por e-mail: nunca mais um post perdido em silêncio."""
    monkeypatch.delenv("PUBLICAR", raising=False)
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    gravar_agenda(repo, [{"numero": 13, "agendado_para": AGENDADO, "artes": []}])
    assert publicar.main(["--raiz", str(repo), "--agora", DEPOIS.isoformat()]) == 1
    saida = capsys.readouterr().out
    assert "post 13" in saida and "SEM APROVAÇÃO" in saida


# ---------- fila (ADR-015): uma publicação por semana, em ordem de aprovação ----------

PUB_FILA = {"fuso": "America/Sao_Paulo", "dias": [{"dia": "quarta", "hora": "18:00"}], "fila": True}
CONFIG_FILA = {**CONFIG, "publicacao": PUB_FILA}
QUARTA = datetime(2026, 10, 21, 21, 0, 30, tzinfo=timezone.utc)      # quarta 21/10, 18:00:30 em Brasília
TERCA = datetime(2026, 10, 20, 21, 0, 30, tzinfo=timezone.utc)


def aprovacao_fila(*itens_troca, aprovado_em="2026-10-01T10:00:00+00:00"):
    """aprovacao.json com vários posts da fila (agendado_para null) e carimbo por post."""
    posts = []
    for troca in itens_troca:
        item = {"numero": 12, "agendado_para": None,
                "legenda_sha256": sha(publicar.texto_legenda(POST).encode("utf-8")),
                "alt_text_sha256": sha(publicar.texto_alt(POST).encode("utf-8")),
                "artes": [{"arquivo": n, "sha256": sha(b)} for n, b in ARTES.items()]}
        item.update(troca)
        posts.append(item)
    dados = {"semana": SEMANA, "aprovado_por": "Aprovador", "aprovado_em": aprovado_em, "nonce": "n2", "posts": posts}
    dados["assinatura"] = publicar.assinar(dados, SEGREDO)
    return dados


def com_posts(repo, *numeros):
    posts = [dict(POST, numero=n) for n in numeros]
    (repo / "content" / "semanas" / SEMANA / "posts.json").write_text(json.dumps({"posts": posts}), encoding="utf-8")
    midia = repo / "site" / "midia" / SEMANA
    for n in numeros:
        for nome, conteudo in ARTES.items():
            (midia / nome.replace("post-12", f"post-{n}")).write_bytes(conteudo)


def artes_de(n):
    return [{"arquivo": nome.replace("post-12", f"post-{n}"), "sha256": sha(b)} for nome, b in ARTES.items()]


def baixar_qualquer(url):
    """As artes de todos os posts dos testes da fila são cópias das do post 12."""
    return ARTES[re.sub(r"post-\d+", "post-12", url.rsplit("/", 1)[1])]


def rodar_fila(raiz, cliente, agora=QUARTA, dry_run=False):
    return publicar.executar(raiz, CONFIG_FILA, segredo=SEGREDO, agora=agora, cliente=cliente,
                             dry_run=dry_run, baixar=baixar_qualquer)


def test_fila_post_sem_data_sai_na_quarta_depois_das_18h(repo):
    gravar_aprovacao(repo, aprovacao_fila({}))
    meta = MetaFalsa()
    assert [p["numero"] for p in rodar_fila(repo, meta)["publicados"]] == [12]


def test_fila_sem_data_e_fila_desligada_e_recusa_grave(repo):
    gravar_aprovacao(repo, aprovacao_fila({}))
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar(repo, meta)
    assert r["publicados"] == [] and r["recusados"][0]["grave"]


def test_fila_sai_um_so_o_aprovado_ha_mais_tempo(repo):
    com_posts(repo, 12, 13, 14)
    gravar_aprovacao(repo, aprovacao_fila(
        {"numero": 12, "aprovado_em": "2026-10-20T12:00:00+00:00"},
        {"numero": 13, "artes": artes_de(13), "aprovado_em": "2026-10-19T12:00:00+00:00"},
        {"numero": 14, "artes": artes_de(14), "aprovado_em": "2026-10-20T13:00:00+00:00"}))
    meta = MetaFalsa()
    r = rodar_fila(repo, meta)
    assert [p["numero"] for p in r["publicados"]] == [13]
    aguardam = [(d["numero"], d["grave"]) for d in r["recusados"] if "fila" in d["motivo"]]
    assert aguardam == [(12, False), (14, False)]
    # na quinta a semana já está servida: ninguém mais sai
    meta2 = MetaFalsa(proibir_publicar=True)
    quinta = QUARTA + timedelta(days=1)
    assert rodar_fila(repo, meta2, agora=quinta)["publicados"] == []
    # na quarta seguinte sai o próximo da ordem
    meta3 = MetaFalsa()
    assert [p["numero"] for p in rodar_fila(repo, meta3, agora=QUARTA + timedelta(days=7))["publicados"]] == [12]


def test_fila_item_sem_carimbo_usa_o_do_arquivo(repo):
    com_posts(repo, 12, 13)
    dados = aprovacao_fila({"numero": 12}, {"numero": 13, "artes": artes_de(13), "aprovado_em": "2026-10-19T12:00:00+00:00"},
                           aprovado_em="2026-10-10T10:00:00+00:00")
    gravar_aprovacao(repo, dados)
    assert [p["numero"] for p in rodar_fila(repo, MetaFalsa())["publicados"]] == [12]


def test_fila_data_fixa_vencida_sai_antes_da_fila(repo):
    """O post 7 de 2026-W41: data antiga (vencida) mantida para a aprovação continuar válida."""
    com_posts(repo, 12, 13)
    gravar_aprovacao(repo, aprovacao_fila(
        {"numero": 12, "aprovado_em": "2026-10-01T12:00:00+00:00"},
        {"numero": 13, "artes": artes_de(13), "agendado_para": "2026-10-09T19:00:00-03:00",
         "aprovado_em": "2026-10-19T22:03:19+00:00"}))
    meta = MetaFalsa()
    assert [p["numero"] for p in rodar_fila(repo, meta)["publicados"]] == [13]


def test_fila_na_terca_nada_sai_mesmo_com_data_vencida(repo):
    """Post 7 em 19/10: data antiga vencida, aprovado na segunda → não sai na terça, sai na quarta 18h."""
    com_posts(repo, 12)
    gravar_aprovacao(repo, aprovacao_fila({"agendado_para": "2026-10-09T19:00:00-03:00",
                                           "aprovado_em": "2026-10-19T22:03:19+00:00"}))
    meta = MetaFalsa(proibir_publicar=True)
    r = rodar_fila(repo, meta, agora=TERCA)
    assert r["publicados"] == [] and all(not d["grave"] for d in r["recusados"])
    assert [p["numero"] for p in rodar_fila(repo, MetaFalsa())["publicados"]] == [12]


def test_fila_quinta_recupera_a_quarta_que_falhou(repo):
    gravar_aprovacao(repo, aprovacao_fila({"aprovado_em": "2026-10-20T12:00:00+00:00"}))
    assert [p["numero"] for p in rodar_fila(repo, MetaFalsa(), agora=QUARTA + timedelta(days=1))["publicados"]] == [12]


def test_fila_data_fixa_futura_continua_esperando(repo):
    gravar_aprovacao(repo, aprovacao_fila({"agendado_para": "2026-10-28T18:00:00-03:00"}))
    meta = MetaFalsa(proibir_publicar=True)
    assert rodar_fila(repo, meta)["publicados"] == []


def test_fila_dry_run_mostra_so_quem_sairia(repo):
    com_posts(repo, 12, 13)
    gravar_aprovacao(repo, aprovacao_fila(
        {"numero": 12, "aprovado_em": "2026-10-20T12:00:00+00:00"},
        {"numero": 13, "artes": artes_de(13), "aprovado_em": "2026-10-19T12:00:00+00:00"}))
    r = rodar_fila(repo, MetaFalsa(proibir_publicar=True), dry_run=True)
    assert [p["numero"] for p in r["prontos"]] == [13]


def test_fila_alerta_quando_nao_ha_nada_aprovado(repo):
    (repo / "content" / "semanas" / SEMANA / "aprovacao.json").unlink()
    assert "fila vazia" in rodar_fila(repo, MetaFalsa(proibir_publicar=True))["alerta_fila"]
    assert "próxima quarta" in rodar_fila(repo, MetaFalsa(proibir_publicar=True), agora=TERCA)["alerta_fila"]
    gravar_aprovacao(repo, aprovacao_fila({"aprovado_em": "2026-10-19T12:00:00+00:00"}))
    assert rodar_fila(repo, MetaFalsa(proibir_publicar=True), agora=TERCA)["alerta_fila"] is None


def test_fila_cli_alerta_retorna_1(repo, monkeypatch, capsys):
    (repo / "content" / "semanas" / SEMANA / "aprovacao.json").unlink()
    monkeypatch.delenv("PUBLICAR", raising=False)
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    cfg = repo / "config.yaml"
    cfg.write_text("publicacao:\n  fuso: America/Sao_Paulo\n  fila: true\n  dias:\n    - {dia: quarta, hora: '18:00'}\n"
                   "midia: {base_url: https://exemplo.github.io/repo/, pasta: site/midia}\nmeta: {}\n", encoding="utf-8")
    assert publicar.main(["--raiz", str(repo), "--config", str(cfg), "--agora", QUARTA.isoformat()]) == 1
    assert "fila vazia" in capsys.readouterr().out
