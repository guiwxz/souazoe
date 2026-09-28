"""Capa do Reel 02 "Tchau, cartaz" (1080x1920), no padrão da capa do Reel 01:
foto em tela cheia, degradê escuro embaixo e uma frase em Poppins com uma palavra em lilás.

A foto é a pata da Zoe encostando na foto dela no cartaz (IMG_8443, 3,0 s). O corte tira o
"PROCURA-SE" do topo e os telefones do cartaz ficam borrados.

Uso: python3 editor/capa_02.py
"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "drive" / "set26" / "cartazes" / "IMG_8443.MOV"
FRAME = ROOT / "videos" / "IMG_8443_3.0.jpg"
OUT = ROOT / "saida" / "video" / "video2" / "capa-02.png"
FONT = ROOT / "editor" / "fonts" / "Poppins-Bold.ttf"
W, H = 1080, 1920
INK, WHITE, LILAC = (23, 19, 31), (255, 255, 255), (185, 167, 243)

# frase em linhas; cada linha é uma lista de (texto, cor)
LINES = [[("Hoje ", WHITE), ("ajudei", LILAC), (" a tirar", WHITE)],
         [("meus cartazes", WHITE)],
         [("da cidade", WHITE)]]
PHONES = (500, 1130, 1050, 1470)   # onde ficam os telefones no quadro original (x0, y0, x1, y1)
ZOOM = 1.15


def main():
    if not FRAME.exists():
        FRAME.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "3.0", "-i", str(SRC),
                        "-frames:v", "1", "-q:v", "2", str(FRAME)], check=True)
    im = Image.open(FRAME).convert("RGB").resize((W, H))

    # borra os telefones com bordas suaves
    blur = im.filter(ImageFilter.GaussianBlur(30))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(PHONES, radius=60, fill=255)
    im = Image.composite(blur, im, mask.filter(ImageFilter.GaussianBlur(20)))

    # corte mais fechado, ancorado embaixo à esquerda: some o "PROCURA-SE", a pata fica inteira
    im = im.resize((int(W * ZOOM), int(H * ZOOM)), Image.LANCZOS)
    im = im.crop((0, im.height - H, W, im.height))

    # degradê escuro (ink) de baixo para cima, para o texto
    grad = Image.new("L", (1, H))
    for y in range(H):
        f = y / H
        a = 0 if f < 0.45 else 0.62 * (f - 0.45) / 0.17 if f < 0.62 else 0.62 + 0.33 * (f - 0.62) / 0.38
        a = max(a, 0.7 * (1 - f / 0.14))       # escurece o topo (resto do "PROCURA-SE", sob a interface)
        grad.putpixel((0, y), int(255 * min(a, 0.95)))
    im = Image.composite(Image.new("RGB", (W, H), INK), im, grad.resize((W, H)))

    # frase alinhada à esquerda, na faixa que aparece também no recorte 3:4 do perfil
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(FONT), 92)
    x0, y, lh = 80, 1175, 112
    for line in LINES:
        x = x0
        for text, color in line:
            d.text((x, y), text, font=font, fill=color)
            x += d.textlength(text, font=font)
        y += lh

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
