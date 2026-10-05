"""Prepara a foto da Bola (perdidos/bola.jpeg) para o template de desaparecidos (bola.html).

A imagem recebida é o print de um Story, com a foto original da Bola no meio (688x521 px). A foto é
mantida como está (sem recorte nem troca de fundo): só a sirene vermelha da arte, colada por cima do
piso ao lado da pata, é apagada (inpaint no piso). Depois ela é ampliada 4x com o EDSR (super-resolução
do OpenCV, fiel à foto: não inventa textura) e reduzida para 1080 px de largura.

Saída: img/bola.jpg (1080 px de largura).

Precisa de opencv-contrib num venv temporário (não está instalado globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install opencv-contrib-python-headless pillow
  /tmp/venv/bin/python templates/desaparecidos/foto_bola.py
O modelo EDSR_x4.pb (38 MB) é baixado na primeira execução para ~/.cache/edsr/ (fora do projeto).
"""
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "perdidos" / "bola.jpeg"
OUT = Path(__file__).resolve().parent / "img" / "bola.jpg"
MODEL = Path.home() / ".cache" / "edsr" / "EDSR_x4.pb"
MODEL_URL = "https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x4.pb"

FOTO = (16, 480, 704, 1001)       # foto original dentro do print (sem o texto de cima e o "URGENTE")
SIRENE = (118, 880, 262, 1001)    # sirene vermelha colada sobre o piso (com os raios e a base preta)


def main():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    arte = np.array(Image.open(SRC).convert("RGB"))
    # recorta antes do inpaint, para ele não puxar cor do "URGENTE" vermelho logo abaixo da foto
    foto = np.ascontiguousarray(arte[FOTO[1]:FOTO[3], FOTO[0]:FOTO[2]])

    # sirene: vermelho (inclusive o mais escuro da base do giroflex) + a base preta, só dentro da caixa
    x0, y0, x1, y1 = (SIRENE[0] - FOTO[0], SIRENE[1] - FOTO[1], SIRENE[2] - FOTO[0], SIRENE[3] - FOTO[1])
    r, g, b = (foto[y0:y1, x0:x1, i].astype(int) for i in range(3))
    vermelho = (r > 90) & (r > 1.6 * g) & (r > 1.6 * b)
    base = (r + g + b < 180) & (np.arange(SIRENE[1], SIRENE[3])[:, None] > 985)
    mask = np.zeros(foto.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = ((vermelho | base) * 255).astype(np.uint8)
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    foto = cv2.inpaint(foto, mask, 7, cv2.INPAINT_TELEA)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(MODEL))
    sr.setModel("edsr", 4)
    grande = sr.upsample(np.ascontiguousarray(foto[..., ::-1]))[..., ::-1]   # o OpenCV trabalha em BGR

    im = Image.fromarray(grande)
    im = im.resize((1080, round(im.height * 1080 / im.width)), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, quality=93)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
