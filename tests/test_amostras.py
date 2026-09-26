"""ADR-007 — amostras do post comum em creme e folhas-contato (comparativo e destaques)."""
from PIL import Image

from pastoral import amostras, render


def _jpg(caminho, cor, tamanho=(1080, 1350)):
    Image.new("RGB", tamanho, cor).save(caminho, "JPEG")
    return caminho


def test_post_em_modo_creme_nao_altera_o_original():
    post = {"numero": 2, "fixado": True, "slides": [{"template": "capa", "titulo": "T"}]}
    comum = amostras.como_post_comum(post)
    assert render.tema_do_post(comum) == "creme"
    assert post["fixado"] is True and comum["slides"] == post["slides"]


def test_folha_comparativo_2x2(tmp_path):
    a = [_jpg(tmp_path / f"{n}.jpg", c) for n, c in
         [("cv", "#7E0F17"), ("cc", "#F2E8D5"), ("pp", "#F3F2EE"), ("pc", "#F2E8D5")]]
    destino = tmp_path / "comparativo.jpg"
    amostras.folha_comparativo(a[0], a[1], a[2], a[3], destino)
    img = Image.open(destino)
    assert img.format == "JPEG" and img.width > img.height * 0.6
    # a capa fixada (vermelha) fica à esquerda, em cima
    r, g, b = img.getpixel((img.width // 4, img.height // 3))
    assert r > 100 and g < 40


def test_folha_destaques_circulos_com_rotulo(tmp_path):
    capas = [(d["nome"], _jpg(tmp_path / f"{d['arquivo']}.jpg", "#F3F2EE", (1080, 1920))) for d in render.DESTAQUES]
    destino = tmp_path / "destaques.jpg"
    amostras.folha_destaques(capas, destino, diametro=200)
    img = Image.open(destino).convert("RGB")
    assert img.width >= 5 * 200
    assert img.getpixel((2, 2)) == (255, 255, 255)          # fundo branco do perfil
