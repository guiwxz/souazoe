"""Recorta a Zoe da foto da creche (IMG_7200: print de um Story, ela olhando para cima de boca aberta)
para a etiqueta dos saquinhos de petisco (index.html).

O print tem 1170x2532; o recorte pega da ponta do rabo (que aparece atrás da cabeça) até o peito,
sem a interface do Instagram em cima e sem o outro cachorro na borda esquerda. O rembg
(isnet-general-use) separa a Zoe da grama sintética; fica só o maior pedaço (sobras do cachorro branco
e da grama somem) e a borda recebe a mesma limpeza do recorte do Thor (cor do pelo de dentro no lugar
do verde que vaza no contorno).

Saída: img/zoe-creche.png (RGBA, cortado rente à Zoe; o peito termina reto embaixo, na borda da etiqueta).

Precisa de rembg + opencv num venv temporário (não estão instalados globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install "rembg[cpu]" opencv-python-headless
  /tmp/venv/bin/python templates/etiqueta/recorte.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "drive" / "instagram" / "apresentação␠" / "IMG_7200.PNG"
if not SRC.exists():  # no Linux/macOS o rclone grava o espaço final do nome da pasta como espaço mesmo
    SRC = ROOT / "drive" / "instagram" / "apresentação " / "IMG_7200.PNG"
OUT = Path(__file__).resolve().parent / "img" / "zoe-creche.png"

FOTO = (228, 330, 1150, 1600)     # do rabo às patas da frente, sem o cachorro branco à esquerda


def main():
    foto = Image.open(SRC).convert("RGB").crop(FOTO)
    cut = np.array(remove(foto, session=new_session("isnet-general-use")))

    # alfa mais firme, sem a grama que o rembg deixa entre as patas (o pelo da Zoe nunca puxa pro verde),
    # só o maior pedaço, ~1 px para dentro e borda suave
    a = cut[..., 3].astype(np.float32)
    a = np.clip((a - 60) / 140, 0, 1)
    rgb = cut[..., :3].astype(np.float32)
    verde = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    a *= 1 - np.clip((verde - 14) / 10, 0, 1)
    n, rot, stats, _ = cv2.connectedComponentsWithStats((a > .5).astype(np.uint8))
    maior = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    a *= cv2.dilate((rot == maior).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    a = cv2.GaussianBlur(a, (0, 0), 1.2)

    # na parte semitransparente da borda, a cor vem do pelo de dentro (não do verde da grama)
    miolo = (a > .99).astype(np.float32)
    rgb = cut[..., :3].astype(np.float32)
    soma = cv2.GaussianBlur(rgb * miolo[..., None], (0, 0), 6)
    peso = cv2.GaussianBlur(miolo, (0, 0), 6)[..., None]
    preenche = soma / np.maximum(peso, 1e-4)
    borda = ((a > 0) & (miolo == 0))[..., None]
    rgb = np.where(borda, preenche, rgb)

    # reflexo verde da grama no pelo junto ao contorno: tira o excesso de verde nos primeiros 14 px
    dist = cv2.distanceTransform((a > .5).astype(np.uint8), cv2.DIST_L2, 5)
    perto = np.clip(1 - dist / 14, 0, 1)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    excesso = np.clip(g - np.maximum(r, b), 0, None) * perto
    rgb[..., 1] = g - excesso

    cut[..., :3] = rgb.clip(0, 255).astype(np.uint8)
    cut[..., 3] = (a * 255).astype(np.uint8)

    im = Image.fromarray(cut, "RGBA")
    im = im.crop(im.getbbox())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
