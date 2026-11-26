"""Efeito "arte de capa do GTA VI" nas fotos do carrossel ZOE VI (carrossel/zoe-vi.html).

As artes oficiais do GTA VI são pinturas digitais em cima de fotos: cores chapadas e suaves (o detalhe fino some),
contorno escuro nas bordas, contraste alto e a luz de fim de tarde de Vice City (sombras roxas, luzes rosa e laranja).
Aqui o efeito é feito só com processamento de imagem, em cima das fotos reais (nada é desenhado nem inventado):

  1. pintura: filtro que preserva bordas (edgePreservingFilter) + um pouco de quantização (k-means) para chapar as cores;
  2. contorno: bordas da imagem suavizada (adaptiveThreshold), em ink, multiplicadas por cima;
  3. cor: saturação e contraste maiores + um mapa de gradiente pôr do sol (roxo → rosa → laranja → creme), misturado em parte;
  4. um grão leve, para não ficar com cara de filtro de app.
O canal alfa do recorte (zoe-creche.png) é mantido.

Saída: carrossel/img/zoe-vi/fx-<nome>.jpg (ou .png para o recorte)
Uso: python carrossel/gta_fx.py   (opencv-python-headless + numpy + Pillow, num venv temporário)
"""
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
IMG = AQUI / "img"
OUT = IMG / "zoe-vi"

FOTOS = [IMG / "3.jpg", IMG / "4.jpg", IMG / "7.jpg", IMG / "9.jpg", OUT / "zoe-creche.png"]

# mapa de gradiente pôr do sol, da sombra para a luz
GRAD = [(0.00, "#1B1035"), (0.30, "#5B2A8C"), (0.55, "#D9408F"), (0.78, "#FF9E7A"), (1.00, "#FFF1DC")]
INK = np.array([0x1F, 0x13, 0x17], np.float32) / 255  # BGR


def hex_bgr(h):
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32) / 255


def gradiente(lum):
    pos = np.array([p for p, _ in GRAD], np.float32)
    cores = np.stack([hex_bgr(c) for _, c in GRAD])
    out = np.zeros(lum.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(lum, pos, cores[:, k])
    return out


def quantiza(img, k=18):
    z = img.reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _, lab, cen = cv2.kmeans(z, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    return cen[lab.flatten()].reshape(img.shape)


def efeito(bgr, alfa=None):
    h, w = bgr.shape[:2]
    escala = max(h, w) / 1350
    # 1. pintura
    pint = cv2.edgePreservingFilter(bgr, flags=cv2.RECURS_FILTER, sigma_s=45, sigma_r=0.32)
    pint = cv2.bilateralFilter(pint, 9, 40, 9)
    q = quantiza(pint).astype(np.float32)
    pint = cv2.addWeighted(pint.astype(np.float32), 0.6, q, 0.4, 0) / 255

    # 3. cor: saturação, contraste em S e o pôr do sol
    hsv = cv2.cvtColor((pint * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.3, 0, 255)
    cor = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255
    cor = np.clip((cor - 0.5) * 1.18 + 0.52, 0, 1)
    cor = cor * cor * (3 - 2 * cor) * 0.55 + cor * 0.45  # curva em S suave
    lum = cv2.cvtColor((cor * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    cor = cor * 0.78 + gradiente(lum) * 0.22

    # 2. contorno em ink nas bordas
    cinza = cv2.cvtColor((pint * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    cinza = cv2.medianBlur(cinza, 5)
    bloco = int(9 * escala) | 1
    borda = cv2.adaptiveThreshold(cinza, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, max(bloco, 7), 5)
    borda = cv2.GaussianBlur(255 - borda, (3, 3), 0).astype(np.float32) / 255 * 0.8
    cor = cor * (1 - borda[..., None]) + INK * borda[..., None]

    # 4. grão leve
    rng = np.random.default_rng(6)
    cor = np.clip(cor + rng.normal(0, 0.018, cor.shape[:2])[..., None], 0, 1)
    out = (cor * 255).astype(np.uint8)
    if alfa is not None:
        out = np.dstack([out, alfa])
    return out


def main():
    for f in FOTOS:
        im = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        alfa = im[..., 3] if im.shape[2] == 4 else None
        out = efeito(im[..., :3], alfa)
        dest = OUT / f"fx-{f.stem}{'.png' if alfa is not None else '.jpg'}"
        cv2.imwrite(str(dest), out, [cv2.IMWRITE_JPEG_QUALITY, 92] if alfa is None else [])
        print(dest.relative_to(AQUI.parent), out.shape[1], "x", out.shape[0])


if __name__ == "__main__":
    main()
