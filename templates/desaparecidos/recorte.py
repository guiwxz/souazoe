"""Recorta Garibaldi e Masha da arte original (perdidos/garibaldi.jpeg) para o template.

A arte recebida já traz os cães recortados sobre um fundo bege, mas com as etiquetas laranjas e as
setas por cima. Antes do recorte, a seta sobre o pelo do Garibaldi é coberta com um remendo de pelo
vizinho, a seta da Masha (sobre o fundo) é apagada e cada etiqueta é coberta com o que está logo acima
dela (pelo sobre o corpo, fundo sobre o fundo). Depois o rembg (isnet-general-use) separa os cães.
A faixa vai até onde começa o painel do contato na arte, para mostrar os cães o máximo possível.

Saída: img/garibaldi-masha.png, a faixa BAND da arte em 2x (o index.html posiciona pela arte original).

Precisa de rembg + opencv num venv temporário (não estão instalados globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install "rembg[cpu]" opencv-python-headless
  /tmp/venv/bin/python templates/desaparecidos/recorte.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "perdidos" / "garibaldi.jpeg"
OUT = Path(__file__).resolve().parent / "img" / "garibaldi-masha.png"

BAND = (0, 440, 1145, 1092)       # faixa dos cães na arte: do título até o painel do contato
ARROW = (178, 770, 268, 856)      # seta do "Garibaldi", sobre o pelo
PATCH = (-30, -60)                # de onde vem o pelo que cobre a seta (deslocamento em px)
ARROW2 = (1000, 878, 1045, 952)   # seta da "Masha", sobre o fundo (a partir de 1000 para não pegar o pelo dela)
LABEL_G = (30, 845, 360, 985)     # etiqueta "Garibaldi"
EDGE_G = 150                      # à esquerda disso a etiqueta cobre o fundo; à direita, o flanco do Garibaldi
PELO_G = (170, 60)                # remendo do flanco: pelo do peito, à direita (abaixo da fivela, antes da guia)
LABEL_M = (870, 935, 1105, 1062)  # etiqueta "Masha": sobre pelo preto e fundo liso, o inpaint basta
BG = (237, 220, 204)              # bege do fundo da arte
PEITO = (530, 780, 660, 1092)     # peito do Garibaldi ao lado da Masha: o rembg deixa semitransparente
FADE = (1050, 1090)               # base do recorte some, já sob o degradê do template


def remenda(rgb, mask, desloc, igualar=True, borda=2.5):
    """Cobre a máscara com a imagem deslocada, com borda suave (e a cor igualada à do entorno)."""
    liso = cv2.inpaint(rgb, mask, 7, cv2.INPAINT_TELEA).astype(np.float32)  # sem o elemento, mas sem textura
    dx, dy = desloc
    remendo = np.roll(liso, (-dy, -dx), axis=(0, 1))
    if igualar:
        ring = cv2.dilate(mask, np.ones((15, 15), np.uint8)) & ~mask
        remendo += liso[ring > 0].mean(0) - remendo[ring > 0].mean(0)
    m = cv2.GaussianBlur(mask, (0, 0), borda).astype(np.float32)[..., None] / 255
    return (liso * (1 - m) + remendo * m).clip(0, 255).astype(np.uint8)


def mascara_escura(rgb, box):
    """Traço escuro (seta) dentro da caixa."""
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    x0, y0, x1, y1 = box
    mask = np.zeros(lum.shape, np.uint8)
    mask[y0:y1, x0:x1] = (lum[y0:y1, x0:x1] < 120).astype(np.uint8) * 255
    return cv2.dilate(mask, np.ones((9, 9), np.uint8))


def mascara_etiqueta(rgb, box):
    """Laranja da etiqueta (bem mais saturado que o pelo) + o texto dentro dela."""
    x0, y0, x1, y1 = box
    r, g, b = (rgb[y0:y1, x0:x1, i].astype(int) for i in range(3))
    laranja = ((r > 200) & (b < 90) & (r - b > 130)).astype(np.uint8) * 255
    casco = cv2.morphologyEx(laranja, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    mask = np.zeros(rgb.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = cv2.dilate(casco, np.ones((7, 7), np.uint8))
    return mask


def main():
    arte = np.array(Image.open(SRC).convert("RGB"))
    arte = remenda(arte, mascara_escura(arte, ARROW), PATCH)
    seta2 = mascara_escura(arte, ARROW2)
    arte = cv2.inpaint(arte, seta2, 7, cv2.INPAINT_TELEA)       # sobre o fundo liso, basta o inpaint

    etq = mascara_etiqueta(arte, LABEL_G)
    flanco = etq.copy()
    flanco[:, :EDGE_G] = 0
    arte = remenda(arte, flanco, PELO_G, borda=8)
    arte = cv2.inpaint(arte, etq - flanco, 7, cv2.INPAINT_TELEA)  # parte sobre o fundo
    arte = cv2.inpaint(arte, mascara_etiqueta(arte, LABEL_M), 9, cv2.INPAINT_TELEA)

    x0, y0, x1, y1 = BAND
    cut = np.array(remove(Image.fromarray(arte[y0:y1, x0:x1]), session=new_session("isnet-general-use")))

    # alfa mais firme (some a névoa semitransparente) e 1 px para dentro
    # (tira o halo claro que o recorte da arte original deixou na borda)
    a = cut[..., 3].astype(np.float32)
    a = cv2.erode(np.clip((a - 60) / 140, 0, 1), np.ones((3, 3), np.uint8))
    a[seta2[y0:y1, x0:x1] > 0] = 0
    a[(etq - flanco)[y0:y1, x0:x1] > 0] = 0                      # etiqueta sobre o fundo

    # peito do Garibaldi: o que não é bege do fundo é cachorro
    px0, py0, px1, py1 = PEITO
    reg = cut[py0 - y0:py1 - y0, px0 - x0:px1 - x0, :3].astype(np.float32)
    dist = np.linalg.norm(reg - np.array(BG, np.float32), axis=2)
    sub = a[py0 - y0:py1 - y0, px0 - x0:px1 - x0]
    np.maximum(sub, np.clip((dist - 35) / 25, 0, 1), out=sub)

    # fade na base (encontro com o painel da arte)
    ys = np.arange(cut.shape[0])[:, None] + y0
    a *= np.clip((FADE[1] - ys) / (FADE[1] - FADE[0]), 0, 1)
    cut[..., 3] = (a * 255).astype(np.uint8)

    # 2x: o template amplia ~1,4x, então o Chrome só reduz
    im = Image.fromarray(cut, "RGBA")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
