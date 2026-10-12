"""Tira a foto do Bidi da arte recebida (perdidos/bidi.jpeg, 720x1280) para o bidi.html.

A arte é um cartaz "ATENÇÃO / DESAPARECIDO" com a foto numa moldura azul de cantos arredondados
(x 126-594, y 430-952). Aqui sai só o miolo da moldura, sem a borda azul. Só recorte, sem retoque:
nada de recorte do fundo, ampliação ou limpeza. A foto é a original, a mesma no feed e no Story,
e é salva em PNG para não passar por outra compressão JPEG.

Saída: img/bidi.png (450x504).
Uso: python3 templates/desaparecidos/foto_bidi.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (135, 439, 585, 943)  # dentro da moldura azul, 2 px para dentro da borda


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "bidi.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "bidi.png")
    print(IMG / "bidi.png", foto.size)


if __name__ == "__main__":
    main()
