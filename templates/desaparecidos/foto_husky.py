"""Tira a foto da husky do print do Story recebido (perdidos/husky.jpeg, 1080x2340) para o husky.html.

O Story tem a foto dela deitada, com duas caixas de texto pretas por cima: "Ontem depois do fogos de artifício
ela sumiu aqui de casa" (y ~378-530, sobre a parede) e "Favor quem souber ou encontrou nos ajude compartilhando"
(y ~1585-1875, sobre as patas da frente). A foto sai do miolo entre as duas caixas: das orelhas ao peito,
com a bandana. As patas ficam de fora porque estão atrás da caixa de baixo e não se reconstrói o que está
escondido. Só recorte, sem retoque nem ampliação (960 px de largura, mais do que o template usa).

Saída: img/husky.jpg
Uso: python3 templates/desaparecidos/foto_husky.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (80, 600, 1040, 1572)  # abaixo da caixa de cima e 13 px acima da de baixo, com ela no centro


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "husky.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "husky.jpg", quality=95)
    print(IMG / "husky.jpg", foto.size)


if __name__ == "__main__":
    main()
