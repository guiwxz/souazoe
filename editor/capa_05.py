"""Capa do Reel 05 "Os 6 dias da Zoe · Parte 3" (1080x1920), no padrão das capas 03 e 04 no texto:
o contador de 6 dias (agora com os 6 cheios), "OS 6 DIAS DA ZOE · PARTE 3" e a frase em Poppins.

A imagem (aprovada pelo Guilherme em 06/10, a opção "C3"): o mapa da prévia do Ep. 3 (`mapa.py ep3`, com a rota
rosa e os nomes das ruas), subido 120 px para o fim da rota ficar acima do texto, e a Zoe recortada (a do
template da etiqueta, templates/etiqueta/img/zoe-creche.png), grande, no alto à direita, por cima da linha.
Atrás dela o mapa escurece numa mancha suave, e ela leva só uma sombra ink desfocada no contorno (sem borda).
A base do recorte (corte reto nas patas) some aos poucos no mapa. A rota vai numa camada à parte, por cima da
mancha, para continuar acesa.

O texto: a abertura da fala da Isabela no gancho, entre aspas e menor, e embaixo, grande, o número do
episódio: os 2 km que ela correu em 7 minutos. Tudo dentro do recorte 3:4 do perfil (y 240–1680).

Uso: python editor/capa_05.py   (Python com Pillow; o mapa sai do editor/mapa.py, via Chrome headless)
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "editor"))
import mapa  # noqa: E402

ZOE = ROOT / "templates" / "etiqueta" / "img" / "zoe-creche.png"
OUT = ROOT / "saida" / "video" / "video5" / "capa-05.png"
WORK = ROOT / "videos" / "ep3"                       # camadas do mapa (não versionadas)
FONTS = ROOT / "editor" / "fonts"
W, H = 1080, 1920
INK, WHITE, LILAC = (23, 19, 31), (255, 255, 255), (185, 167, 243)

PARTE, CHEIOS = 3, 6   # o episódio e quantos dos 6 dias ele já cobriu
SOBE = 70              # o bloco de texto sobe (dois textos: a fala e o número), para caber no recorte 3:4
# o texto em blocos: (fonte, tamanho, altura da linha, espaço depois, linhas); cada linha é uma lista de (texto, cor)
BLOCOS = [
    ("Poppins-Bold.ttf", 64, 80, 22, [[("“É inacreditável o que", WHITE)],      # a fala da Isabela
                                      [("essa cachorra fez.”", WHITE)]]),
    ("Poppins-Bold.ttf", 104, 122, 0, [[("2 km em", WHITE)],                   # o número do episódio
                                       [("7 minutos", LILAC), (".", WHITE)]]),
]
# o mapa: a vista da prévia ep3-a (1500 m de largura, o meio da rota em x 540) com o meio 120 px mais alto
LARGURA_M, ANCORA = 1500, (W / 2, 860 - 120)
ZOE_H, ZOE_Y, ZOE_DIR = 860, 150, 30   # altura, topo e folga até a borda direita
FADE_BASE = 170                        # px da base do recorte que somem no mapa


def gradiente(im):
    """Degradê ink de baixo para cima (o das capas 02 a 04, a 90%), para o texto."""
    grad = Image.new("L", (1, H))
    for yy in range(H):
        f = yy / H
        a = 0 if f < 0.45 else 0.62 * (f - 0.45) / 0.17 if f < 0.62 else 0.62 + 0.33 * (f - 0.62) / 0.38
        grad.putpixel((0, yy), int(255 * min(a * 0.9, 0.95)))
    return Image.composite(Image.new("RGB", (W, H), INK), im, grad.resize((W, H)))


def texto(im):
    """Contador, nome da série e a frase, alinhados à esquerda (o padrão das capas)."""
    im = im.convert("RGBA")
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    x0 = 80

    # contador de 6 dias: segmentos lilás cheios e os demais em branco translúcido
    sw, sh, gap, y = 72, 10, 12, 1190 - SOBE
    for i in range(6):
        cor = LILAC + (255,) if i < CHEIOS else WHITE + (70,)
        d.rounded_rectangle((x0 + i * (sw + gap), y, x0 + i * (sw + gap) + sw, y + sh), radius=sh // 2, fill=cor)

    # nome da série, em caixa alta com espaçamento
    tag = ImageFont.truetype(str(FONTS / "Poppins-ExtraBold.ttf"), 38)
    x, y = x0, 1220 - SOBE
    for ch in f"OS 6 DIAS DA ZOE · PARTE {PARTE}":
        d.text((x, y), ch, font=tag, fill=LILAC + (255,))
        x += d.textlength(ch, font=tag) + 3

    # o texto, bloco a bloco
    y = 1284 - SOBE
    for fname, size, lh, depois, lines in BLOCOS:
        font = ImageFont.truetype(str(FONTS / fname), size)
        for line in lines:
            x = x0
            for text, color in line:
                d.text((x, y), text, font=font, fill=color + (255,))
                x += d.textlength(text, font=font)
            assert x <= W - 60, f"linha larga demais ({x:.0f} px): diminua a fonte"
            y += lh
        y += depois
    assert y <= 1700, f"o texto passa do recorte 3:4 do perfil (termina em y {y})"
    return Image.alpha_composite(im, over).convert("RGB")


def main():
    # o mapa com os nomes das ruas (sem a rota) e a rota numa camada transparente
    els = mapa.load()
    r, _ = mapa.rota_ruas(els)
    v = mapa.View(mapa.meio(r), LARGURA_M, anchor=ANCORA)
    por_rua = {p[0]: mapa.rota_ruas(els, [p])[0] for p in mapa.PERNAS_EP3}
    WORK.mkdir(parents=True, exist_ok=True)
    base_png, rota_png = WORK / "capa-mapa.png", WORK / "capa-rota.png"
    mapa.render(mapa.svg_map(els, v, mapa.ep3_labels(els, v, por_rua)), base_png)
    mapa.render(mapa.svg_layer(mapa.route(v, r, 12)), rota_png, transparent=True)
    c = gradiente(Image.open(base_png).convert("RGB")).convert("RGBA")

    # a Zoe recortada, com a base sumindo aos poucos
    z = Image.open(ZOE).convert("RGBA")
    z = z.resize((round(z.width * ZOE_H / z.height), ZOE_H), Image.LANCZOS)
    zx, zy = W - z.width - ZOE_DIR, ZOE_Y
    fade = Image.linear_gradient("L").resize((z.width, FADE_BASE)).transpose(Image.FLIP_TOP_BOTTOM)
    am = z.getchannel("A")
    base = am.crop((0, ZOE_H - FADE_BASE, z.width, ZOE_H))
    am.paste(Image.composite(base, Image.new("L", base.size, 0), fade), (0, ZOE_H - FADE_BASE))
    z.putalpha(am)

    # o mapa escurece numa mancha suave atrás dela (elipse desfocada); a rota vem por cima, acesa
    dim = Image.new("L", (W, H), 0)
    cx, cy, rx, ry = zx + z.width * 0.52, zy + ZOE_H * 0.52, z.width * 0.62, ZOE_H * 0.58
    ImageDraw.Draw(dim).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=200)
    c = Image.composite(Image.new("RGBA", (W, H), INK + (255,)), c, dim.filter(ImageFilter.GaussianBlur(90)))
    c.alpha_composite(Image.open(rota_png).convert("RGBA"))

    # a sombra ink desfocada no contorno dela (sem borda) e a Zoe
    pad = 60
    alpha = Image.new("L", (z.width + 2 * pad, z.height + 2 * pad), 0)
    alpha.paste(z.getchannel("A"), (pad, pad))
    sombra = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
    sombra.paste(Image.new("RGBA", alpha.size, (8, 6, 12, 255)),
                 mask=alpha.filter(ImageFilter.GaussianBlur(30)).point(lambda a: int(min(255, a * 1.15))))
    c.alpha_composite(sombra, (zx - pad + 6, zy - pad + 20))
    c.alpha_composite(z, (zx, zy))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    texto(c).save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
