"""Prepara a foto da shih tzu encontrada na São José para o encontrada-sao-jose.html.

A imagem recebida (perdidos/sao-jose.jpeg, 1080x1440) é a foto que veio por direct: ela deitada de lado
num sofá cinza, sobre uma manta rosa, com o braço de quem a acolheu em cima e uma perna de calça jeans à esquerda.

A foto sai num corte horizontal, do alto da cabeça às patas, abaixo do braço (que termina em y ~480).
O rabo já vem cortado na borda direita da foto original. Só recorte, sem retoque.

Saída: img/sao-jose.jpg
Uso: python3 templates/desaparecidos/foto_sao_jose.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (125, 478, 1080, 1040)    # ela inteira, com a manta embaixo e sem o braço em cima


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "sao-jose.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "sao-jose.jpg", quality=93)
    print(IMG / "sao-jose.jpg", foto.size)


if __name__ == "__main__":
    main()
