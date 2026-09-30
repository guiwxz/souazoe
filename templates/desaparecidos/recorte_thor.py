"""Recorta o Thor da arte recebida (perdidos/thor.jpeg) para o template de desaparecidos (thor.html).

A arte tem 722 px de largura e traz três fotos; a usada é a maior (o Thor em pé, de corpo inteiro),
que tem só 371x550 px. Ela é ampliada 4x com o EDSR (super-resolução do OpenCV, fiel à foto: não
inventa textura como os modelos GAN) e o rembg (isnet-general-use) separa o cachorro da grama.

Saída: img/thor.png (RGBA, cortado rente ao cachorro).

Precisa de rembg + opencv-contrib num venv temporário (não estão instalados globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install "rembg[cpu]" opencv-contrib-python-headless
  /tmp/venv/bin/python templates/desaparecidos/recorte_thor.py
O modelo EDSR_x4.pb (38 MB) é baixado na primeira execução para ~/.cache/edsr/ (fora do projeto).
"""
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "perdidos" / "thor.jpeg"
OUT = Path(__file__).resolve().parent / "img" / "thor.png"
MODEL = Path.home() / ".cache" / "edsr" / "EDSR_x4.pb"
MODEL_URL = "https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x4.pb"

FOTO = (14, 240, 385, 790)        # foto principal na arte (dentro da borda branca)


def main():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    foto = np.array(Image.open(SRC).convert("RGB").crop(FOTO))

    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(MODEL))
    sr.setModel("edsr", 4)
    grande = sr.upsample(foto[..., ::-1])[..., ::-1]      # o OpenCV trabalha em BGR

    cut = np.array(remove(Image.fromarray(grande), session=new_session("isnet-general-use")))

    # alfa: mais firme (tira a grama semitransparente entre as patas), sem os fiapos finos da borda
    # e ~2 px (da foto original) para dentro, onde o pelo já não tem mistura com a grama; borda suave
    a = cut[..., 3].astype(np.float32)
    a = np.clip((a - 60) / 140, 0, 1)
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    a = cv2.GaussianBlur(a, (0, 0), 3)

    # na parte semitransparente da borda, a cor vem do pelo de dentro (não da grama que ficou por trás)
    # (média ponderada só do miolo, para não puxar a cor da grama que ficou fora do recorte)
    miolo = (a > .99).astype(np.float32)
    rgb = cut[..., :3].astype(np.float32)
    soma = cv2.GaussianBlur(rgb * miolo[..., None], (0, 0), 8)
    peso = cv2.GaussianBlur(miolo, (0, 0), 8)[..., None]
    preenche = soma / np.maximum(peso, 1e-4)
    borda = ((a > 0) & (miolo == 0))[..., None]
    rgb = np.where(borda, preenche, rgb)

    # pelo acinzentado pela grama junto ao contorno: clareia aos poucos na direção do pelo de dentro,
    # só onde está mais escuro que ele e sumindo até 40 px para dentro (sem faixa dura, sem emenda)
    dist = cv2.distanceTransform((a > .5).astype(np.uint8), cv2.DIST_L2, 5)
    fundo = (dist >= 40).astype(np.float32)
    dentro = cv2.GaussianBlur(rgb * fundo[..., None], (0, 0), 16) / np.maximum(
        cv2.GaussianBlur(fundo, (0, 0), 16)[..., None], 1e-4)
    lum = lambda x: x @ np.array([.299, .587, .114], np.float32)
    w = np.clip((lum(dentro) - lum(rgb) - 6) / 18, 0, 1) * np.clip(1 - dist / 40, 0, 1)
    rgb = rgb * (1 - w[..., None]) + dentro * w[..., None]

    cut[..., :3] = rgb.clip(0, 255).astype(np.uint8)
    cut[..., 3] = (a * 255).astype(np.uint8)

    im = Image.fromarray(cut, "RGBA")
    im = im.crop(im.getbbox())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
