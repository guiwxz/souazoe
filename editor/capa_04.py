"""Capa do Reel 04 "Os 6 dias da Zoe · Parte 2" (1080x1920), no padrão da capa do Reel 03:
foto em tela cheia, degradê escuro embaixo, o contador de 6 dias (com os dias já cobertos cheios),
"OS 6 DIAS DA ZOE · PARTE N" e uma frase em Poppins com uma palavra em lilás.

A foto é a Zoe deitada na cama, olhando para a câmera (abril de 2026, da pasta da apresentação).
A frase joga com o tema do episódio: as parecidas e as Zoes de IA que chegaram, e nenhuma era ela.

Uso: python editor/capa_04.py   (Python com Pillow)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
APRES = ROOT / "drive" / "instagram" / "apresentação␠"   # o último caractere é U+2420 (o espaço gravado pelo rclone)
SRC = APRES / "AC6E350A-3CFA-48C3-B586-EF3C41538078.JPG"
ZOOM, SUBIR = 1.08, 150   # amplia um pouco e sobe a foto, para o rosto ficar acima do degradê
OUT = ROOT / "saida" / "video" / "video4" / "capa-04.png"
FONTS = ROOT / "editor" / "fonts"
W, H = 1080, 1920
INK, WHITE, LILAC = (23, 19, 31), (255, 255, 255), (185, 167, 243)

PARTE, CHEIOS = 2, 5   # o episódio e quantos dos 6 dias ele já cobriu
# frase em linhas; cada linha é uma lista de (texto, cor)
LINES = [[("Muitas Zoes.", WHITE)],
         [("Nenhuma", LILAC), (" era eu.", WHITE)]]


def main():
    im = ImageOps.exif_transpose(Image.open(SRC)).convert("RGB")
    s = max(W / im.width, H / im.height) * ZOOM
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, min(SUBIR, im.height - H)
    im = im.crop((x, y, x + W, y + H))

    # degradê escuro (ink) de baixo para cima, para o texto (o mesmo das capas 02 e 03)
    grad = Image.new("L", (1, H))
    for y in range(H):
        f = y / H
        a = 0 if f < 0.45 else 0.62 * (f - 0.45) / 0.17 if f < 0.62 else 0.62 + 0.33 * (f - 0.62) / 0.38
        grad.putpixel((0, y), int(255 * min(a, 0.95)))
    im = Image.composite(Image.new("RGB", (W, H), INK), im, grad.resize((W, H)))

    # tudo alinhado à esquerda, abaixo do focinho da Zoe e dentro do recorte 3:4 do perfil (y 240–1680)
    im = im.convert("RGBA")
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    x0 = 80

    # contador de 6 dias: segmentos lilás cheios e os demais em branco translúcido
    sw, sh, gap, y = 72, 10, 12, 1190
    for i in range(6):
        cor = LILAC + (255,) if i < CHEIOS else WHITE + (70,)
        d.rounded_rectangle((x0 + i * (sw + gap), y, x0 + i * (sw + gap) + sw, y + sh), radius=sh // 2, fill=cor)

    # nome da série, em caixa alta com espaçamento
    tag = ImageFont.truetype(str(FONTS / "Poppins-ExtraBold.ttf"), 38)
    x, y = x0, 1220
    for ch in f"OS 6 DIAS DA ZOE · PARTE {PARTE}":
        d.text((x, y), ch, font=tag, fill=LILAC + (255,))
        x += d.textlength(ch, font=tag) + 3

    # a frase
    font = ImageFont.truetype(str(FONTS / "Poppins-Bold.ttf"), 104)
    y, lh = 1290, 122
    for line in LINES:
        x = x0
        for text, color in line:
            d.text((x, y), text, font=font, fill=color + (255,))
            x += d.textlength(text, font=font)
        assert x <= W - 60, f"linha larga demais ({x:.0f} px): diminua a fonte"
        y += lh

    im = Image.alpha_composite(im, over).convert("RGB")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
