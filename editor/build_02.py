"""Monta o Reel 'Como encontraram a Zoe?' (9:16, ~57s) — história contada por texto na tela.

Sem narração gravada: os textos carregam a história; o áudio real entra no gancho e no reencontro.
Gera duas versões: com trilha de referência (sintetizada aqui) e sem trilha (para usar música no app).

Uso: python3 editor/build_02.py
"""
import math, struct, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
V = ROOT / "videos"
EF, CF = ROOT / "editor" / "fonts", ROOT / "carrossel" / "fonts"
OUTDIR = ROOT / "saida" / "video" / "video2"
TMP = ROOT / "editor" / ".tmp-02"          # overlays e trilha (regenerados a cada build)
W, H, FPS = 1080, 1920, 30

CREAM, LILAC, PINK = (246, 241, 233), (185, 167, 243), (236, 72, 153)

# ── Takes ────────────────────────────────────────────────────────────────────
# (arquivo, início no clipe, início na linha do tempo, opções)
#   fx/fy: foco do recorte (0..1)  z: zoom  pan: deslocamento horizontal ao longo do take
#   fit: foto inteira sobre fundo desfocado  doc: dessaturado (material de busca)  spd: velocidade
SHOTS = [
    ("VID-20260924-WA0172.mp4", 0.9, 0.00, dict(z=1.08)),                  # gancho: Zoe pulando na Isabela
    ("d8113f49-408d-478b-b508-2f8d043188ab.JPG", 0, 2.60, dict(fit=1, doc=1, blur_contact=1)),  # cartaz
    ("0db16a59-2cdf-4b30-a9c9-4d234b85e595.JPG", 0, 3.55, dict(fit=1, doc=1)),   # raio de 3 km
    ("cdf8adaa-2d56-4586-b22b-6daffb22db11.MP4", 0.4, 4.45, dict(doc=1)),        # câmeras no celular
    ("ca9e1666-7f2d-4da0-8c19-fa0a569ac37b.JPG", 0, 5.35, dict(fit=1, doc=1)),   # trajeto da busca
    ("f1db99c8-942b-485d-b437-da424eb1e6ed.MP4", 2.0, 6.25, dict(doc=1, fx=0.4)),  # DVR
    (None, 0, 7.20, {}),                                                    # preto: 6 DIAS DEPOIS / UMA LIGAÇÃO
    ("VID-20260924-WA0156.mp4", 0.0, 9.60, dict(doc=1, rec=1, fx=0.8, pan=-160)),   # Instituto, câmera 06
    ("VID-20260924-WA0156.mp4", 12.0, 15.60, dict(doc=1, rec=1, fx=1.0, z=1.35, pan=-90)),  # mato à direita
    ("VID-20260924-WA0156.mp4", 17.0, 18.60, dict(doc=1, rec=1, fx=0.9, fy=0.2, z=1.7, pan=-80)),
    (None, 0, 22.00, {}),                                                   # preto: NADA.
    ("VID-20260924-WA0160.mp4", 0.0, 23.20, dict(doc=1, rec=1, z=1.25, spd=0.55)),  # a câmera
    ("VID-20260924-WA0171.mp4", 4.8, 27.80, dict(fy=1.0, z=1.9, fx=0.15, pan=160)),   # o mato (campo do reencontro)
    ("VID-20260924-WA0171.mp4", 14.0, 31.90, dict(fy=1.0, z=2.2, fx=0.0, pan=120)),
    (None, 0, 36.00, {}),                                                   # preto: ZOE!
    ("VID-20260924-WA0197.mp4", 4.6, 37.20, dict(z=1.05)),                  # ela ali, na coleira
    ("VID-20260924-WA0197.mp4", 8.3, 39.40, dict(z=1.05)),                  # "Zuzu! Meu amor!"
    ("VID-20260924-WA0171.mp4", 6.4, 42.40, dict(z=1.15, fx=0.55)),         # Guilherme abraçando
    ("IMG-20260924-WA0174.jpg", 0, 45.40, dict(z=1.08, pan=-60)),           # ela sorrindo
    ("IMG_8348.MOV", 16.5, 47.20, dict(z=1.05)),                            # em casa, no sol
    ("IMG_8337.MOV", 22.0, 49.80, dict(z=1.05)),                            # dormindo
    ("IMG_8343.jpg", 0, 52.20, dict(z=1.06, fy=0.35, dim=1)),               # na janela: tela final
]
DUR = 58.2

