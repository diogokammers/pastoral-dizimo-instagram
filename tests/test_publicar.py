"""Fatia 7 — portão de publicação (arquitetura §5 e §6). Cliente da Meta sempre falso.

Regra de ouro: em qualquer caso negativo, `media_publish` NÃO pode ser chamado.
"""
import hashlib
import json
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
    assert publicar.main(["--raiz", str(repo), "--agora", DEPOIS.isoformat()]) == 0
    assert "[ok]" in capsys.readouterr().out


def test_sem_semanas_nao_falha(tmp_path, monkeypatch):
    monkeypatch.setenv("APROVACAO_HMAC_SECRET", SEGREDO)
    assert publicar.main(["--raiz", str(tmp_path)]) == 0


def test_url_publica():
    assert publicar.url_publica("https://a.io/r/", "2026-W41", "post-1-01.jpg") == \
        "https://a.io/r/midia/2026-W41/post-1-01.jpg"
    assert publicar.url_publica("https://a.io/r", "2026-W41", "x.jpg") == "https://a.io/r/midia/2026-W41/x.jpg"
