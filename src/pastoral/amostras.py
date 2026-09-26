"""Amostras para o Diogo (ADR-007): post comum em fundo creme e folhas-contato.

- `content/estreia/amostras/post-comum-creme-01..07.jpg`: o post 2 do pacote renderizado como post comum
  (sem `fixado`/`importante`), sem alterar o post 2 real, que continua fixado e vermelho.
- `comparativo.jpg`: capa fixada (vermelha) × capa comum (creme) e conteúdo prata × conteúdo creme.
- `destaques.jpg`: as 5 capas de destaque em círculos, como aparecem no perfil (fundo branco, rótulo abaixo).

Uso: python -m pastoral.amostras  (depois de `python -m pastoral.render ... --destaques`)
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from pastoral.render import DESTAQUES, RAIZ, Renderizador

ESTREIA = RAIZ / "content" / "estreia"
FONTE = RAIZ / "assets/fonts/source-sans-3/SourceSans3-wght.ttf"


def como_post_comum(post: dict) -> dict:
    """Cópia do post sem as marcas `fixado`/`importante` (→ tema creme). O original não muda."""
    comum = copy.deepcopy(post)
    comum.pop("fixado", None)
    comum.pop("importante", None)
    return comum


def _fonte(tamanho: int, peso: str = "Regular") -> ImageFont.FreeTypeFont:
    try:
        fonte = ImageFont.truetype(str(FONTE), tamanho)
    except OSError:
        return ImageFont.load_default()
    try:
        fonte.set_variation_by_name(peso)            # fonte variável: sem isso sai no peso mais fino
    except (OSError, ValueError):
        pass
    return fonte


def _salvar(img: Image.Image, destino: Path) -> None:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(destino, "JPEG", quality=90, subsampling=0, optimize=True)


def folha_comparativo(capa_fixada: Path, capa_comum: Path, conteudo_prata: Path, conteudo_creme: Path,
                      destino: Path, largura: int = 540) -> None:
    """Grade 2×2 com rótulos: à esquerda o post fixado (vermelho/prata), à direita o comum (creme)."""
    altura = largura * 1350 // 1080
    margem, topo, rotulo = 40, 90, 50
    W = margem * 3 + largura * 2
    H = topo + (rotulo + altura + margem) * 2
    folha = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(folha)
    d.text((margem, 28), "Post fixado ou importante", fill="#1E1B1B", font=_fonte(34, "SemiBold"))
    d.text((margem * 2 + largura, 28), "Post comum da semana", fill="#1E1B1B", font=_fonte(34, "SemiBold"))
    linhas = [("Capa", capa_fixada, capa_comum), ("Conteúdo", conteudo_prata, conteudo_creme)]
    for k, (nome, esq, dir_) in enumerate(linhas):
        y = topo + k * (rotulo + altura + margem)
        for j, (arq, legenda) in enumerate([(esq, "vermelho profundo" if k == 0 else "prata"), (dir_, "creme")]):
            x = margem + j * (largura + margem)
            d.text((x, y + 8), f"{nome} · fundo {legenda}", fill="#5F5A57", font=_fonte(26))
            with Image.open(arq) as img:
                folha.paste(img.convert("RGB").resize((largura, altura), Image.LANCZOS), (x, y + rotulo))
    _salvar(folha, destino)


def folha_destaques(capas: list[tuple[str, Path]], destino: Path, diametro: int = 200) -> None:
    """Capas de destaque (1080×1920) recortadas no círculo central, lado a lado, com o nome abaixo."""
    esc = 2                                          # desenha em 2× e reduz: bordas suaves
    D, gap, margem, rotulo = diametro * esc, 48 * esc, 48 * esc, 60 * esc
    W = margem * 2 + len(capas) * D + (len(capas) - 1) * gap
    H = margem * 2 + D + rotulo
    folha = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(folha)
    fonte = _fonte(26 * esc)
    anel = 6 * esc                                   # anel cinza claro, como no app
    for i, (nome, arq) in enumerate(capas):
        x = margem + i * (D + gap)
        with Image.open(arq) as img:
            img = img.convert("RGB")
            lado = min(img.size)
            topo = (img.height - lado) // 2
            quadrado = img.crop((0, topo, lado, topo + lado))
        interno = D - 2 * anel
        miolo = quadrado.resize((interno, interno), Image.LANCZOS)
        mascara = Image.new("L", (interno, interno), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, interno - 1, interno - 1), fill=255)
        d.ellipse((x, margem, x + D - 1, margem + D - 1), outline="#DBDBDB", width=2 * esc)
        folha.paste(miolo, (x + anel, margem + anel), mascara)
        largura_txt = d.textlength(nome, font=fonte)
        d.text((x + (D - largura_txt) / 2, margem + D + 16 * esc), nome, fill="#262626", font=fonte)
    folha = folha.resize((W // esc, H // esc), Image.LANCZOS)
    _salvar(folha, destino)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Amostras do post comum em creme e folhas-contato (ADR-007)")
    ap.add_argument("--posts", type=Path, default=ESTREIA / "posts.json")
    ap.add_argument("--numero", type=int, default=2, help="post do pacote usado como amostra")
    ap.add_argument("--render", type=Path, default=ESTREIA / "render")
    ap.add_argument("--saida", type=Path, default=ESTREIA / "amostras")
    args = ap.parse_args(argv)

    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    dados = json.loads(args.posts.read_text(encoding="utf-8"))
    post = next(p for p in dados["posts"] if p["numero"] == args.numero)
    prefixo = "post-comum-creme"
    with Renderizador() as r:
        qa = r.renderizar_post(como_post_comum(post), args.saida, config, prefixo=prefixo)
    n = args.numero
    # 2º slide do post = 1º slide de conteúdo
    folha_comparativo(args.render / f"post-{n}-01.jpg", args.saida / f"{prefixo}-01.jpg",
                      args.render / f"post-{n}-02.jpg", args.saida / f"{prefixo}-02.jpg",
                      args.saida / "comparativo.jpg")
    folha_destaques([(d["nome"], args.render / f"destaque-{d['arquivo']}.jpg") for d in DESTAQUES],
                    args.saida / "destaques.jpg")
    reprovadas = [q["arquivo"] for q in qa if not q["ok"]]
    (args.saida / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(qa)} slides em creme + comparativo.jpg + destaques.jpg em {args.saida}; "
          f"reprovadas: {reprovadas or 'nenhuma'}")
    return 1 if reprovadas else 0


if __name__ == "__main__":
    sys.exit(main())