# ── Textos ───────────────────────────────────────────────────────────────────
# (início, fim, estilo, texto)   estilos: hook, big, line, small, end*
TEXTS = [
    (0.05, 2.55, "hook", "COMO ENCONTRARAM|A ZOE?"),
    (2.70, 7.10, "big", "6 DIAS|PROCURANDO"),
    (7.35, 8.45, "big", "6 DIAS DEPOIS,"),
    (8.45, 9.55, "big", "UMA LIGAÇÃO."),
    (9.75, 11.95, "line", "Uma veterinária que acompanhava a história"),
    (11.95, 14.00, "line", "viu uma cachorrinha preta saindo do mato"),
    (14.00, 15.55, "line", "perto do Instituto Menino Deus."),
    (15.65, 17.10, "line", "Ela chamou. A cachorrinha correu."),
    (17.10, 18.55, "line", "E ligou pra Isabela."),
    (18.70, 20.40, "line", "Quem já estava nas buscas foi direto pra lá."),
    (20.40, 21.95, "line", "Procuraram. Chamaram. Entraram no mato."),
    (22.15, 23.15, "big", "NADA."),
    (23.30, 25.70, "line", "Até que uma câmera mostrou, por uma fração de segundo, uma cachorrinha."),
    (25.70, 27.75, "big", "ERA ELA?"),
    (27.90, 29.90, "line", "Ninguém tinha certeza. A Isabela foi pra lá."),
    (29.90, 31.85, "line", "Entrou no mato chamando e assoviando."),
    (31.95, 33.70, "line", "O Guilherme procurava por outro acesso."),
    (33.70, 35.95, "line", "Já iam pra outra parte quando ela viu uma cachorrinha correndo lá na frente."),
    (36.05, 37.15, "zoe", "ZOE!"),
    (37.30, 38.30, "small", "Ela correu mais um pouco."),
    (38.30, 39.35, "small", "Parou."),
    (39.55, 41.60, "big", "ELA VEIO."),
    (43.00, 45.00, "small", "Era ela."),
    (47.40, 49.70, "line", "Depois de seis dias, a Zoe voltou pra casa."),
    (49.95, 52.10, "line", "Porque alguém que acompanhava a história viu, reconheceu e avisou."),
    (52.40, 55.20, "end1", ""),
    (55.20, DUR, "end2", ""),
]

# ── Áudio real (arquivo, início no clipe, início na linha do tempo, duração, ganho dB) ──
AUDIO = [
    ("VID-20260924-WA0172.mp4", 0.9, 0.00, 2.60, -4),     # "Tá, pega!"
    ("VID-20260924-WA0197.mp4", 4.6, 37.20, 2.20, -12),   # ambiente do campo
    ("VID-20260924-WA0197.mp4", 8.3, 39.40, 3.00, -2),    # "Zuzu! Meu amor!"
    ("VID-20260924-WA0171.mp4", 6.4, 42.40, 3.00, -16),   # vento do campo
]


def font(name, size):
    p = (EF / name) if (EF / name).exists() else (CF / name)
    return ImageFont.truetype(str(p), size)


def wrap(draw, text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def fit_font(name, size, lines, maxw=940):
    """Reduz o corpo até a linha mais longa caber na largura útil."""
    while True:
        f = font(name, size)
        if max(f.getlength(l) for l in lines) <= maxw or size <= 40:
            return f
        size -= 4


def draw_block(img, lines, fnt, cy, fill, lh=1.12, glow=14, colors=None, top=None):
    """Desenha linhas centralizadas em cy (ou a partir de top), com sombra difusa por trás."""
    d = ImageDraw.Draw(img)
    asc, desc = fnt.getmetrics()
    step = int((asc + desc) * lh)
    y0 = int(top if top is not None else cy - step * len(lines) / 2)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, ln in enumerate(lines):
        x = (W - d.textlength(ln, font=fnt)) / 2
        sd.text((x, y0 + i * step + 4), ln, font=fnt, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(glow))
    img.alpha_composite(shadow)
    img.alpha_composite(shadow)
    for i, ln in enumerate(lines):
        x = (W - d.textlength(ln, font=fnt)) / 2
        d.text((x, y0 + i * step), ln, font=fnt, fill=(colors[i] if colors else fill))
    return y0 + step * len(lines)


def emoji(ch, size):
    f = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)


