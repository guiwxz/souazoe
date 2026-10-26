"""Tira a foto da Frida do print do post de Facebook (perdidos/frida.jpeg, 600x790) para o frida.html.

O print é de um grupo de achados e perdidos, cortado só no post da família (sem os posts vizinhos do grupo):
"Sumiu a pouco na vila Jardim. Atende por Frida..." com a foto dela deitada, enrolada num sofá com manta
estampada, de peitoral azul (x 0-600, y ~175-725).
No canto de baixo à esquerda, por cima da manta, o Facebook pôs o avatar de quem curtiu (x ~15-75, y ~650-710).
A foto sai sem esse canto e sem a interface: ela inteira, centrada, com um pouco de manta em volta.
Só recorte, sem retoque nem ampliação (o template amplia um pouco no navegador, como no caso Bidi).

Saída: img/frida.png (PNG para não passar por outra compressão JPEG)
Uso: python3 templates/desaparecidos/foto_frida.py  (só precisa do Pillow)
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

FOTO = (80, 235, 540, 705)  # à direita do avatar do Facebook; ela vai de x ~97 a 450 e de y ~337 a 630


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    foto = Image.open(ROOT / "perdidos" / "frida.jpeg").convert("RGB").crop(FOTO)
    foto.save(IMG / "frida.png")
    print(IMG / "frida.png", foto.size)


if __name__ == "__main__":
    main()
