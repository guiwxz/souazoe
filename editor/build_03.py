"""Monta o Reel 03 "Os 6 dias da Zoe · Parte 1" (9:16, 30 fps, ~67 s), narrado pela Isabela.

Ep. 1 da série (dias 1 e 2, sex 18 e sáb 19/09): "o barulho e o silêncio". Segue o mapa de tempo
de roteiros/serie-6-dias/roteiro.md com os tempos reais da narração (editor/words-03.json).

Como funciona:
  1. Áudio: apara o silêncio de audios/1..8.ogg e encadeia os parágrafos (PARTS e GAPS; CUTS tira
     silêncio de dentro de um arquivo), com highpass + afftdn. A trilha (editor/trilha_03.py) é gerada aqui com as marcas reais: fica por
     baixo da voz com duck (sidechain), zera no P7 e volta baixinha no fecho. Saem duas mixagens
     em -14 LUFS (ganho linear medido + limitador): com trilha e sem trilha (voz + ambiente do fecho).
  2. Imagem: cada quadro é composto em Python (Pillow), plano a plano (SHOTS): fotos com zoom
     lento, prints em cartão (um por vez, inteiros, telefones borrados), mapas animados (a linha que
     cresce pela Tiradentes e pela Lava Pés até mapa.FIM, os zooms A→B e B→C, o ponto pulsando no FIM),
     a tela ink do silêncio e os vídeos (o Reel do sábado, a Zoe hoje).
  3. Texto (ASS, queimado pelo ffmpeg): legendas em blocos de até 3 palavras com a palavra ativa em
     amarelo, contador de 6 dias, gancho, cartelas, "NINGUÉM VIU." / "NINGUÉM OUVIU." e o fecho.

Requisitos: ffmpeg/ffprobe no PATH, Chrome (mapas, via editor/mapa.py) e um venv com Python 3.9,
numpy, scipy e Pillow (o Python padrão da máquina é 3.7, sem Pillow):
  py -3.9 -m venv <tmp>/venv
  <tmp>/venv/Scripts/pip install numpy scipy Pillow
Uso:
  <tmp>/venv/Scripts/python editor/build_03.py              render completo → saida/video/video3/
  <tmp>/venv/Scripts/python editor/build_03.py 26 38        só um trecho, para conferir → videos/ep1/trecho.mp4
  <tmp>/venv/Scripts/python editor/build_03.py palavras     refaz words-03.json a partir de
                                                            videos/ep1/palavras-locais.json (se PARTS/GAPS mudarem)
As palavras vieram do faster-whisper (medium, int8, venv 3.9), com a grafia conferida pela fala e
os inícios/fins acertados pelo envelope de energia de cada arquivo.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "editor"))
import mapa        # noqa: E402  camadas dos mapas (Chrome headless)
import trilha_03   # noqa: E402  trilha original (numpy + scipy)

DRIVE = ROOT / "drive"
APRES = DRIVE / "instagram" / "apresentação␠"   # o último caractere é U+2420 (o espaço gravado pelo rclone)
SET = DRIVE / "set26"
DIV = SET / "divulgacao"
AUD = ROOT / "audios"
WORK = ROOT / "videos" / "ep1"                       # cópias de trabalho (não versionadas)
MAPS = WORK / "mapas"
FONTS = ROOT / "editor" / "fonts"
WORDS = ROOT / "editor" / "words-03.json"
MUSIC = AUD / "trilha-03.wav"
OUTDIR = ROOT / "saida" / "video" / "video3"
OUT = OUTDIR / "03-os-6-dias-parte-1.mp4"
OUT_NAT = OUTDIR / "03-os-6-dias-parte-1-sem-musica.mp4"
ASS = OUTDIR / "legendas-03.ass"
W, H, FPS = 1080, 1920, 30
HANDLE = "@souazoe.pf"

# identidade
INK, CREAM, LILAC, PINK, MUTED = (0x17, 0x13, 0x1F), (0xF6, 0xF1, 0xE9), (0xB9, 0xA7, 0xF3), (0xEC, 0x48, 0x99), (0x6E, 0x66, 0x7A)


def ass_c(rgb):
    return "&H{:02X}{:02X}{:02X}&".format(rgb[2], rgb[1], rgb[0])


# ---------------------------------------------------------------- áudio e linha do tempo
# (arquivo, início, fim) em segundos: a fala de cada parágrafo sem o silêncio da gravação
# (≈ 80 ms antes da primeira sílaba e ≈ 200 ms depois da última, pelo envelope de energia)
PARTS = [
    (1, 0.66, 2.95),    # A gente tava viajando quando a Zoe sumiu.
    (2, 0.63, 8.33),    # Ela ficou com uma pessoa de confiança ... e disparou.
    (3, 0.76, 6.26),    # Subiu a Tiradentes e chegou na Lava Pés ...
    (4, 0.54, 8.86),    # Enquanto a gente tentava uma passagem de volta ...
    (5, 0.70, 12.18),   # E lá de longe ... na rádio Uirapuru.   (ruído em 12,3 s fica de fora)
    (6, 1.01, 7.06),    # No sábado era aniversário do Guilherme ...
    (7, 0.94, 8.88),    # E nenhuma informação. Ninguém viu. Ninguém ouviu ...  (pausas dela mantidas)
    (8, 0.98, 7.39),    # Era desespero puro ... e ela não ia estar lá.
]
# silêncio tirado de dentro de um arquivo: {arquivo: [(início, fim), ...]}, só silêncio digital
CUTS = {7: [(3.05, 3.28)]}   # "informação." (termina em 2,52) → "Ninguém" (começa em 3,35): pausa de ~0,6 s
LEAD = 0.20                                          # antes da primeira palavra
GAPS = [1.10, 0.30, 0.80, 0.35, 1.15, 0.53, 0.80]    # respiro depois de cada parágrafo
#       └ cartela DIA 1     └ "?"      └ DIA 2 └ o corte do P7 (0,5 s até o P7) └ o mapa com o "?"
AFTER = 1.00                                         # silêncio depois do "não ia estar lá"
FECHO = 5.50                                         # a Zoe hoje, sem voz


def _segments(f, a, b):
    """Trechos do arquivo que entram na montagem: (a, b) menos os CUTS."""
    segs, t = [], a
    for c0, c1 in CUTS.get(f, []):
        segs.append((t, c0))
        t = c1
    return segs + [(t, b)]


def _removed(f, t):
    """Quanto silêncio foi tirado do arquivo f antes do instante local t."""
    return sum(min(c1, max(t, c0)) - c0 for c0, c1 in CUTS.get(f, []))


def _timeline():
    t, starts = LEAD, []
    for i, (f, a, b) in enumerate(PARTS):
        starts.append(round(t, 3))
        t += b - a - _removed(f, b) + (GAPS[i] if i < len(GAPS) else 0)
    return starts


P0 = _timeline()                                             # início de cada parágrafo
P1 = [round(s + b - a - _removed(f, b), 3) for s, (f, a, b) in zip(P0, PARTS)]  # fim de cada parágrafo
T_FECHO = round(P1[-1] + AFTER, 3)
DUR = round((T_FECHO + FECHO) * FPS) / FPS
NFRAMES = int(round(DUR * FPS))

_WORDS = json.loads(WORDS.read_text(encoding="utf-8")) if WORDS.exists() else []


def _norm(s):
    return re.sub(r"[^\w]", "", s.lower())


def cue(phrase, n=1, end=False):
    """Tempo (início, ou fim com end=True) da n-ésima ocorrência da frase na narração."""
    keys = [_norm(x) for x in phrase.split()]
    k = 0
    for i in range(len(_WORDS) - len(keys) + 1):
        if all(_norm(_WORDS[i + j]["w"]) == keys[j] for j in range(len(keys))):
            k += 1
            if k == n:
                return _WORDS[i + len(keys) - 1]["e"] if end else _WORDS[i]["s"]
    raise KeyError(f"não achei '{phrase}' #{n} em {WORDS.name}")


def palavras():
    """Converte videos/ep1/palavras-locais.json (tempos de cada arquivo) para a linha do tempo final."""
    loc = json.loads((WORK / "palavras-locais.json").read_text(encoding="utf-8"))
    out = []
    for (f, a, b), p0 in zip(PARTS, P0):
        for w in loc[str(f)]:
            s, e = max(w["s"], a), min(w["e"], b)
            out.append({"w": w["w"], "s": round(p0 + s - a - _removed(f, s), 3),
                        "e": round(p0 + e - a - _removed(f, e), 3)})
    WORDS.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(WORDS, len(out), "palavras")


# ---------------------------------------------------------------- mídia
# print → (arquivo, caixas a borrar em frações: largura, altura, x, y). A primeira é o telefone.
PRINTS = {
    "story": ("Screenshot_20260918_134001_Instagram.jpg",       # story de alerta, sex 13h40
              [(.54, .10, .23, .75),
               (.18, .045, .765, .81)]),     # as marcações (@ da creche, da carona e de pessoas): não expor ninguém
    "cartaz": ("Screenshot_20260918_204309_Instagram.jpg", [(.44, .10, .54, .81)]),     # cartaz novo, sex 20h43
    "uirapuru": ("Screenshot_20260928_152923_Instagram.jpg", [(.42, .048, .55, .535)]),  # Rádio Uirapuru, 18/09
}
REEL = DIV / "WhatsApp Video 2026-09-21 at 12.48.28.mp4"     # o Reel do sábado (576x1024, sem áudio)
HOJE = SET / "IMG_8419.MOV"                                  # a Zoe hoje, no sofá (4K)
HOJE_SS = 20.0                                               # trecho mais calmo (a partir de ~18 s)

# fotos: chave → (arquivo, recorte em pixels ou None)
PHOTOS = {
    "aviao": (WORK / "IMG_7685.png", None),                              # qui 17/09, no avião
    "creche": (APRES / "IMG_7200.PNG", (8, 300, 1162, 2190)),           # print de story: só a foto
    "grama": (WORK / "IMG_6304.png", (1058, 0, 1996, 1673)),             # na grama: só a Zoe (x .35–.66, y 0–.415)
    "sofa": (APRES / "58659130-acfd-4d55-80a7-0bf15de6e94d.JPG", None),  # no sofá
    "bola": (WORK / "IMG_6106.png", None),                               # a bola
}


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def prep():
    WORK.mkdir(parents=True, exist_ok=True)
    # HEIC do iPhone: no ffmpeg 9, sem -vf sai a imagem inteira (com filtro viraria a grade de tiles)
    for name in ("IMG_7685", "IMG_6304", "IMG_6106"):
        out = WORK / f"{name}.png"
        if not out.exists():
            run(["ffmpeg", "-y", "-v", "error", "-i", APRES / f"{name}.HEIC", "-frames:v", "1", out])
    # prints com o telefone borrado: recorta cada caixa, boxblur=20:3 e cola no mesmo lugar (sempre refaz)
    for key, (f, boxes) in PRINTS.items():
        fc, last = [], "0"
        for j, (bw, bh, bx, by) in enumerate(boxes):
            fc.append(f"[{last}]split[a{j}][b{j}];[b{j}]crop=iw*{bw}:ih*{bh}:iw*{bx}:ih*{by},boxblur=20:3[bl{j}];"
                      f"[a{j}][bl{j}]overlay=W*{bx}:H*{by}[o{j}]")
            last = f"o{j}"
        run(["ffmpeg", "-y", "-v", "error", "-i", DIV / f, "-filter_complex", ";".join(fc), "-map", f"[{last}]",
             "-frames:v", "1", WORK / f"print-{key}.png"])
    # camadas dos mapas: refaz se faltarem ou se o FIM/a âncora do mapa.py mudaram
    cam = MAPS / "ep1-camadas.json"
    info = json.loads(cam.read_text(encoding="utf-8")) if cam.exists() else {}
    if info.get("rota_latlon", [None])[-1] != list(mapa.FIM) or info.get("anchor") != list(mapa.ANCORA):
        mapa.ep1_camadas(MAPS)
        _cache.clear()


# ---------------------------------------------------------------- utilidades de imagem
_cache = {}


def cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def solid(rgb):
    return cached(("solid", rgb), lambda: Image.new("RGB", (W, H), rgb))


def photo(key):
    def load():
        path, crop = PHOTOS[key]
        im = Image.open(path).convert("RGB")
        if crop:
            im = im.crop(crop)
        # reduz uma vez: a caixa 9:16 precisa de ~1,5x a tela para o zoom continuar nítido
        bw = min(im.width, im.height * W / H)
        k = min(1.0, 1.5 * W / bw)
        return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS) if k < 1 else im
    return cached(("photo", key), load)


def cover_box(iw, ih, cx=0.5, cy=0.5):
    """Maior caixa 9:16 dentro da imagem, centrada em (cx, cy) (frações), sem sair da imagem."""
    bw, bh = (ih * W / H, ih) if iw / ih > W / H else (iw, iw * H / W)
    x0 = min(max(cx * iw - bw / 2, 0), iw - bw)
    y0 = min(max(cy * ih - bh / 2, 0), ih - bh)
    return x0, y0, bw, bh


def darken(im, k):
    return im if k >= 0.999 else Image.blend(solid((0, 0, 0)), im, max(k, 0.0))


def fade_alpha(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * max(a, 0))))
    return out


def place(layer, cx, cy, s, rot=0.0):
    """Camada RGBA na tela: escala s, rotação rot (graus) e centro (cx, cy) → RGBA WxH."""
    lw, lh = layer.size
    th = math.radians(rot)
    c, sn = math.cos(th) / s, math.sin(th) / s
    return layer.transform((W, H), Image.AFFINE,
                           (c, sn, lw / 2 - c * cx - sn * cy, -sn, c, lh / 2 + sn * cx - c * cy),
                           resample=Image.BICUBIC)


# ---------------------------------------------------------------- planos: fotos
PAD_TOP, FEATHER = 0.12, 0.05     # ink acima da foto e a transição (frações da altura), para a `win`


def padded(key):
    """A foto com uma faixa ink em cima: a foto se funde no ink ao longo de FEATHER da altura."""
    def make():
        im = photo(key)
        pad, fe = round(PAD_TOP * im.height), round(FEATHER * im.height)
        mask = np.full((im.height, im.width), 255, np.uint8)
        mask[:fe] = (255 * ease_arr(np.linspace(0, 1, fe)))[:, None]
        base = Image.new("RGB", (im.width, im.height + pad), INK)
        base.paste(im, (0, pad), Image.fromarray(mask))
        return base, pad
    return cached(("padded", key), make)


def ease_arr(u):
    return u * u * (3 - 2 * u)


def grad_top(fr, a0=0.85, y1=700):
    """Degradê ink no topo (a0 em y=0 até 0 em y1), para dar leitura ao título."""
    def make():
        y = np.arange(H, dtype=float)
        a = np.where(y < y1, a0 * (1 + np.cos(np.pi * np.minimum(y, y1) / y1)) / 2, 0.0)
        lay = np.zeros((H, W, 4), np.uint8)
        lay[..., :3] = INK
        lay[..., 3] = (255 * a).astype(np.uint8)[:, None]
        return Image.fromarray(lay)
    out = fr.convert("RGBA")
    out.alpha_composite(cached("gradtop", make))
    return out.convert("RGB")


def f_foto(o, t, t0, t1):
    """Foto com zoom lento: `z` (início, fim) sobre a caixa de cobertura; `f` é o ponto que fica parado.
    `left`: borda esquerda fixa (fração da largura), para deixar algo fora do quadro.
    `win`: janela explícita, ((altura, topo) no início, (altura, topo) no fim) em frações da altura da
    foto, com o centro em `cx`; o topo pode ser negativo (a foto desce e o alto vira ink).
    `grad`: degradê ink no topo."""
    u = (t - t0) / (t1 - t0)
    if "win" in o:
        im, pad = padded(o["src"])
        (h0, top0), (h1, top1) = o["win"]
        ih = im.height - pad
        h2 = lerp(h0, h1, u) * ih
        w2 = h2 * W / H
        X, Y = o.get("cx", 0.5) * im.width - w2 / 2, pad + lerp(top0, top1, u) * ih
    else:
        im = photo(o["src"])
        x0, y0, bw, bh = cover_box(*im.size, *o.get("c", (0.5, 0.5)))
        z = lerp(*o.get("z", (1.0, 1.08)), u)
        fx, fy = o.get("f", (0.5, 0.5))
        w2, h2 = bw / z, bh / z
        X = o["left"] * im.width if "left" in o else x0 + (bw - w2) * fx
        Y = y0 + (bh - h2) * fy
    fr = im.resize((W, H), Image.BICUBIC, box=(X, Y, X + w2, Y + h2), reducing_gap=2.0)
    if o.get("grad"):
        fr = grad_top(fr)
    if "dark" in o:                       # escurece até o preto entre dois instantes
        d0, d1 = o["dark"]
        fr = darken(fr, 1 - ease((t - d0) / (d1 - d0)) if t < d1 else 0)
    return fr


def f_ink(o, t, t0, t1):
    return solid(INK)


# ---------------------------------------------------------------- planos: prints em cartão
# cartão → (print, recorte em pixels, largura na tela, centro na tela, rotação). No P5 cada print
# aparece uma vez só, inteiro (também no fim do zoom de 5%), um de cada vez.
CARDS = {
    "story": ("story", (0, 0, 1080, 2080), 780, (540, 1085), -1.5),         # com o relógio 13:40 à vista
    "cartaz": ("cartaz", None, 900, (540, 380 + 450), 1.5),
    "uirapuru": ("uirapuru", (0, 250, 1080, 1740), 860, (540, 320 + 594), -0.8),  # do @ até a data
}
CARD_Z = (1.0, 1.05)  # zoom lento e contínuo em cada print
XF = 0.3              # crossfade entre um print e o próximo


def card_layer(key):
    def make():
        src, crop, dw, _, _ = CARDS[key]
        im = Image.open(WORK / f"print-{src}.png").convert("RGB")
        if crop:
            im = im.crop(crop)
        lw, lh = dw, round(im.height * dw / im.width)
        im = im.resize((lw, lh), Image.LANCZOS)
        pad, r = 110, 26
        mask = Image.new("L", (lw, lh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, lw - 1, lh - 1), r, fill=255)
        sh = Image.new("L", (lw + 2 * pad, lh + 2 * pad), 0)
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 30, pad + lw, pad + lh + 30), r, fill=170)
        sh = sh.filter(ImageFilter.GaussianBlur(40))
        layer = Image.merge("RGBA", (*[Image.new("L", sh.size, 0)] * 3, sh))
        card = im.convert("RGBA")
        card.putalpha(mask)
        layer.alpha_composite(card, (pad, pad))
        return layer
    return cached(("card", key), make)


def card_frame(key, z):
    """O print inteiro, em cartão (com sombra) sobre ink, na escala z."""
    _, _, _, (cx, cy), rot = CARDS[key]
    fr = solid(INK).convert("RGBA")
    fr.alpha_composite(place(card_layer(key), cx, cy, z, rot))
    return fr.convert("RGB")


def f_cartao(o, t, t0, t1):
    """P5: um print por vez, com um zoom lento e contínuo (CARD_Z). `xf` = (cartão, início, fim) do plano
    anterior, que sai num crossfade de XF s continuando o próprio zoom. Sem pop, balanço ou flash."""
    fr = card_frame(o["card"], lerp(*CARD_Z, (t - t0) / (t1 - t0)))
    if "xf" in o and t - t0 < XF:
        key, p0, p1 = o["xf"]
        fr = Image.blend(card_frame(key, lerp(*CARD_Z, (t - p0) / (p1 - p0))), fr, ease((t - t0) / XF))
    return fr


# ---------------------------------------------------------------- planos: mapas
# As três vistas (A, B, C) têm o mesmo centro (o meio da rota) na mesma âncora da tela (mapa.ANCORA).
def mj():
    return cached("mapjson", lambda: json.loads((MAPS / "ep1-camadas.json").read_text(encoding="utf-8")))


def map_img(name, mode="RGB"):
    return cached(("map", name), lambda: Image.open(MAPS / name).convert(mode))


def m_grande(key, k):
    """Vista "grande" (3x a área) com zoom-out k ≥ 1 em torno da âncora."""
    k = min(max(k, 1.0), 3.0)
    (gx, gy), (ax, ay) = mj()["grande_anchor"], mj()["anchor"]
    return map_img(f"ep1-{key}-grande.png").resize(
        (W, H), Image.BICUBIC, box=(gx - ax * k, gy - ay * k, gx + (W - ax) * k, gy + (H - ay) * k),
        reducing_gap=2.0)


def m_3x(key, g):
    """Vista em 3x de resolução com zoom-in g ≥ 1 (g = 1 é a vista normal)."""
    g = max(g, 1.0)
    ax, ay = mj()["anchor"]
    return map_img(f"ep1-{key}-3x.png").resize(
        (W, H), Image.BICUBIC,
        box=(3 * (ax - ax / g), 3 * (ay - ay / g), 3 * (ax + (W - ax) / g), 3 * (ay + (H - ay) / g)),
        reducing_gap=2.0)


def scaled_layer(layer, f):
    """Camada 1x (WxH) reduzida por f em torno da âncora do mapa."""
    if abs(f - 1) < 1e-4:
        return layer
    ax, ay = mj()["anchor"]
    return layer.transform((W, H), Image.AFFINE, (1 / f, 0, ax - ax / f, 0, 1 / f, ay - ay / f),
                           resample=Image.BICUBIC)


def dot_pos(s):
    """Posição na tela do FIM (onde ela foi vista pela última vez) numa escala s (px/m)."""
    (dx, dy), (ax, ay) = mj()["fim_m"], mj()["anchor"]
    return ax + dx * s, ay + dy * s


def draw_dot(fr, s, a=1.0):
    x, y = dot_pos(s)
    fr.alpha_composite(fade_alpha(map_img("ep1-ponto.png", "RGBA"), a), (round(x - 120), round(y - 120)))


def draw_rings(fr, s, t, since, period=1.35):
    """Ondas saindo do ponto (onde ela foi vista pela última vez), uma a cada `period` s."""
    if t < since:
        return
    x, y = dot_pos(s)
    k = 0
    while since + k * period <= t:
        u = (t - since - k * period) / 1.6
        k += 1
        if u >= 1:
            continue
        r, a = 16 + 70 * (1 - (1 - u) ** 2), 0.75 * (1 - u) ** 1.5
        ss, size = 3, int(2 * (r + 6)) + 4
        m = Image.new("L", (size * ss, size * ss), 0)
        c = size * ss / 2
        ImageDraw.Draw(m).ellipse((c - r * ss, c - r * ss, c + r * ss, c + r * ss),
                                  outline=int(255 * a), width=4 * ss)
        ring = Image.new("RGBA", (size, size), PINK + (0,))
        ring.putalpha(m.resize((size, size), Image.LANCZOS))
        fr.alpha_composite(ring, (round(x - size / 2), round(y - size / 2)))


def credit(fr):
    fr.alpha_composite(map_img("ep1-credito.png", "RGBA"))
    return fr.convert("RGB")


def route_arc():
    """Comprimento (px, vista A) da rota até cada vértice: [0, ..., total]."""
    def make():
        pts = mj()["rota"]
        acc = [0.0]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            acc.append(acc[-1] + math.hypot(x2 - x1, y2 - y1))
        return acc
    return cached("arc", make)


def route_reveal(p):
    """A rota da vista A revelada até a fração p do comprimento, com a ponta cortada na perpendicular
    (borda macia). Cada pixel da camada recebe a posição, ao longo da rota, do trecho mais próximo."""
    def prep_route():
        lay = map_img("ep1-a-rota.png", "RGBA")
        box = lay.getchannel("A").getbbox()
        arr = np.asarray(lay.crop(box)).copy()
        pts, acc = mj()["rota"], route_arc()
        ys, xs = np.mgrid[box[1]:box[3], box[0]:box[2]].astype(float)
        best, arc = np.full(xs.shape, np.inf), np.zeros(xs.shape)
        for i, ((x1, y1), (x2, y2)) in enumerate(zip(pts, pts[1:])):
            dx, dy = x2 - x1, y2 - y1
            u = np.clip(((xs - x1) * dx + (ys - y1) * dy) / (dx * dx + dy * dy), 0, 1)
            d = (xs - x1 - u * dx) ** 2 + (ys - y1 - u * dy) ** 2
            m = d < best
            best[m], arc[m] = d[m], acc[i] + u[m] * (acc[i + 1] - acc[i])
        return box, arr, arc, acc[-1]
    box, arr, arc, L = cached("route", prep_route)
    lim = 20 + p * (L + 30)                    # 20 px: o círculo da esquina já aparece antes da linha
    a = arr[..., 3] * np.clip((lim - arc) / 8 + 0.5, 0, 1)
    out = arr.copy()
    out[..., 3] = a.astype(np.uint8)
    return Image.fromarray(out), box[:2]


def line_progress(t, keys):
    """Fração da rota desenhada em t. `keys` = [(t, fração), ...]: começa e termina devagar (smoothstep)
    e passa exatamente por cada chave (o tempo é deformado por partes, sem parar no meio)."""
    inv = [0.5 - math.sin(math.asin(1 - 2 * f) / 3) for _, f in keys]   # inverso do smoothstep
    ts = [k for k, _ in keys]
    if t <= ts[0]:
        return 0.0
    if t >= ts[-1]:
        return 1.0
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    return ease(lerp(inv[i], inv[i + 1], (t - ts[i]) / (ts[i + 1] - ts[i])))


def question(fr, t, t_in, f=1.0, a=1.0):
    """O "?" da vista A (no FIM), entrando com um tranco em t_in."""
    if t < t_in:
        return
    def prep_q():
        lay = map_img("ep1-a-interrogacao.png", "RGBA")
        box = lay.getchannel("A").getbbox()
        return lay.crop(box), box
    q, box = cached("q", prep_q)
    u = (t - t_in) / 0.35
    pop = 1.0 if u >= 1 else 0.6 + 0.4 * ease(u) + 0.12 * math.sin(math.pi * min(u, 1))
    s = pop * f
    ax, ay = mj()["anchor"]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    cx, cy = ax + (cx - ax) * f, ay + (cy - ay) * f
    qq = q.resize((max(1, round(q.width * s)), max(1, round(q.height * s))), Image.BICUBIC)
    fr.alpha_composite(fade_alpha(qq, a * min(1, (t - t_in) / 0.12)),
                       (round(cx - qq.width / 2), round(cy - qq.height / 2)))


def f_mapa_linha(o, t, t0, t1):
    """P3: mapa A; a linha rosa cresce sem parar: sobe a Tiradentes, chega na Lava Pés e segue por ela
    até a Fagundes dos Reis (o FIM). Depois, o "?". `linha` = (início, na Lava Pés, no FIM)."""
    fr = m_grande("a", 1.0).convert("RGBA")
    l0, l1, l2 = o["linha"]
    acc = route_arc()
    lay, pos = route_reveal(line_progress(t, [(l0, 0.0), (l1, acc[1] / acc[-1]), (l2, 1.0)]))
    fr.alpha_composite(fade_alpha(lay, min(1, (t - t0) / 0.25)), pos)
    question(fr, t, o["q"])
    return credit(fr)


def zoom_k(k_end, t, z0, z1):
    """Zoom-out contínuo: k vai de 1 a k_end, em escala logarítmica (velocidade aparente constante)."""
    return math.exp(math.log(k_end) * ease((t - z0) / (z1 - z0)))


def xfade(k, k0, k1):
    return ease((math.log(k) - math.log(k0)) / (math.log(k1) - math.log(k0)))


def f_mapa_bairro(o, t, t0, t1):
    """P4: o mapa abre de A (a esquina) para B (o bairro); a rota vira o ponto, que pulsa."""
    sa, sb = mj()["scale"]["a"], mj()["scale"]["b"]
    k = zoom_k(sa / sb, t, *o["zoom"])
    w = xfade(k, 1.9, 2.9)
    fr = m_grande("a", min(k, 3.0)) if w < 1 else None
    if w > 0:
        b = m_3x("b", sa / sb / k)
        fr = b if fr is None else Image.blend(fr, b, w)
    fr = fr.convert("RGBA")
    if w < 1:
        lay, pos = route_reveal(1.0)
        full = Image.new("RGBA", (W, H))
        full.alpha_composite(lay, pos)
        fr.alpha_composite(fade_alpha(scaled_layer(full, 1 / k), 1 - w))
        question(fr, t, -1, f=1 / k, a=1 - ease((t - o["zoom"][0]) / 1.0))   # preso ao FIM, encolhe com o mapa
    s = sa / k
    if w > 0:
        draw_dot(fr, s, w)
    draw_rings(fr, s, t, o["pulso"])
    return credit(fr)


def f_mapa_cidade(o, t, t0, t1):
    """P6: o mesmo bairro (B) e, em "a cidade inteira", o mapa abre para a cidade toda (C)."""
    sb, sc = mj()["scale"]["b"], mj()["scale"]["c"]
    k = zoom_k(sb / sc, t, *o["zoom"])
    w = xfade(k, 1.7, 2.7)
    fr = m_grande("b", min(k, 3.0)) if w < 1 else None
    if w > 0:
        c = m_3x("c", sb / sc / k)
        fr = c if fr is None else Image.blend(fr, c, w)
    fr = fr.convert("RGBA")
    s = sb / k
    draw_dot(fr, s)
    draw_rings(fr, s, t, t0 + 0.2)
    return credit(fr)


def f_mapa_volta(o, t, t0, t1):
    """P7: volta o mapa A com a linha parada e o "?", abrindo devagar."""
    k = 1 + 0.05 * ease((t - t0) / (t1 - t0))
    fr = m_grande("a", k).convert("RGBA")
    lay, pos = route_reveal(1.0)
    full = Image.new("RGBA", (W, H))
    full.alpha_composite(lay, pos)
    fr.alpha_composite(scaled_layer(full, 1 / k))
    question(fr, t, -1, f=1 / k)
    return credit(fr)


# ---------------------------------------------------------------- planos: vídeo
class Reader:
    """Lê quadros RGB de um vídeo pelo ffmpeg (já no tamanho e no fps certos)."""

    def __init__(self, path, ss, dur, w, h, vf):
        self.w, self.h, self.last = w, h, None
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(path), "-vf", f"fps={FPS},{vf}", "-an",
             "-frames:v", str(int(math.ceil(dur * FPS)) + 1), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)

    def read(self):
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) == self.w * self.h * 3:
            self.last = Image.frombuffer("RGB", (self.w, self.h), buf, "raw", "RGB", 0, 1)
        return self.last

    def close(self):
        self.p.stdout.read()          # lê o que sobrou, para o ffmpeg terminar sem erro de pipe
        self.p.stdout.close()
        self.p.wait()


REEL_W, REEL_H, REEL_TOP = 820, 1458, 300          # o Reel em cartão (o texto que foi ao ar fica na área segura)


def f_reel(o, t, t0, t1):
    """P6: o Reel "Ajude encontrar a Zoe" (o vídeo original), em cartão sobre ink."""
    def bg():
        base = solid(INK).convert("RGBA")
        pad, r = 60, 26
        sh = Image.new("L", (W, H), 0)
        x0 = (W - REEL_W) // 2
        ImageDraw.Draw(sh).rounded_rectangle((x0, REEL_TOP + 30, x0 + REEL_W, REEL_TOP + REEL_H + 30), r, fill=170)
        base.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 0)] * 3, sh.filter(ImageFilter.GaussianBlur(40)))))
        mask = Image.new("L", (REEL_W, REEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, REEL_W - 1, REEL_H - 1), r, fill=255)
        return base.convert("RGB"), mask
    base, mask = cached("reelbg", bg)
    if "_rd" not in o:
        o["_rd"] = Reader(REEL, o["ss"], t1 - t0, REEL_W, REEL_H, f"scale={REEL_W}:{REEL_H}:flags=lanczos")
    rd = o["_rd"]
    fr = base.copy()
    fr.paste(rd.read(), ((W - REEL_W) // 2, REEL_TOP), mask)
    return fr


def f_hoje(o, t, t0, t1):
    """Fecho: a Zoe hoje, em casa. Entra saindo do preto."""
    if "_rd" not in o:
        o["_rd"] = Reader(HOJE, HOJE_SS + o.get("_off", 0), t1 - t0, W, H, f"scale={W}:{H}:flags=lanczos")
    rd = o["_rd"]
    return darken(rd.read(), ease((t - t0) / o.get("fade", 0.9)))


# ---------------------------------------------------------------- a montagem (SHOTS)
def shots():
    """(início, função, opções): cada plano vai até o início do próximo. Os tempos vêm das palavras."""
    sexta = cue("Na sexta mesmo") - 0.05           # o Uirapuru entra em "Na sexta mesmo"
    troca = cue("jornal") - 0.05                   # story → cartaz: a palavra mais perto do meio do P5
    return [
        # gancho (P1) — "A gente tava viajando quando a Zoe sumiu."
        # (a testa do Guilherme, y≈0,19 da foto, fica abaixo de y=440; o lábio da Isabela, y≈0,555, acima de 1125)
        (0.0, f_foto, {"src": "aviao", "win": ((1.05, -0.052), (1.03, -0.0471)), "cx": 0.6, "grad": True}),
        # cartela DIA 1 · SEX 18/09 (no respiro)
        (P1[0], f_ink, {}),
        # a fuga (P2) — "Ela ficou com uma pessoa de confiança e foi de carona pra creche."
        (P0[1], f_foto, {"src": "creche", "z": (1.0, 1.1), "f": (0.5, 0.35)}),
        # "Quando chegou, se assustou na rua, escapou da guia e disparou."
        (cue("Quando chegou") - 0.08, f_foto, {"src": "grama", "z": (1.0, 1.1), "f": (0.3, 0.45)}),
        # a linha (P3) — sobe a Tiradentes, chega na Lava Pés em "chegou na Lava Pés" e segue por ela, sem
        # parar, até a Fagundes dos Reis durante "Tentaram ir atrás, mas ela correu demais"; o "?" logo depois
        (cue("disparou", end=True) + 0.08, f_mapa_linha,
         {"linha": (cue("Subiu") + 0.12, cue("Lava Pés"), cue("demais", end=True) - 0.15),
          "q": cue("demais", end=True) + 0.05}),
        # os amigos (P4) — "Enquanto a gente tentava uma passagem de volta, nossos amigos..."
        # o "?" fica cheio até o zoom-out começar (1,25 s depois de entrar) e some no 1º segundo do zoom;
        # o fim do zoom não muda: a vista B chega antes de "Vários carros"
        (P0[3] - 0.25, f_mapa_bairro, {"zoom": (cue("demais", end=True) + 0.05 + 1.25, P0[3] + 5.5),
                                       "pulso": P0[3] + 3.2}),
        # o barulho (P5): um print por vez, inteiro e devagar, sem repetir: story → cartaz → Uirapuru
        (P0[4], f_cartao, {"card": "story"}),                                    # "E lá de longe ... divulgar:"
        (troca, f_cartao, {"card": "cartaz", "xf": ("story", P0[4], troca)}),    # "jornal, rádio, ... influenciadores."
        (sexta, f_cartao, {"card": "uirapuru", "xf": ("cartaz", troca, sexta)}),  # "Na sexta mesmo, ... rádio Uirapuru."
        # cartela DIA 2 · SÁB 19/09
        (P1[4] + 0.05, f_ink, {}),
        # dia 2 (P6) — "No sábado era aniversário do Guilherme."
        (P0[5], f_reel, {"ss": 0.3}),
        # "E foi a mesma coisa: uns cinco carros revirando a cidade inteira."
        (cue("E foi a mesma") - 0.05, f_mapa_cidade, {"zoom": (cue("uns cinco") - 0.6, cue("a cidade inteira"))}),
        # o silêncio (P7): tudo corta — "E nenhuma informação. Ninguém viu. Ninguém ouviu. A gente não tinha ideia de"
        (cut_time(), f_ink, {}),
        # "pra que lado ela foi."
        (cue("pra que lado") - 0.05, f_mapa_volta, {}),
        # a casa (P8) — "Era desespero puro. A gente só conseguia pensar"
        (P0[7] - 0.05, f_foto, {"src": "sofa", "left": 288 / 1113, "z": (1.095, 1.17), "f": (0.6, 0.4)}),
        # "que ia chegar em casa… e ela não ia estar lá." — escurece até o preto
        (cue("que ia chegar") - 0.05, f_foto, {"src": "bola", "c": (0.55, 0.5), "z": (1.02, 1.14), "f": (0.55, 0.45),
                                                "dark": (cue("em casa", end=True) - 0.2, cue("estar lá", end=True) + 0.05)}),
        # fecho: a Zoe hoje (1 s de silêncio, depois o som ambiente)
        (T_FECHO - 0.35, f_hoje, {"fade": 0.9}),
    ]


def cut_time():
    """O corte do P7 (imagem e trilha): logo depois de "a cidade inteira"."""
    return round(cue("cidade inteira", end=True) + 0.25, 3)


# ---------------------------------------------------------------- texto (ASS)
LIBASS_EM = 0.558      # no libass, o "em" da Poppins é ~0,558 x Fontsize (medido: a maiúscula tem ~0,41)
CAP_Y, CAP_MAXW = 1180, 800        # legendas: centro em x=540, sem entrar nos 130 px da direita
YEL, WHT = r"{\c&H00D7FF&}", r"{\c&HFFFFFF&}"
# contador: 6 segmentos no topo, abaixo da interface do Instagram (y ≈ 230)
SEG_X0, SEG_X1, SEG_Y, SEG_H, SEG_GAP = 130, 950, 252, 10, 14
SEG_W = (SEG_X1 - SEG_X0 - 5 * SEG_GAP) / 6


def tw(txt, fs, bold=False, spacing=0):
    """Largura aproximada do texto no libass (Poppins ExtraBold, ou Bold)."""
    f = cached(("font", bold), lambda: ImageFont.truetype(
        str(FONTS / ("Poppins-Bold.ttf" if bold else "Poppins-ExtraBold.ttf")), 200))
    return f.getlength(txt) * fs * LIBASS_EM / 200 + spacing * len(txt)


def ass_time(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def rrect(w, h, r):
    """Retângulo de cantos arredondados em desenho ASS (\\p1), com origem no canto superior esquerdo."""
    k = r * 0.4477
    return (f"m {r:.1f} 0 l {w - r:.1f} 0 b {w - k:.1f} 0 {w:.1f} {k:.1f} {w:.1f} {r:.1f} "
            f"l {w:.1f} {h - r:.1f} b {w:.1f} {h - k:.1f} {w - k:.1f} {h:.1f} {w - r:.1f} {h:.1f} "
            f"l {r:.1f} {h:.1f} b {k:.1f} {h:.1f} 0 {h - k:.1f} 0 {h - r:.1f} l 0 {r:.1f} b 0 {k:.1f} {k:.1f} 0 {r:.1f} 0")


def arrow(w, h, t):
    """Seta → em desenho ASS: haste de espessura t e ponta com a altura h."""
    hd = h * 0.62
    return (f"m 0 {h / 2 - t / 2:.1f} l {w - hd:.1f} {h / 2 - t / 2:.1f} l {w - hd - t * 0.2:.1f} 0 "
            f"l {w:.1f} {h / 2:.1f} l {w - hd - t * 0.2:.1f} {h:.1f} l {w - hd:.1f} {h / 2 + t / 2:.1f} "
            f"l 0 {h / 2 + t / 2:.1f}")


def cap_word(w):
    return w["w"].rstrip(".,:…").upper()


# palavras que não devem fechar um bloco: artigos e preposições (peso maior) e outras curtas
SOLTAS = {w: 1.2 for w in ("a", "o", "e", "de", "da", "do", "na", "no", "pra", "para", "com", "um", "uma",
                           "uns", "as", "os", "se")}
SOLTAS.update({w: 0.4 for w in ("que", "eu", "ia", "já", "não", "só", "mas", "quando", "ela", "era")})


def cap_chunks(words):
    """Blocos de até 3 palavras que caibam na largura. Quebra na pontuação e nas pausas da fala e,
    dentro de cada frase, escolhe a divisão com menos blocos, evitando bloco que termina em palavra
    solta ("revirando a | cidade inteira") e bloco de uma palavra curta."""
    phrases, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if w["w"][-1] in ".,:…" or (nxt and nxt["s"] - w["e"] > 0.25):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)

    def cost(p, last):
        if len(p) > 1 and tw(" ".join(cap_word(x) for x in p), 124) > CAP_MAXW:
            return None
        c = 1.0
        if not last:
            c += SOLTAS.get(_norm(p[-1]["w"]), 0.0)
        if len(p) == 1 and len(cap_word(p[0])) < 8:
            c += 0.5
        return c

    out = []
    for ph in phrases:
        n = len(ph)
        best = [(0.0, [])] + [(math.inf, None)] * n     # melhor divisão das i primeiras palavras
        for i in range(1, n + 1):
            for k in (1, 2, 3):
                if k <= i and best[i - k][1] is not None:
                    c = cost(ph[i - k:i], i == n)
                    if c is not None and best[i - k][0] + c < best[i][0]:
                        best[i] = (best[i - k][0] + c, best[i - k][1] + [ph[i - k:i]])
        out += best[n][1]
    return out


def build_ass(path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins ExtraBold,124,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,8,4,5,60,60,0
Style: Hook,Poppins ExtraBold,170,&H00E9F1F6,&H00E9F1F6,&H001F1317,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,40,40,0
Style: HookSub,Poppins ExtraBold,93,&H00F3A7B9,&H00F3A7B9,&H001F1317,&H00000000,-1,0,0,0,100,100,4,0,1,0,0,5,40,40,0
Style: Dia,Poppins ExtraBold,300,&H00E9F1F6,&H00E9F1F6,&H001F1317,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,40,40,0
Style: Data,Poppins ExtraBold,112,&H00F3A7B9,&H00F3A7B9,&H001F1317,&H00000000,-1,0,0,0,100,100,6,0,1,0,0,5,40,40,0
Style: Big,Poppins ExtraBold,310,&H00E9F1F6,&H00E9F1F6,&H001F1317,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,40,40,0
Style: Chip,Poppins ExtraBold,46,&H001F1317,&H001F1317,&H00F3A7B9,&H00000000,-1,0,0,0,100,100,1,0,3,14,0,5,40,40,0
Style: Fecho,Poppins ExtraBold,84,&H00E9F1F6,&H00E9F1F6,&H001F1317,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,4,40,40,0
Style: Handle,Poppins,50,&H4DE9F1F6,&H4DE9F1F6,&H801F1317,&H801F1317,-1,0,0,0,100,100,1,0,1,3,0,5,40,40,0
Style: Draw,Poppins,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []

    def add(s, e, style, txt, layer=1):
        ev.append(f"Dialogue: {layer},{ass_time(s)},{ass_time(e)},{style},,0,0,0,,{txt}")

    sh = shots()
    starts = [s[0] for s in sh]

    def shot_end(t0):
        i = starts.index(t0)
        return sh[i + 1][0] if i + 1 < len(sh) else DUR

    # --- legendas (no P7, "Ninguém viu. Ninguém ouviu." viram texto grande e saem da legenda)
    n0, n1 = cue("Ninguém viu"), cue("Ninguém ouviu", end=True)
    words = [w for w in _WORDS if not (n0 - 0.01 <= w["s"] <= n1)]
    chunks = cap_chunks(words)
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else DUR
        last_end = nxt if nxt - ch[-1]["e"] < 0.6 else ch[-1]["e"] + 0.35
        full = " ".join(cap_word(x) for x in ch)
        k = min(1.0, CAP_MAXW / max(tw(full, 124), 1))
        fit = rf"\fscx{k * 100:.0f}\fscy{k * 100:.0f}" if k < 1 else ""
        for wi, w in enumerate(ch):
            s = w["s"]
            e = ch[wi + 1]["s"] if wi + 1 < len(ch) else last_end
            txt = " ".join((YEL + cap_word(x) + WHT) if j == wi else cap_word(x) for j, x in enumerate(ch))
            if wi == 0:
                tag = (rf"{{\pos(540,{CAP_Y})\fscx{108 * k:.0f}\fscy{108 * k:.0f}"
                       rf"\t(0,90,\fscx{k * 100:.0f}\fscy{k * 100:.0f})}}")
            else:
                tag = rf"{{\pos(540,{CAP_Y}){fit}}}"
            add(s, e, "Cap", tag + txt, 3)

    # --- contador de dias: 6 segmentos vazios desde o gancho; enche nas cartelas
    def seg(i):
        return SEG_X0 + i * (SEG_W + SEG_GAP)
    for i in range(6):
        add(0, DUR, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(CREAM)}\1a&HBF&\fad(250,0)\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 0)
    for i, tf in enumerate(FILLS()):
        x = seg(i)
        clip0 = rf"\clip({x:.0f},{SEG_Y - 20},{x:.0f},{SEG_Y + SEG_H + 20})"
        clip1 = rf"\clip({x:.0f},{SEG_Y - 20},{x + SEG_W:.0f},{SEG_Y + SEG_H + 20})"
        add(tf, DUR, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}{clip0}\t(0,450,{clip1})\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
        # brilho curto enquanto enche
        add(tf, tf + 1.2, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}\1a&H60&\blur8{clip0}"
            rf"\t(0,450,{clip1})\fad(0,500)\p1}}" + rrect(SEG_W, SEG_H, SEG_H / 2), 1)

    # --- gancho no topo: duas linhas (maiúscula ~70 px e ~38 px), sem caixa; o degradê ink vem da foto
    # (no libass o centro da maiúscula fica ~0,06 x Fontsize acima do \pos)
    pop = r"\fad(0,150)\fscx102\fscy102\t(0,160,\fscx100\fscy100)"
    add(0, P0[1], "Hook", rf"{{\pos(540,{327 + 0.0605 * 170:.0f}){pop}}}OS 6 DIAS DA ZOE", 4)
    add(0, P0[1], "HookSub", rf"{{\pos(540,{403 + 0.0605 * 93:.0f}){pop}}}PARTE 1", 4)

    # --- cartelas
    for (t0, t1), dia, data in (((P1[0], P0[1]), "DIA 1", "SEX 18/09"),
                                ((P1[4] + 0.05, P0[5]), "DIA 2", "SÁB 19/09")):
        add(t0 + 0.04, t1, "Dia", r"{\move(540,905,540,880,0,220)\fad(120,90)}" + dia, 2)
        add(t0 + 0.12, t1, "Data", r"{\move(540,1060,540,1040,0,220)\fad(120,90)}" + data, 2)

    # --- etiquetas de horário nos prints (story 13h40 e cartaz 20h43)
    chips = {"story": ("SEX 18/09 · 13H40", 330), "cartaz": ("SEX 18/09 · 20H43", 380)}
    for t0, fn, o in sh:
        if fn is f_cartao and o["card"] in chips:
            txt, y = chips[o["card"]]
            # sai junto com o crossfade para o próximo print
            add(t0 + 0.12, shot_end(t0) + XF, "Chip", rf"{{\pos(700,{y})\frz3\fad(80,{XF * 1000:.0f})\fscx112\fscy112"
                rf"\t(0,120,\fscx100\fscy100)}}" + txt, 4)

    # --- o silêncio: "NINGUÉM" / "VIU." e depois "NINGUÉM" / "OUVIU.", em duas linhas (maiúscula ~127 px),
    # cada palavra no seu tempo; o segundo bloco substitui o primeiro. Some com fade quando a legenda volta.
    fade = cue("A gente não tinha")
    blocks = [(cue("Ninguém viu"), cue("viu"), cue("Ninguém ouviu"), "VIU.", "0"),
              (cue("Ninguém ouviu"), cue("ouviu"), fade + 0.4, "OUVIU.", "400")]
    for t_a, t_b, t_end, second, out in blocks:
        for txt, t_in, cap_y in (("NINGUÉM", t_a, 673.5), (second, t_b, 846.5)):     # bloco centrado em y≈760
            k = min(1.0, 900 / tw(txt, 310))
            add(t_in, t_end, "Big", rf"{{\pos(540,{cap_y + 0.0605 * 310:.0f})\fscx{106 * k:.0f}\fscy{106 * k:.0f}"
                rf"\t(0,140,\fscx{100 * k:.0f}\fscy{100 * k:.0f})\fad(60,{out})}}" + txt, 2)

    # --- fecho: PARTE 2 · DIAS 3 E 4 → e o @
    ft, fs = "PARTE 2 · DIAS 3 E 4", 84
    txt_w = tw(ft, fs, spacing=1)
    aw, ah, gap, padx, bh = 66, 48, 26, 46, 136
    bw = txt_w + gap + aw + 2 * padx
    bx, by = 540 - bw / 2, 1290 - bh / 2
    t_in = T_FECHO + 0.55
    add(t_in, DUR, "Draw", rf"{{\pos({bx:.1f},{by:.1f})\1c{ass_c(INK)}\1a&H1A&\fad(250,0)\p1}}" + rrect(bw, bh, 22), 5)
    add(t_in, DUR, "Fecho", rf"{{\an4\pos({bx + padx:.1f},1292)\fad(250,0)}}" + ft, 6)
    add(t_in, DUR, "Draw", rf"{{\pos({bx + padx + txt_w + gap:.1f},{1290 - ah / 2:.1f})\1c{ass_c(PINK)}"
        rf"\fad(250,0)\p1}}" + arrow(aw, ah, 13), 6)
    add(t_in + 0.3, DUR, "Handle", rf"{{\pos(540,{by + bh + 58:.0f})\fad(300,0)}}" + HANDLE, 6)

    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


def FILLS():
    """Quando cada segmento do contador enche: nas cartelas DIA 1 e DIA 2."""
    return [P1[0] + 0.15, P1[4] + 0.2]


# ---------------------------------------------------------------- áudio
def ff(args):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", *[str(a) for a in args]], check=True)


def loudness(path):
    """Loudness integrada (LUFS) e pico (dBFS) pelo ebur128."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    return i, float(p.group(1)) if p and p.group(1) != "-inf" else -99.0


