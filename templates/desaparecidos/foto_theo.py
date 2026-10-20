"""Tira a foto do Theo da foto original recebida (perdidos/theo-2.jpeg, 1079x1439) para o theo.html.

A arte "PROCURA-SE / THEO" (perdidos/theo-1.jpeg) usa essa mesma foto, recortada mais justa (só o sofá,
o Theo e o tapete) e ampliada, com zigue-zagues por cima. Aqui sai o mesmo enquadramento da arte, só que
da foto original, que está limpa: a foto da arte (x 165-894, y 344-1096) bate com a original na escala 0,835
(correlação de 0,99), o que dá o retângulo abaixo. Só recorte, sem retoque nem ampliação. Fica de fora o
resto do piso e o selo da PataVida no canto. Salva em PNG para não passar por outra compressão JPEG.

Saída: img/theo.png (609x628).
Uso: python3 templates/desaparecidos/foto_theo.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (347, 293, 956, 921)  # o enquadramento da arte, na foto original


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "theo-2.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "theo.png")
    print(IMG / "theo.png", foto.size)


if __name__ == "__main__":
    main()
