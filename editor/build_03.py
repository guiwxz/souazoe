"""Versão 2 do Reel 'Como encontraram a Zoe?' (9:16, ~62s): meio mais enxuto, menos drama,
e um fechamento dizendo que o perfil foi criado para seguir ajudando outras Zoes.

Sem narração gravada: os textos carregam a história; o áudio real entra no gancho e no reencontro.
Gera duas versões: com trilha de referência (sintetizada aqui) e sem trilha (para usar música no app).

Uso: python3 editor/build_03.py
"""
import math, struct, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
V = ROOT / "videos"
EF, CF = ROOT / "editor" / "fonts", ROOT / "carrossel" / "fonts"
OUTDIR = ROOT / "saida" / "video" / "video3"
TMP = ROOT / "editor" / ".tmp-03"          # overlays e trilha (regenerados a cada build)
W, H, FPS = 1080, 1920, 30

CREAM, LILAC, PINK = (246, 241, 233), (185, 167, 243), (236, 72, 153)

# ── Takes ────────────────────────────────────────────────────────────────────
# (arquivo, início no clipe, início na linha do tempo, opções)
#   fx/fy: foco do recorte (0..1)  z: zoom  pan: deslocamento horizontal ao longo do take
#   fit: foto inteira sobre fundo desfocado  doc: dessaturado (material de busca)  spd: velocidade
SHOTS = [
    ("VID-20260924-WA0172.mp4", 0.0, 0.00, dict(z=1.08)),                  # gancho: Zoe pulando na Isabela
    ("d8113f49-408d-478b-b508-2f8d043188ab.JPG", 0, 3.50, dict(fit=1, doc=1, blur_contact=1)),  # cartaz
    ("0db16a59-2cdf-4b30-a9c9-4d234b85e595.JPG", 0, 4.40, dict(fit=1, doc=1)),   # raio de 3 km
    ("cdf8adaa-2d56-4586-b22b-6daffb22db11.MP4", 0.4, 5.30, dict(doc=1)),        # câmeras no celular
    ("f1db99c8-942b-485d-b437-da424eb1e6ed.MP4", 2.0, 6.20, dict(doc=1, fx=0.4)),  # DVR
    (None, 0, 7.10, {}),                                                    # preto: a ligação
    ("VID-20260924-WA0156.mp4", 0.0, 8.70, dict(doc=1, rec=1, fx=0.8, pan=-160)),   # Instituto, câmera 06
    ("VID-20260924-WA0156.mp4", 12.0, 16.20, dict(doc=1, rec=1, fx=1.0, z=1.35, pan=-90)),  # mato à direita
    ("VID-20260924-WA0160.mp4", 0.0, 20.50, dict(doc=1, rec=1, z=1.25, spd=0.55)),  # a câmera
    ("VID-20260924-WA0171.mp4", 4.8, 25.50, dict(fy=1.0, z=1.9, fx=0.15, pan=160)),   # o mato
    ("VID-20260924-WA0197.mp4", 4.3, 29.30, dict(z=1.05)),                  # ela ali, na coleira
    ("VID-20260924-WA0197.mp4", 7.8, 32.80, dict(z=1.05)),                  # "Zuzu! Meu amor!"
    ("VID-20260924-WA0171.mp4", 6.4, 37.10, dict(z=1.15, fx=0.55)),         # Guilherme abraçando
    ("IMG-20260924-WA0174.jpg", 0, 41.10, dict(z=1.08, pan=-60)),           # ela sorrindo
    ("IMG_8348.MOV", 16.5, 43.70, dict(z=1.05)),                            # em casa, no sol
    ("IMG_8337.MOV", 22.0, 46.30, dict(z=1.05)),                            # dormindo
    ("IMG_8340.MOV", 13.6, 49.10, dict(z=1.05)),                            # deitada na cama
    ("IMG_8356.MOV", 3.0, 52.10, dict(z=1.05)),                             # rostinho de perto
    ("IMG_8343.jpg", 0, 55.10, dict(z=1.06, fy=0.35, dim=1)),               # na janela: fechamento
]
DUR = 62.5

# ── Textos ───────────────────────────────────────────────────────────────────
# (início, fim, estilo, texto)   estilos: hook, big, line, small, endmsg, end2
TEXTS = [
    (0.05, 3.40, "hook", "COMO ENCONTRARAM|A ZOE?"),
    (3.60, 7.00, "big", "6 DIAS|PROCURANDO"),
    (7.25, 8.60, "line", "Até que veio uma ligação"),
    (8.80, 11.00, "line", "Uma veterinária que acompanhava a história"),
    (11.00, 14.00, "line", "viu uma cachorrinha preta saindo do mato, perto do Instituto Menino Deus"),
    (14.00, 16.10, "line", "A cachorrinha correu|Ela ligou pra Isabela"),
    (16.30, 19.00, "line", "Quem estava nas buscas foi até lá, mas não encontrou"),
    (20.60, 23.20, "line", "Uma câmera mostrou, por uma fração de segundo, uma cachorrinha"),
    (23.20, 25.40, "big", "ERA ELA?"),
    (25.60, 27.40, "line", "A Isabela entrou no mato chamando"),
    (27.40, 29.20, "line", "E viu uma cachorrinha correndo lá na frente"),
    (29.40, 31.30, "small", "Ela chamou: “Zoe!”"),
    (33.00, 35.60, "big", "E ELA VEIO"),
    (41.20, 43.60, "small", "Era ela"),
    (43.85, 46.20, "line", "Depois de seis dias, a Zoe voltou pra casa"),
    (46.40, 49.00, "line", "Uma pessoa prestando atenção ajudou a mudar o final"),
    (49.20, 52.00, "line", "Nem todo animal perdido tem tanta gente procurando"),
    (52.20, 55.00, "line", "A gente quer seguir ajudando outras Zoes"),
    (55.20, 58.90, "endmsg", "Foi pra isso que|decidimos criar|este perfil"),
    (58.90, DUR, "end2", ""),
]

