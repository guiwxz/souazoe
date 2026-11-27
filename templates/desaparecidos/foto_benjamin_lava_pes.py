"""Prepara a foto do cachorro visto solto na esquina da Benjamin Constant com a Lava-Pés para o perdido-benjamin-lava-pes.html.

A imagem recebida (perdidos/benjamin-lava-pes.jpeg, 900x1600) é uma foto da rua: o cachorro branco, de coleira escura,
aparece pequeno, atrás de uma pilha de madeira na frente de uma obra. A foto sai num recorte horizontal em volta dele,
com a obra para dar o lugar, ampliada 2x (Lanczos) para a polaroide. Só recorte e ampliação, sem retoque: as patas
ficam atrás da madeira, como na foto (nada reconstruído).

Saída: img/benjamin-lava-pes.jpg
Uso: python3 templates/desaparecidos/foto_benjamin_lava_pes.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (250, 580, 700, 880)   # o cachorro com a madeira e os pilares da obra em volta


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "benjamin-lava-pes.jpeg").convert("RGB").crop(FOTO)
    foto = foto.resize((foto.width * 2, foto.height * 2), Image.LANCZOS)
    foto.save(IMG / "benjamin-lava-pes.jpg", quality=93)
    print(IMG / "benjamin-lava-pes.jpg", foto.size)


if __name__ == "__main__":
    main()
