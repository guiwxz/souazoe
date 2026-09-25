"""Monta o Reel 'Como encontramos a Zoe' (9:16, duração = áudio da narração)."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V = ROOT / "videos"
AUDIO = ROOT / "audios" / "1.ogg"
WORDS = Path(sys.argv[1])          # words.json gerado pelo whisper
FONTS = Path(sys.argv[2])          # pasta com Poppins
OUT = ROOT / "saida" / "01-como-encontramos-a-zoe.mp4"
W, H, FPS = 1080, 1920, 30

DUR = float(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(AUDIO)]))

# (arquivo, início no clipe, início na linha do tempo, zoom/pan)  — cortes nas palavras
SHOTS = [
    ("VID-20260924-WA0196.mp4", 0.4, 0.00),   # "A Zoe foi encontrada" — reencontro no campo
    ("VID-20260924-WA0171.mp4", 0.0, 2.46),   # "dia 24 de setembro, às 16h" — busca no mato
    ("VID-20260924-WA0156.mp4", 2.0, 5.00),   # "no Instituto Menino Deus" — câmera do local
    ("VID-20260924-WA0182.mp4", 1.4, 6.98),   # "vivendo sozinha no mato"
    ("VID-20260924-WA0197.mp4", 3.0, 8.38),   # "no mato"
    ("VID-20260924-WA0204.mp4", 5.0, 9.52),   # "sem ferimentos" — conferindo as patinhas
    ("VID-20260924-WA0172.mp4", 1.6, 10.38),  # "ficou muito feliz"
    ("IMG-20260924-WA0174.jpg", 0.0, 11.94),  # "ao encontrá-los" — foto sorrindo
]

# correções de transcrição (fala real)
FIX = {"a": "ao"}


def cover(extra=1.0):
    return (f"scale={int(W*extra)}:{int(H*extra)}:force_original_aspect_ratio=increase,"
            f"crop={int(W*extra)}:{int(H*extra)}")


def build_video_filters():
    inputs, parts = [], []
    for i, (f, ss, t0) in enumerate(SHOTS):
        t1 = SHOTS[i + 1][2] if i + 1 < len(SHOTS) else DUR
        d = t1 - t0
        src = V / f
        if f.endswith(".jpg"):
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(src)]
        else:
            inputs += ["-ss", f"{ss}", "-t", f"{d:.3f}", "-i", str(src)]
        # pan lento em todos os takes: dá movimento e disfarça tremidas
        z = 1.12
        parts.append(
            f"[{i}:v]{cover(z)},fps={FPS},"
            f"crop={W}:{H}:x='(iw-{W})/2*(1-t/{d:.3f})':y='(ih-{H})/2',"
            f"setsar=1,trim=duration={d:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
    concat = "".join(f"[v{i}]" for i in range(len(SHOTS)))
    parts.append(f"{concat}concat=n={len(SHOTS)}:v=1:a=0[vc]")
    return inputs, parts


def ass_time(t):
    t = max(t, 0)
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"


def build_ass(path):
    words = json.load(open(WORDS))
    # junta "encontrá" + "-los"
    merged = []
    for w in words:
        if merged and w["w"].startswith("-"):
            merged[-1]["w"] += w["w"]; merged[-1]["e"] = w["e"]
        else:
            merged.append(dict(w))
    for w in merged:
        w["w"] = FIX.get(w["w"], w["w"])
        w["p"] = w["w"][-1] in ".,"          # guarda a pausa, tira a pontuação da tela
        w["w"] = w["w"].rstrip(".,")
    # blocos de até 3 palavras, quebrando em pontuação
    # nomes que não podem ser quebrados entre blocos
    KEEP = {("Menino", "Deus")}
    chunks, cur = [], []
    for i, w in enumerate(merged):
        nxt = merged[i + 1] if i + 1 < len(merged) else None
        if len(cur) == 2 and nxt and (w["w"], nxt["w"]) in KEEP:
            chunks.append(cur); cur = []
        cur.append(w)
        if len(cur) == 3 or w["p"]:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins ExtraBold,124,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,8,4,5,60,60,0
Style: Hook,Poppins ExtraBold,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,26,0,8,90,90,260

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    YEL = r"{\c&H00D7FF&}"   # amarelo (BGR)
    WHT = r"{\c&HFFFFFF&}"
    for ci, ch in enumerate(chunks):
        end_chunk = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else DUR
        for wi, w in enumerate(ch):
            s = w["s"]
            e = ch[wi + 1]["s"] if wi + 1 < len(ch) else end_chunk
            txt = " ".join((YEL + x["w"].upper() + WHT) if j == wi else x["w"].upper()
                           for j, x in enumerate(ch))
            pop = r"{\pos(540,1180)\fscx108\fscy108\t(0,90,\fscx100\fscy100)}" if wi == 0 else r"{\pos(540,1180)}"
            ev.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{pop}{txt}")
    # gancho no topo (fundo em caixa, área segura)
    ev.append(r"Dialogue: 2,0:00:00.00,0:00:02.46,Hook,,0,0,0,,{\3c&H5A3CE6&\fad(0,200)}COMO ENCONTRAMOS A ZOE")
    path.write_text(head + "\n".join(ev) + "\n")


def main():
    OUT.parent.mkdir(exist_ok=True)
    ass = OUT.parent / "legendas-01.ass"
    build_ass(ass)
    inputs, parts = build_video_filters()
    n = len(SHOTS)
    fc = ";".join(parts) + (
        f";[vc]subtitles='{ass}':fontsdir='{FONTS}'[vout]"
        f";[{n}:a]highpass=f=80,afftdn=nf=-25,loudnorm=I=-14:TP=-1.5:LRA=11,"
        f"aresample=48000,aformat=channel_layouts=stereo,atrim=duration={DUR:.3f}[aout]")
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-i", str(AUDIO),
           "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-t", f"{DUR:.3f}", str(OUT)]
    subprocess.run(cmd, check=True)
    print(OUT)


if __name__ == "__main__":
    main()
