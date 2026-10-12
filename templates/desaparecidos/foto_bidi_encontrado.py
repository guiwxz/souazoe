"""Prepara a foto do Bidi (perdidos/bidi-print.jpeg) para o aviso de encontrado (bidi-encontrado.html).

A imagem é o print (1080x2340) do alerta de desaparecido do Bidi (bidi.html). Este aviso foi feito numa sessão
sem a arte original (perdidos/bidi.jpeg, que o foto_bidi.py usa), então a foto sai do print: o cartão da foto é recortado por
dentro da borda e da sombra rosa, e duas coisas da arte são apagadas (inpaint): os cantos arredondados
(lilás) e o "Bidi" à mão, que invade o canto de baixo à esquerda (sobre o chão branco). O nome volta no
mesmo lugar pelo HTML. A foto já está no tamanho em que o template a usa (~680 px), então não há ampliação.

Saída: img/bidi-encontrado.jpg (677x759).

Precisa de opencv num venv temporário (não está instalado globalmente):
  python -m venv /tmp/venv && /tmp/venv/bin/pip install opencv-python-headless pillow
  /tmp/venv/bin/python templates/desaparecidos/foto_bidi_encontrado.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "perdidos" / "bidi-print.jpeg"
OUT = Path(__file__).resolve().parent / "img" / "bidi-encontrado.jpg"

FOTO = (202, 507, 879, 1266)     # cartão da foto no print, 1 px para dentro da borda (a sombra rosa começa em 881/1268)
RAIO = 24                        # raio dos cantos arredondados do cartão, no print
NOME = (196, 1128, 330, 1266)    # caixa do "Bidi" à mão (contorno ink + preenchimento branco + sombra)


def main():
    arte = np.array(Image.open(SRC).convert("RGB"))
    foto = np.ascontiguousarray(arte[FOTO[1]:FOTO[3], FOTO[0]:FOTO[2]])
    h, w = foto.shape[:2]

    # cantos: tudo o que fica fora do retângulo arredondado
    dentro = np.zeros((h, w), np.uint8)
    cv2.rectangle(dentro, (RAIO, 0), (w - 1 - RAIO, h - 1), 255, -1)
    cv2.rectangle(dentro, (0, RAIO), (w - 1, h - 1 - RAIO), 255, -1)
    for cx, cy in ((RAIO, RAIO), (w - 1 - RAIO, RAIO), (RAIO, h - 1 - RAIO), (w - 1 - RAIO, h - 1 - RAIO)):
        cv2.circle(dentro, (cx, cy), RAIO, 255, -1)
    mask = cv2.dilate(255 - dentro, np.ones((5, 5), np.uint8))

    # nome: o contorno ink é escuro (o chão embaixo é claro); fechar o contorno e preencher as letras
    x0, y0, x1, y1 = NOME[0] - FOTO[0], NOME[1] - FOTO[1], NOME[2] - FOTO[0], NOME[3] - FOTO[1]
    x0 = max(x0, 0)
    caixa = foto[y0:y1, x0:x1].astype(int)
    escuro = ((caixa.sum(-1) < 330) * 255).astype(np.uint8)
    escuro = cv2.morphologyEx(escuro, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    letras = np.zeros_like(escuro)
    contornos, _ = cv2.findContours(escuro, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(letras, contornos, -1, 255, -1)
    letras = cv2.dilate(np.maximum(letras, escuro), np.ones((9, 9), np.uint8))   # inclui pedaços do contorno na borda
    mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], letras)

    foto = cv2.inpaint(foto, mask, 9, cv2.INPAINT_TELEA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(foto).save(OUT, quality=93)
    print(OUT, (w, h))


if __name__ == "__main__":
    main()