def render_text(style, text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if style == "hook":
        l1, l2 = text.split("|")
        f = fit_font("Poppins-ExtraBold.ttf", 104, [l1, l2])
        draw_block(img, [l1, l2], f, 470, CREAM, lh=1.0, colors=[CREAM, LILAC])
    elif style == "big":
        f = fit_font("Poppins-ExtraBold.ttf", 150, text.split("|"))
        draw_block(img, text.split("|"), f, 900, CREAM, lh=1.0)
    elif style == "zoe":
        f = font("Poppins-ExtraBold.ttf", 300)
        draw_block(img, [text], f, 900, PINK, glow=24)
    elif style == "line":
        f = font("Poppins-Bold.ttf", 66)
        draw_block(img, wrap(d, text, f, 880), f, 1180, CREAM)
    elif style == "small":
        f = font("Poppins-SemiBold.ttf", 64)
        draw_block(img, [text], f, 1250, CREAM)
    elif style in ("end1", "end2"):
        # degradê escuro no alto: o texto fica acima da Zoe, que olha pela janela
        grad = Image.new("L", (1, H))
        for yy in range(H):
            grad.putpixel((0, yy), int(215 * max(0.0, 1 - yy / 1150) ** 0.8))
        shade = Image.new("RGBA", (W, H), (23, 19, 31, 255))
        shade.putalpha(grad.resize((W, H)))
        img.alpha_composite(shade)
        if style == "end1":
            f1, f2 = font("Poppins-SemiBold.ttf", 56), font("Poppins-ExtraBold.ttf", 80)
            y = draw_block(img, ["6 dias procurando a Zoe."], f1, 0, CREAM, top=330)
            y = draw_block(img, ["Uma pessoa prestando", "atenção ajudou a", "mudar o final."],
                           f2, 0, CREAM, lh=1.06, top=y + 40)
            draw_block(img, ["@souazoe.pf"], font("Poppins-SemiBold.ttf", 44), 0, LILAC, glow=8, top=y + 40)
        else:
            f1 = font("Poppins-ExtraBold.ttf", 88)
            f2 = font("Caveat.ttf", 112)
            y = draw_block(img, ["Você também", "me procurou?"], f1, 0, CREAM, lh=1.02, top=320)
            y = draw_block(img, ["Agora já sabe onde", "me encontrar"], f2, 0, PINK, lh=0.92, glow=10, top=y + 36)
            paw = emoji("🐾", 88)
            last_w = d.textlength("me encontrar", font=f2)
            img.alpha_composite(paw, (int((W + last_w) / 2 + 34), int(y - paw.height - 28)))
            # pílula "siga @souazoe.pf"
            f3 = font("Poppins-Bold.ttf", 58)
            label = "siga @souazoe.pf"
            tw = d.textlength(label, font=f3)
            bx0, by0 = (W - tw) / 2 - 44, y + 40
            d.rounded_rectangle((bx0, by0, bx0 + tw + 88, by0 + 108), radius=54, fill=CREAM)
            d.text((bx0 + 44, by0 + 16), label, font=f3, fill=(23, 19, 31))
    img.save(path)


def render_rec(path):
    """Selo discreto de câmera de segurança (canto superior esquerdo, fora da área da UI)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((70, 262, 102, 294), fill=(230, 40, 40))
    d.text((118, 252), "REC", font=font("Poppins-Bold.ttf", 44), fill=CREAM)
    img.save(path)


def prep_still(src, opts, path):
    """Fotos: 'fit' = foto inteira sobre fundo desfocado; senão só corrige a orientação."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if opts.get("blur_contact"):   # esconde os telefones do cartaz
        w, h = im.size
        box = (0, int(h * 0.855), w, h)
        im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(28)), box[:2])
    if not opts.get("fit"):
        im.save(path, quality=94); return
    bg = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda v: int(v * 0.45))
    fg = im.copy(); fg.thumbnail((960, 1500), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2 - 60))
    bg.save(path, quality=94)


