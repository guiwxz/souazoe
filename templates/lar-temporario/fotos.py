"""Fotos dos 6 lares temporários (drive/lares temporários/<Nome> - N.jpg) → img/<n>.jpg, quadradas, 1080 px.

- Theodor: o recorte deixa de fora o pé de chinelo no canto de baixo.
- Heitor: o fundo (parede com a logo de um pet shop) é desfocado com uma máscara do rembg; o cão fica intacto.
Nada é reconstruído: só recorte, redimensionamento e o desfoque do fundo.

Uso (venv com pillow, rembg[cpu] e opencv-python-headless):
    python templates/lar-temporario/fotos.py
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / 'drive' / 'lares temporários'
OUT = Path(__file__).resolve().parent / 'img'

# arquivo, (x, y, lado) do quadrado no original
CORTES = {
    1: ('Theodor - 1.jpg', (500, 1050, 1750)),
    2: ('Rocco - 2.jpg', (0, 330, 1200)),
    3: ('Heitor - 3.jpg', (0, 280, 1200)),
    4: ('Camélia - 4.jpg', (0, 130, 960)),
    5: ('Mocca - 5.JPG', (0, 40, 720)),
    6: ('Mia -6.JPG', (0, 1000, 2160)),
}


def heitor_sem_logo(im):
    from rembg import new_session, remove
    mask = remove(im, session=new_session('u2net'), only_mask=True)
    mask = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6))  # folga na borda do pelo
    fundo = im.filter(ImageFilter.GaussianBlur(38))
    return Image.composite(im, fundo, mask)


for n, (nome, (x, y, lado)) in CORTES.items():
    im = ImageOps.exif_transpose(Image.open(SRC / nome)).convert("RGB")
    if n == 3:
        im = heitor_sem_logo(im)
    im = im.crop((x, y, x + lado, y + lado)).resize((1080, 1080), Image.LANCZOS)
    im.save(OUT / f'{n}.jpg', quality=90)
    print(OUT / f'{n}.jpg')
