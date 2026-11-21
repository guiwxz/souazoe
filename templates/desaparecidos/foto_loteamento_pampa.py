"""Prepara a foto da cachorra encontrada perto do Loteamento Pampa para o encontrada-loteamento-pampa.html.

As imagens recebidas (perdidos/loteamento-pampa-1.png e -2.png, 1170x2532) são prints do post
"PROCURA-SE O TUTOR!" do @adoteumcachorrinhopf (as fotos 1/2 e 2/2 do carrossel).
Usa a 2/2 (ela de corpo inteiro, de pé, no sol, com a mancha caramelo da cabeça e a coleira com o pingente):
sai só a foto do post, sem a interface do Instagram, cortada logo abaixo do selo "2/2" (que fica no asfalto,
longe dela). Só recorte, sem retoque.

Saída: img/loteamento-pampa.jpg
Uso: python3 templates/desaparecidos/foto_loteamento_pampa.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (20, 405, 1170, 1430)    # da ponta do rabo às patas com a sombra, sem o selo "2/2" nem a interface


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "loteamento-pampa-2.png").convert("RGB").crop(FOTO)
    foto.save(IMG / "loteamento-pampa.jpg", quality=93)
    print(IMG / "loteamento-pampa.jpg", foto.size)


if __name__ == "__main__":
    main()
