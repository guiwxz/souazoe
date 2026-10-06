"""Prepara as duas fotos da Chiquinha para o template de desaparecidos (chiquinha.html e chiquinha-vista.html).

As imagens recebidas são dois prints (1080x2340) de Stories:
  perdidos/chiquinha-1.jpeg  a arte "PROCURA-SE Chiquinha", com a foto dela sentada no sofá à esquerda
                             e a caixinha branca "Está de lenço rosa no pescoço" por cima da pata
  perdidos/chiquinha-2.jpeg  ela de lenço rosa na rua, perto da Retipasso, com a caixa preta de texto por cima

Foto 1 (img/chiquinha.png): o rembg (isnet-general-use) separa a Chiquinha do sofá. Ela vai INTEIRA, do jeito
que veio: das orelhas até onde a faixa creme da arte começa (y=1600), sem fade, para assentar na divisa do
bloco ink. Nada é reconstruído: a caixinha branca continua no recorte (alfa cheio) e o chiquinha.html põe a
nota na identidade da Zoe exatamente por cima dela. Na borda, a cor do pelo de dentro cobre o cinza do sofá
que o recorte arrasta. Sai em 2x, com um unsharp leve.
Foto 2 (img/chiquinha-vista.jpg, Story separado: chiquinha-vista.html): a foto inteira abaixo da caixa preta,
na largura toda (o "1141" e a placa da fachada ficam acima da caixa e saem junto). A "arrumadinha" é leve,
para continuar sendo a foto real: um bilateral tira os pingos e o ruído sem borrar as bordas, os níveis e um
CLAHE suave (só na luminância) devolvem o contraste que a chuva lavou, e um pouco de cor e de nitidez.

Precisa de rembg + opencv num venv temporário (não estão instalados globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install "rembg[cpu]" opencv-python-headless
  /tmp/venv/bin/python templates/desaparecidos/foto_chiquinha.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent.parent
IMG = Path(__file__).resolve().parent / "img"

BAND = (0, 630, 630, 1600)   # print 1: das orelhas (abaixo do coração da arte) até a faixa creme (y>=1603)
NOTA = (145, 1330, 388, 1473)  # caixinha branca "Está de lenço rosa no pescoço" (fica no recorte)
SOFA_Y = 1330                  # daqui para baixo, o cinza escuro entre as patas é o assento do sofá
OMBRO = (150, 950)             # e à esquerda de x=150, abaixo de y=950, é o encosto junto do ombro
VISTA = (0, 868, 1048, 2040)   # print 2: a foto toda abaixo da caixa preta (que termina em y=863), sem os ícones
                               # do Instagram na borda direita (x>=1055) nem os cantos arredondados do pé


def recorte():
    arte = Image.open(ROOT / "perdidos" / "chiquinha-1.jpeg").convert("RGB")
    cut = np.array(remove(arte.crop(BAND), session=new_session("isnet-general-use")))

    # alfa mais firme (some a névoa semitransparente do sofá) e 1 px para dentro (tira o halo cinza)
    a = cut[..., 3].astype(np.float32)
    a = cv2.erode(np.clip((a - 50) / 150, 0, 1), np.ones((3, 3), np.uint8))
    a = cv2.GaussianBlur(a, (0, 0), 0.7)
    # o assento do sofá entre as patas e a faixa dele junto do ombro esquerdo (cinza neutro e escuro) o rembg
    # deixa como se fosse ela; o pelo é caramelo
    rgb = cut[..., :3].astype(int)
    sofa = (rgb.max(2) < 95) & (rgb.max(2) - rgb.min(2) < 22)
    sofa[:SOFA_Y - BAND[1], OMBRO[0]:] = False                # acima das patas, só no ombro esquerdo
    sofa[:OMBRO[1] - BAND[1]] = False                         # (abaixo da orelha, que tem sombra escura)
    sofa = cv2.morphologyEx(sofa.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    sofa = cv2.dilate(sofa, np.ones((3, 3), np.uint8))
    a *= 1 - cv2.GaussianBlur(sofa.astype(np.float32), (0, 0), 1.2)
    x0, y0, x1, y1 = NOTA
    a[y0 - BAND[1]:y1 - BAND[1], x0 - BAND[0]:x1 - BAND[0]] = 1

    # borda sem o cinza do sofá: na faixa de ~4 px da borda, a cor vem do pelo logo dentro dela
    dentro = cv2.erode((a > 0.95).astype(np.float32), np.ones((9, 9), np.uint8))
    rgb = cut[..., :3].astype(np.float32)
    viz = cv2.GaussianBlur(rgb * dentro[..., None], (0, 0), 3) / (cv2.GaussianBlur(dentro, (0, 0), 3)[..., None] + 1e-6)
    borda = (a > 0) & (dentro == 0) & (cv2.GaussianBlur(dentro, (0, 0), 3) > 0.02)
    rgb[borda] = viz[borda]
    cut[..., :3] = rgb.clip(0, 255).astype(np.uint8)
    cut[..., 3] = (a * 255).astype(np.uint8)

    im = Image.fromarray(cut, "RGBA")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 40, 2))
    im.save(IMG / "chiquinha.png")
    print(IMG / "chiquinha.png", im.size)


def vista():
    foto = np.array(Image.open(ROOT / "perdidos" / "chiquinha-2.jpeg").convert("RGB").crop(VISTA))
    foto = cv2.bilateralFilter(foto, 5, 20, 5)
    lab = cv2.cvtColor(foto, cv2.COLOR_RGB2LAB)
    lum = lab[..., 0].astype(np.float32)
    lo, hi = np.percentile(lum, [1, 99.7])
    lab[..., 0] = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(2, 2)).apply(
        np.clip((lum - lo) * 255 / (hi - lo), 0, 255).astype(np.uint8))
    foto = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    im = Image.fromarray(foto)
    im = ImageEnhance.Color(im).enhance(1.08)
    im = im.filter(ImageFilter.UnsharpMask(1.5, 60, 2))
    im.save(IMG / "chiquinha-vista.jpg", quality=93)
    print(IMG / "chiquinha-vista.jpg", im.size)


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    recorte()
    vista()
