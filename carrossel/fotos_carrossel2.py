"""Fotos do carrossel 2 ("Antes de eu sumir, eu fui encontrada") → carrossel/img/carrossel2/.

Fontes: drive/dia da adoção/, drive/Luma/ e as fotos atuais da Zoe já em carrossel/img/.
Só redimensiona (lado maior 1600 px); o enquadramento fica no object-position do carrossel2.html.
A primeira foto em família (HEIC) precisa estar convertida antes para .jpg (pillow-heif).

Uso: python carrossel/fotos_carrossel2.py
"""
from pathlib import Path
from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
AD = RAIZ / 'drive' / 'dia da adoção'
OUT = RAIZ / 'carrossel' / 'img' / 'carrossel2'

FOTOS = {
    'resgate.jpg': AD / 'foto envida por quem havia resgatado ela.JPG',
    'pelucia.jpg': AD / 'a99a091c-77cd-4b06-8d1a-8e6c11ec7ec9.JPG',
    'luma.jpg': RAIZ / 'drive' / 'Luma' / '20161010_070640.jpg',
    'dormindo.jpg': AD / 'A291B271-3F94-488F-9127-F9F2481E79ED.JPG',
    'vacina.jpg': AD / 'primeira_vacina.JPG',
    'natal.jpg': AD / 'primeira_foto_em_familia_natal_2024.jpg',
}
for nome, src in FOTOS.items():
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    im.save(OUT / nome, quality=90)
    print(OUT / nome, im.size)