# ── Áudio real (arquivo, início no clipe, início na linha do tempo, duração, ganho dB) ──
AUDIO = [
    ("VID-20260924-WA0172.mp4", 0.0, 0.00, 3.50, -4),     # "Tá, pega!"
    ("VID-20260924-WA0197.mp4", 4.3, 29.30, 3.50, -8),    # "Ela estava pra lá!" + ambiente do campo
    ("VID-20260924-WA0197.mp4", 7.8, 32.80, 4.30, -2),    # "Zuzu! Meu amor!"
    ("VID-20260924-WA0171.mp4", 6.4, 37.10, 4.00, -16),   # vento do campo
]


def font(name, size):
    p = (EF / name) if (EF / name).exists() else (CF / name)
    return ImageFont.truetype(str(p), size)


KEEP = ("Menino Deus",)   # nomes que não podem quebrar entre linhas


def wrap(draw, text, fnt, maxw):
    for k in KEEP:
        text = text.replace(k, k.replace(" ", "\x00"))
    lines, cur = [], ""
    for w in (w.replace("\x00", " ") for w in text.split(" ")):
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
        lines = [l for part in text.split("|") for l in wrap(d, part, f, 880)]
        draw_block(img, lines, f, 1180, CREAM)
    elif style == "small":
        f = font("Poppins-SemiBold.ttf", 64)
        draw_block(img, text.split("|"), f, 1250, CREAM)
    elif style in ("endmsg", "end2"):
        # degradê escuro no alto: o texto fica acima da Zoe, que olha pela janela
        grad = Image.new("L", (1, H))
        for yy in range(H):
            grad.putpixel((0, yy), int(215 * max(0.0, 1 - yy / 1150) ** 0.8))
        shade = Image.new("RGBA", (W, H), (23, 19, 31, 255))
        shade.putalpha(grad.resize((W, H)))
        img.alpha_composite(shade)
        if style == "endmsg":
            f2 = font("Poppins-ExtraBold.ttf", 86)
            y = draw_block(img, text.split("|"), f2, 0, CREAM, lh=1.06, top=330)
            draw_block(img, ["@souazoe.pf"], font("Poppins-SemiBold.ttf", 46), 0, LILAC, glow=8, top=y + 40)
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
    """Pad grave com pulso suave até o reencontro; passa sem corte para um acorde maior (alívio)."""
    def hz(n): return 440 * 2 ** ((n - 69) / 12)
    tension = [hz(45), hz(52), hz(57), hz(60)]          # Lá menor (A2 E3 A3 C4)
    relief = [hz(41), hz(48), hz(57), hz(60), hz(64)]   # Fá maior com 9ª (F2 C3 A3 C4 E4)
    T_CALL, T_TURN, T_ARP = 7.1, 32.8, 43.7             # ligação, "ela veio", casa
    XF = 1.5                                            # crossfade tensão → alívio
    n = int(DUR * sr)
    buf = bytearray()
    ph_beat = 0.0
    for i in range(n):
        t = i / sr
        s = 0.0
        if t < T_TURN + XF:
            amp = 0.05 + 0.04 * min(t / T_TURN, 1)
            fade = min(t / 1.5, 1) * min(max((T_TURN + XF - t) / XF, 0), 1)
            for k, f in enumerate(tension):
                s += math.sin(2 * math.pi * f * t + k) * (1.0 if k < 2 else 0.5)
                s += 0.3 * math.sin(2 * math.pi * f * 1.003 * t)
            s *= amp * fade * (0.85 + 0.15 * math.sin(2 * math.pi * 0.25 * t))
            if T_CALL < t < T_TURN:                                   # pulso discreto, sem acelerar muito
                bpm = 64 + 12 * (t - T_CALL) / (T_TURN - T_CALL)
                ph_beat += bpm / 60 / sr
                dt = ph_beat % 1.0
                if dt < 0.18:
                    s += 0.10 * math.sin(2 * math.pi * 52 * dt) * math.exp(-dt * 28) * fade
        if t >= T_TURN:
            env = min((t - T_TURN) / 2.5, 1) * min((DUR - t) / 2.0, 1)
            r = 0.0
            for k, f in enumerate(relief):
                r += math.sin(2 * math.pi * f * t + k) * (1.0 if k < 2 else 0.6)
                r += 0.3 * math.sin(2 * math.pi * f * 0.997 * t)
            if t > T_ARP:                                             # arpejo leve de "caixinha"
                notes = [hz(72), hz(76), hz(79), hz(84)]
                step = 0.5
                j = int((t - T_ARP) / step)
                dt = (t - T_ARP) - j * step
                r += 0.9 * math.sin(2 * math.pi * notes[j % 4] * t) * math.exp(-dt * 5)
            s += r * 0.07 * env
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
        score = TMP / "trilha-03.wav"
        if not score.exists():
            synth_score(score)
        inputs += ["-i", str(score)]
        parts.append(f"[{idx}:a]aformat=channel_layouts=stereo,aresample=48000,volume=-3dB[sc]")
        alabels.append("[sc]"); idx += 1
    inputs += ["-f", "lavfi", "-t", f"{DUR:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    alabels.append(f"[{idx}:a]")
    parts.append("".join(alabels) + f"amix=inputs={len(alabels)}:normalize=0:duration=longest,"
                 f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo,atrim=duration={DUR:.3f}[aout]")

    name = "01-como-encontraram-a-zoe-v2" + ("" if with_score else "-sem-trilha") + ".mp4"
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