# ── Trilha de referência ─────────────────────────────────────────────────────
def synth_score(path, sr=44100):
    """Pad grave + pulso tipo batimento que acelera; silêncio no "ZOE!"; acorde maior no alívio."""
    def hz(n): return 440 * 2 ** ((n - 69) / 12)
    tension = [hz(45), hz(52), hz(57), hz(60)]          # Lá menor (A2 E3 A3 C4)
    relief = [hz(41), hz(48), hz(57), hz(60), hz(64)]   # Fá maior com 9ª → luz (F2 C3 A3 C4 E4)
    n = int(DUR * sr)
    buf = bytearray()
    ph_beat = 0.0
    for i in range(n):
        t = i / sr
        s = 0.0
        if t < 36.0:
            amp = 0.05 + 0.07 * min(t / 36, 1)                       # cresce devagar
            fade = min(t / 1.5, 1) * min(max((36.0 - t) / 0.25, 0), 1)
            for k, f in enumerate(tension):
                s += math.sin(2 * math.pi * f * t + k) * (1.0 if k < 2 else 0.5)
                s += 0.3 * math.sin(2 * math.pi * f * 1.003 * t)
            s *= amp * fade * (0.85 + 0.15 * math.sin(2 * math.pi * 0.25 * t))
            if t > 9.6:                                               # batimento a partir da ligação
                bpm = 64 + 34 * (t - 9.6) / 26.4
                ph_beat += bpm / 60 / sr
                x = ph_beat % 1.0
                for off in (0.0, 0.22):
                    dt = x - off
                    if 0 <= dt < 0.18:
                        s += 0.22 * math.sin(2 * math.pi * 52 * dt) * math.exp(-dt * 28) * fade
        elif t >= 38.3:
            env = min((t - 38.3) / 3.0, 1) * min((DUR - t) / 2.0, 1)
            for k, f in enumerate(relief):
                s += math.sin(2 * math.pi * f * t + k) * (1.0 if k < 2 else 0.6)
                s += 0.3 * math.sin(2 * math.pi * f * 0.997 * t)
            # arpejo suave de "caixinha" no final
            if t > 45.4:
                notes = [hz(72), hz(76), hz(79), hz(84)]
                step = 0.5
                j = int((t - 45.4) / step)
                dt = (t - 45.4) - j * step
                s += 0.9 * math.sin(2 * math.pi * notes[j % 4] * t) * math.exp(-dt * 5)
            s *= 0.07 * env
        v = max(-1.0, min(1.0, s))
        buf += struct.pack("<h", int(v * 32000))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(bytes(buf))


# ── Montagem ─────────────────────────────────────────────────────────────────
def shot_filter(i, f, opts, d, src_is_img):
    z = opts.get("z", 1.1)
    fx, fy, pan = opts.get("fx", 0.5), opts.get("fy", 0.5), opts.get("pan", 70)
    spd = opts.get("spd", 1.0)
    cw, ch = int(W * z) // 2 * 2, int(H * z) // 2 * 2
    # posição x vai de x0 até x0+pan ao longo do take (pan lento), limitada à imagem
    x = f"max(0,min(iw-{W},(iw-{W})*{fx}+({pan})*(t/{d:.3f}-0.5)))"
    y = f"max(0,min(ih-{H},(ih-{H})*{fy}))"
    chain = [f"scale={cw}:{ch}:force_original_aspect_ratio=increase:force_divisible_by=2"]
    if spd != 1.0:
        chain.insert(0, f"setpts=PTS/{spd}")
    chain += [f"fps={FPS}", f"crop={W}:{H}:x='{x}':y='{y}'"]
    if opts.get("doc"):
        chain.append("eq=saturation=0.35:contrast=1.06:brightness=-0.02,vignette=PI/5")
    else:
        chain.append("eq=saturation=1.05:contrast=1.02")
    if opts.get("dim"):
        chain.append("eq=brightness=-0.16:saturation=0.9")
    chain += ["setsar=1", f"trim=duration={d:.3f}", "setpts=PTS-STARTPTS", "format=yuv420p"]
    return f"[{i}:v]" + ",".join(chain) + f"[v{i}]"


