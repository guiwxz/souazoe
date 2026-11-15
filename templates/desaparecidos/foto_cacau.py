"""Tira a foto da Cacau do print do alerta (perdidos/cacau.jpeg, 1080x2340) para o cacau.html.

O print é de um Story: a foto original ocupa a largura toda (y 156-1374) e o texto do alerta, numa caixa
preta, começa logo abaixo, cortando as patas. Aqui sai só um recorte da foto em volta dela (cabeça, lenço,
laço e patas até a caixa de texto), sem retoque: as patinhas rosa na cabeça ficam como estão na foto.
Salva em PNG para não passar por outra compressão JPEG.

Saída: img/cacau.png (860x1072, proporção 4:5).
Uso: python3 templates/desaparecidos/foto_cacau.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (150, 300, 1010, 1372)  # da altura do encosto do banco até 2 px antes da caixa de texto


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "cacau.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "cacau.png")
    print(IMG / "cacau.png", foto.size)


if __name__ == "__main__":
    main()
