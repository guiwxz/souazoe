"""Tira a foto da Layde da arte recebida (perdidos/layde.jpeg, 1170x2080) para o layde.html.

A arte é um cartaz "CÃO PERDIDO / RECOMPENSA-SE" com a foto grande à esquerda, entre a faixa vermelha
de cima e o pincel amarelo de baixo (x 32-644, y 477-1384; a borda de baixo desce um pouco para a
esquerda). Aqui sai só a foto, 1 px para dentro das bordas. Só recorte, sem retoque: nada de
recorte do fundo, ampliação ou limpeza. A segunda foto da arte (o quadrinho à direita) fica de fora:
uma segunda foto vai num Story separado, nunca na mesma arte.

Saída: img/layde.png (611x904), em PNG para não passar por outra compressão JPEG.
Uso: python3 templates/desaparecidos/foto_layde.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (33, 478, 644, 1382)  # entre a moldura vermelha, a faixa branca da direita e o pincel amarelo


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "layde.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "layde.png")
    print(IMG / "layde.png", foto.size)


if __name__ == "__main__":
    main()