def build(with_score=True):
    TMP.mkdir(exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    inputs, parts = [], []
    rec_ranges = []
    for i, (f, ss, t0, opts) in enumerate(SHOTS):
        t1 = SHOTS[i + 1][2] if i + 1 < len(SHOTS) else DUR
        d = t1 - t0
        if f is None:
            inputs += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", f"color=c=0x17131F:s={W}x{H}:r={FPS}"]
            parts.append(f"[{i}:v]setsar=1,format=yuv420p[v{i}]")
            continue
        src = V / f
        is_img = f.lower().endswith((".jpg", ".png"))
        if is_img:
            p = TMP / f"still{i}.jpg"
            prep_still(src, opts, p)
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(p)]
        else:
            inputs += ["-ss", f"{ss}", "-t", f"{d * opts.get('spd', 1.0) + 0.1:.3f}", "-i", str(src)]
        parts.append(shot_filter(i, f, opts, d, is_img))
        if opts.get("rec"):
            rec_ranges.append((t0, t1))
    n = len(SHOTS)
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[base]")

    # overlays de texto
    idx, last = n, "base"
    render_rec(TMP / "rec.png")
    overlays = [(t0, t1, TMP / "rec.png", False) for t0, t1 in rec_ranges]
    for k, (t0, t1, style, text) in enumerate(TEXTS):
        p = TMP / f"txt{k:02d}.png"
        render_text(style, text, p)
        overlays.append((t0, t1, p, True))
    for k, (t0, t1, p, fade) in enumerate(overlays):
        d = t1 - t0
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(p)]
        fl = f"[{idx}:v]format=rgba"
        if fade:
            fl += f",fade=in:st=0:d=0.14:alpha=1,fade=out:st={max(d - 0.14, 0):.3f}:d=0.14:alpha=1"
        fl += f",setpts=PTS-STARTPTS+{t0:.3f}/TB[o{k}]"
        parts.append(fl)
        parts.append(f"[{last}][o{k}]overlay=0:0:eof_action=pass:enable='between(t,{t0:.3f},{t1:.3f})'[b{k}]")
        last = f"b{k}"
        idx += 1

    # áudio
    alabels = []
    for k, (f, ss, t0, d, g) in enumerate(AUDIO):
        inputs += ["-ss", f"{ss}", "-t", f"{d:.3f}", "-i", str(V / f)]
        ms = int(t0 * 1000)
        parts.append(
            f"[{idx}:a]aformat=channel_layouts=stereo,aresample=48000,highpass=f=90,"
            f"afade=in:d=0.08,afade=out:st={d - 0.25:.3f}:d=0.25,volume={g}dB,"
            f"adelay={ms}|{ms}[a{k}]")
        alabels.append(f"[a{k}]"); idx += 1
    if with_score:
        score = TMP / "trilha-02.wav"
        if not score.exists():
            synth_score(score)
        inputs += ["-i", str(score)]
        parts.append(f"[{idx}:a]aformat=channel_layouts=stereo,aresample=48000,volume=-3dB[sc]")
        alabels.append("[sc]"); idx += 1
    inputs += ["-f", "lavfi", "-t", f"{DUR:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    alabels.append(f"[{idx}:a]")
    parts.append("".join(alabels) + f"amix=inputs={len(alabels)}:normalize=0:duration=longest,"
                 f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo,atrim=duration={DUR:.3f}[aout]")

    name = "01-como-encontraram-a-zoe" + ("" if with_score else "-sem-trilha") + ".mp4"
    out = OUTDIR / name
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(parts),
           "-map", f"[{last}]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-t", f"{DUR:.3f}", str(out)]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    build(with_score=True)
    build(with_score=False)