def music_marks():
    sexta = cue("Na sexta mesmo") - 0.05
    bar = 4 * trilha_03.BEAT
    return {
        "t0": sexta - bar * math.floor(sexta / bar),     # grade da trilha: "Na sexta mesmo" cai num 1º tempo
        "pulse": P0[4] - 0.2,                            # o pulso entra com o P5
        "noise": cue("jornal") - 0.1,                    # semicolcheias na lista
        "friday": sexta,
        "cut": cut_time(),                               # zera no P7
        "fecho": T_FECHO + 0.05,                         # volta baixinha no fecho
        "end": DUR,
        "chimes": FILLS(),                               # o contador enchendo
    }


MUSIC_DB = -8.0         # trilha em relação à voz, antes do duck (a voz tira ~6 dB dela)
AMB_DB = 8.0            # ambiente do fecho (o som original é bem baixo)


def build_audio():
    """voz.wav → mixagem com trilha e sem trilha, as duas em -14 LUFS."""
    voz, pre, pre_nat = WORK / "voz.wav", WORK / "mix-pre.wav", WORK / "mix-sem-musica-pre.wav"
    ins, fc = [], []
    for k, (f, a, b) in enumerate(PARTS):
        ins += ["-i", AUD / f"{f}.ogg"]
        d = b - a - _removed(f, b)
        segs = _segments(f, a, b)
        if len(segs) == 1:
            src = f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS"
        else:                             # tira o silêncio de dentro (CUTS) e emenda os trechos
            names = "".join(f"[c{k}_{j}]" for j in range(len(segs)))
            fc.append(f"[{k}:a]asplit={len(segs)}{names}")
            for j, (s0, s1) in enumerate(segs):
                fc.append(f"[c{k}_{j}]atrim=start={s0}:end={s1},asetpts=PTS-STARTPTS[t{k}_{j}]")
            src = "".join(f"[t{k}_{j}]" for j in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1"
        fc.append(f"{src},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"
                  f"afade=t=in:d=0.015,afade=t=out:st={d - 0.04:.3f}:d=0.04[p{k}]")
    for k, g in enumerate([LEAD] + GAPS):
        fc.append(f"aevalsrc=0:s=48000:d={g},aformat=sample_fmts=fltp:channel_layouts=mono[g{k}]")
    seq = "".join(f"[g{k}][p{k}]" for k in range(len(PARTS)))
    fc.append(f"{seq}concat=n={2 * len(PARTS)}:v=0:a=1,highpass=f=80,afftdn=nf=-25,"
              f"acompressor=threshold=0.1:ratio=2.5:attack=10:release=150,apad=whole_dur={DUR}[v]")
    ff([*ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", DUR, "-c:a", "pcm_s16le", voz])

    trilha_03.render(MUSIC, music_marks())
    vi, _ = loudness(voz)
    mi, _ = loudness(MUSIC)
    mg = vi + MUSIC_DB - mi
    ms = int(T_FECHO * 1000)
    amb = (f"[2:a]aresample=48000,aformat=channel_layouts=stereo,highpass=f=120,lowpass=f=9000,"
           f"volume={AMB_DB}dB,afade=t=in:d=0.8,afade=t=out:st={FECHO - 1.3:.2f}:d=1.2,adelay={ms}|{ms},"
           f"apad=whole_dur={DUR}[amb]")
    hoje = ["-ss", HOJE_SS + 0.35, "-t", FECHO, "-i", HOJE]
    # com trilha: a voz empurra a trilha para baixo (sidechain)
    fc = (f"[0:a]pan=stereo|c0=c0|c1=c0,asplit=2[v][key];"
          f"[1:a]aresample=48000,volume={mg:.2f}dB[m];"
          f"[m][key]sidechaincompress=threshold=0.02:ratio=2.5:attack=25:release=400:makeup=1[md];{amb};"
          f"[v][md][amb]amix=inputs=3:normalize=0:duration=first[out]")
    ff(["-i", voz, "-i", MUSIC, *hoje, "-filter_complex", fc, "-map", "[out]", "-t", DUR, "-c:a", "pcm_s16le", pre])
    fc = f"[0:a]pan=stereo|c0=c0|c1=c0[v];{amb.replace('[2:a]', '[1:a]')};[v][amb]amix=inputs=2:normalize=0:duration=first[out]"
    ff(["-i", voz, *hoje, "-filter_complex", fc, "-map", "[out]", "-t", DUR, "-c:a", "pcm_s16le", pre_nat])
    outs = []
    for src in (pre, pre_nat):
        i, _ = loudness(src)
        dst = src.with_name(src.name.replace("-pre", ""))
        ff(["-i", src, "-af", f"volume={-14 - i:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled",
            "-c:a", "pcm_s16le", dst])
        li, lp = loudness(dst)
        print(f"{dst.name}: {li:.1f} LUFS, pico {lp:.1f} dBFS (voz {vi:.1f} LUFS, trilha {mg:+.1f} dB)")
        outs.append(dst)
    return outs


# ---------------------------------------------------------------- vídeo
def fpath(p):
    # caminho para dentro do filtergraph: no Windows, "C:\..." quebra o parser do ffmpeg
    return Path(p).resolve().as_posix().replace(":", r"\:")


def render(mix, out, t_from=0.0, t_to=None):
    t_to = DUR if t_to is None else min(t_to, DUR)
    sh = shots()
    starts = [s[0] for s in sh]
    assert starts == sorted(starts), "SHOTS fora de ordem"
    vf = (f"[0:v]setpts=PTS+{t_from}/TB,subtitles='{fpath(ASS)}':fontsdir='{fpath(FONTS)}',setpts=PTS-STARTPTS,"
          f"scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", f"{t_from}", "-i", str(mix), "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{t_to - t_from:.3f}", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    cur = None
    for n in range(n0, n1):
        t = n / FPS
        i = max(k for k, s in enumerate(starts) if s <= t + 1e-6)
        t0, fn, o = sh[i]
        t1 = sh[i + 1][0] if i + 1 < len(sh) else DUR
        if cur is not None and cur is not o and "_rd" in cur:
            cur.pop("_rd").close()
        cur = o
        if "_off" not in o:                       # render parcial começando no meio de um vídeo
            o["_off"] = t - t0
            if fn is f_reel:
                o["ss"] += o["_off"]
        fr = fn(o, t, t0, t1)
        proc.stdin.write(fr.convert("RGB").tobytes())
        if n % 150 == 0:
            print(f"  {t:5.1f}/{t_to:.1f} s", flush=True)
    if cur is not None and "_rd" in cur:
        cur.pop("_rd").close()
    proc.stdin.close()
    if proc.wait():
        raise SystemExit("ffmpeg falhou")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "palavras":
        return palavras()
    prep()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    build_ass(ASS)
    print("linha do tempo:", " | ".join(f"P{i + 1} {a:.2f}-{b:.2f}" for i, (a, b) in enumerate(zip(P0, P1))),
          f"| fecho {T_FECHO:.2f} | fim {DUR:.2f}")
    mix, mix_nat = build_audio()
    if len(sys.argv) > 2:
        t_from, t_to = float(sys.argv[1]), float(sys.argv[2])
        render(mix, WORK / "trecho.mp4", t_from, t_to)
        print(WORK / "trecho.mp4")
        return
    render(mix, OUT)
    ff(["-i", OUT, "-i", mix_nat, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", f"{DUR:.3f}", OUT_NAT])
    print(OUT)
    print(OUT_NAT)


if __name__ == "__main__":
    main()
