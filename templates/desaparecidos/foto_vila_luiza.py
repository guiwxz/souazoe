"""Prepara as fotos do cachorro encontrado na Vila Luiza para o encontrado-vila-luiza.html.

As imagens recebidas são três prints (1080x2340) de um Story que repostou o post do @cademeupetpf_:
  perdidos/vila-luiza-1.jpeg  a arte "PERDIDO(A) / VOCÊ ME CONHECE?" com os dados (macho, olho branco, local)
  perdidos/vila-luiza-2.jpeg  ele em pé na grama, de lado: é onde o olho branco aparece melhor
  perdidos/vila-luiza-3.jpeg  ele sentado, de frente (a mesma foto da arte, maior)

A foto principal sai do print 3, cortada antes do "3/3" e dos ícones do Instagram (curtir, comentar...)
que ficam por cima do piso, à direita. O detalhe do olho branco sai do print 2. Só recorte, sem retoque:
as fotos já têm mais resolução do que o template usa.

Saída: img/vila-luiza.jpg (foto principal) e img/vila-luiza-olho.jpg (detalhe quadrado do olho).
Uso: python3 templates/desaparecidos/foto_vila_luiza.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (35, 398, 936, 1498)      # print 3: das orelhas às patas, à esquerda dos ícones (x >= 965)
OLHO = (740, 870, 940, 1070)     # print 2: o olho esquerdo dele (o branco), com o pelo em volta


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "vila-luiza-3.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "vila-luiza.jpg", quality=93)
    olho = Image.open(ROOT / "perdidos" / "vila-luiza-2.jpeg").convert("RGB").crop(OLHO)
    olho.save(IMG / "vila-luiza-olho.jpg", quality=93)
    print(IMG / "vila-luiza.jpg", foto.size, IMG / "vila-luiza-olho.jpg", olho.size)


if __name__ == "__main__":
    main()
