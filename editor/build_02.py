"""Monta o Reel 02 "Tchau, cartaz" (9:16, 19,5 s): a retirada dos cartazes da Zoe pela cidade.

Sem narração. O texto na tela fala com a voz da Zoe, os cortes seguem o tempo da trilha
(120 BPM, gerada por editor/trilha_02.py) e cada cartaz rasga num tempo forte, com o
som real do papel por baixo da música. Também gera uma versão sem a trilha, só com o
som ambiente, para usar um áudio em alta dentro do app.

O "jogo" da Zoe: a pata encosta no cartaz (IMG_8443) e o corte vai, no drop, para o
mesmo poste já sem o cartaz (IMG_8445, 18 s depois), com o som de um rasgo real.

Uso: python3 editor/build_02.py   (antes: python editor/trilha_02.py audios/trilha-02.wav)
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "drive" / "set26"
CART = SET / "cartazes"
WORK = ROOT / "videos"                       # cópias de trabalho (fotos convertidas)
MUSIC = ROOT / "audios" / "trilha-02.wav"
FONTS = ROOT / "editor" / "fonts"
OUTDIR = ROOT / "saida" / "video" / "video2"
OUT = OUTDIR / "02-tchau-cartaz.mp4"
OUT_NAT = OUTDIR / "02-tchau-cartaz-sem-musica.mp4"
W, H, FPS = 1080, 1920, 30
DUR = 19.5

# fotos usadas como still: HEIC e o quadro único do IMG_8445 viram JPG em videos/
STILLS = {
    "IMG_8445.jpg": CART / "IMG_8445.MOV",    # o poste da pata, já sem o cartaz
    "IMG_8447.jpg": CART / "IMG_8447.HEIC",   # a Zoe na cadeirinha do carro
}

# (arquivo, início no clipe, início na linha do tempo, velocidade, extras)
# hit = quando o cartaz sai, em segundos dentro do take (cai sempre num tempo da música)
SHOTS = [
    (CART / "IMG_8437.MOV", 0.0, 0.0, 1.3, {"nat": 0.4}),           # a Zoe de guia, indo pro poste
    (CART / "IMG_8437.MOV", 2.9, 2.0, 1.1, {"nat": 0.4}),           # o cartaz ainda está lá
    (CART / "IMG_8440.MOV", 1.0, 4.0, 1.5, {"hit": 0.5}),           # tapume (drop + título)
    (CART / "IMG_8439.MOV", 0.9, 5.0, 1.2, {"hit": 0.5}),           # poste na calçada
    (CART / "IMG_8446.MOV", 1.6, 6.0, 1.45, {"hit": 1.0}),          # árvore: "nessa foto eu tava linda"
    (CART / "IMG_8448.MOV", 1.0, 7.5, 1.6, {"hit": 0.5, "ax": 1.0}),  # vidro do abrigo, na praça
    (CART / "WhatsApp Video 2026-09-25 at 22.00.22.mp4", 1.0, 8.5, 1.5,
     {"hit": 0.5, "nat": 0.45, "sharp": True}),                     # coluna de granito
    (CART / "IMG_8441.MOV", 0.95, 9.5, 1.2, {"hit": 0.25}),         # poste com o círculo laranja
    (CART / "IMG_8443.MOV", 0.0, 10.0, 1.0, {"nat": 0.6}),          # a Zoe olha a cidade e estica a pata
    (CART / "IMG_8443.MOV", 2.48, 11.3, 0.75,
     {"zoom": 1.25, "top": True, "nat": 0.6}),                      # a pata no cartaz, em câmera lenta...
    (WORK / "IMG_8445.jpg", 0, 12.0, 1.0,
     {"still": True, "zoom": 1.12, "hit": 0.0, "amp": 2.0}),        # ...corta pro poste sem o cartaz: "fácil."
    (WORK / "IMG_8447.jpg", 0, 13.0, 1.0, {"still": True}),         # fiscalizando, da cadeirinha do carro
    (CART / "IMG_8442.MOV", 0.3, 14.0, 1.0, {"nat": 0.5}),          # chega perto pra conferir
    (CART / "IMG_8438.MOV", 1.35, 15.0, 1.0, {"hit": 0.5}),         # o último rasga em 15,5 s
    (SET / "IMG_8348.MOV", 19.45, 16.0, 1.0, {"nat": 0.25}),        # em casa, deitada no sol
]
FLASHES = [(4.0, 0.75), (12.0, 0.8)]        # clarão curto no drop e no "rasgo da Zoe"
# efeitos com som real, em tempo absoluto: (início, arquivo, início no clipe, duração, volume)
SFX = [(11.9, CART / "IMG_8438.MOV", 1.8, 0.6, 1.2)]   # o rasgo começa um instante antes do corte

# identidade: ink #17131F, lilac #B9A7F3, pink #EC4899 (no ASS a ordem é &HBBGGRR)
PINK = "&H9948EC&"


def fpath(p):
    # caminho para dentro do filtergraph: no Windows, "C:\..." quebra o parser do ffmpeg
    return Path(p).resolve().as_posix().replace(":", r"\:")


def prep_stills():
    WORK.mkdir(exist_ok=True)
    for name, src in STILLS.items():
        if not (WORK / name).exists():
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-frames:v", "1",
                            "-q:v", "2", str(WORK / name)], check=True)


def cover(z):
    w, h = int(W * z) // 2 * 2, int(H * z) // 2 * 2
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", (w - W) / 2, (h - H) / 2


def shot_filters(i, vi, ai, speed, o, d):
    z = o.get("zoom", 1.08)
    sc, mx, my = cover(z)
    # pan lento (alternando o sentido) + tranco quando o cartaz sai; "ax" fixa o quadro na horizontal
    dirx = 1 if i % 2 else -1
    x = f"{mx:.1f}+{dirx}*{mx * 0.6:.1f}*(2*t/{d:.3f}-1)" if "ax" not in o else f"{o['ax'] * 2 * mx:.1f}"
    y = f"{0 if o.get('top') else my:.1f}"
    if "hit" in o:
        h, amp = o["hit"], o.get("amp", 1.0)
        k = f"gte(t,{h})*exp(-(t-{h})*14)*sin(2*PI*11*(t-{h}))"
        x += f"+{min(12 * amp, mx * 0.35 * amp):.1f}*{k}"
        y += f"+{min(24 * amp, my * 0.3 * amp):.1f}*{k}"
    x, y = f"clip({x},0,{2 * mx:.1f})", f"clip({y},0,{2 * my:.1f})"
    extra = ",unsharp=5:5:0.7" if o.get("sharp") else ""
    v = (f"[{vi}:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},{sc},"
         f"crop={W}:{H}:x='{x}':y='{y}',setsar=1{extra},eq=contrast=1.04:saturation=1.08,"
         f"trim=duration={d:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
    # som real: tira o vento (grave), ajusta o volume e evita estalo nos cortes
    a = (f"[{ai}:a]aresample=48000,aformat=channel_layouts=stereo,atempo={speed},"
         f"highpass=f=200,lowpass=f=12000,volume={o.get('nat', 1.0)},"
         f"apad=whole_dur={d:.3f},atrim=duration={d:.3f},asetpts=PTS-STARTPTS,"
         f"afade=t=in:d=0.01,afade=t=out:st={d - 0.015:.3f}:d=0.015[a{i}]")
    return v, a


def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def build_ass(path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Big,Poppins ExtraBold,175,&H00FFFFFF,&H00FFFFFF,&H001F1317,&H801F1317,-1,0,0,0,100,100,0,0,1,9,5,5,40,40,0
Style: Title,Poppins ExtraBold,265,&H00FFFFFF,&H00FFFFFF,&H001F1317,&H009948EC,-1,0,0,0,100,100,0,0,1,11,14,5,40,40,0
Style: Label,Poppins ExtraBold,105,&H001F1317,&H001F1317,&H00F3A7B9,&H00000000,-1,0,0,0,100,100,4,0,3,20,0,5,40,40,0
Style: Hand,Caveat,185,&H00FFFFFF,&H00FFFFFF,&H001F1317,&H801F1317,0,0,0,0,100,100,0,0,1,8,4,5,40,40,0
Style: Box,Poppins ExtraBold,128,&H00FFFFFF,&H00FFFFFF,&H001F1317,&H00000000,-1,0,0,0,100,100,0,0,3,24,0,5,40,40,0
Style: BoxPink,Poppins ExtraBold,150,&H00FFFFFF,&H00FFFFFF,&H009948EC,&H00000000,-1,0,0,0,100,100,0,0,3,26,0,5,40,40,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # no libass o Fontsize é a altura da linha: na Poppins a letra maiúscula tem ~0,41 disso.
    # Linhas de título vão em eventos separados para ficarem mais juntas que o \N.
    pop = r"\fscx114\fscy114\t(0,120,\fscx100\fscy100)"
    slam = r"\fscx180\fscy180\frz-9\t(0,130,\fscx100\fscy100\frz-3)"
    hand = r"\fscx88\fscy88\t(0,140,\fscx100\fscy100)\fad(90,140)"
    ev = [
        # abertura
        (0.12, 1.95, "Big", rf"{{\pos(540,500){pop}\fad(0,110)}}EU JÁ TÔ"),
        (0.12, 1.95, "Big", rf"{{\pos(540,640){pop}\fad(0,110)}}EM CASA."),
        (2.05, 3.90, "Big", rf"{{\pos(540,1250)\fs112{pop}\fad(0,110)}}MAS MEUS CARTAZES,"),
        (2.30, 3.90, "Big", rf"{{\pos(540,1395)\c{PINK}{pop}\fad(0,110)}}AINDA NÃO."),
        # título no drop
        (4.00, 5.55, "Label", rf"{{\pos(540,330){slam}\fad(0,150)}}OPERAÇÃO"),
        (4.00, 5.55, "Title", rf"{{\pos(540,520){slam}\fad(0,150)}}TCHAU,"),
        (4.00, 5.55, "Title", rf"{{\pos(540,700){slam}\fad(0,150)}}CARTAZ"),
        # comentários da Zoe (manuscritos)
        (6.05, 7.20, "Hand", rf"{{\pos(540,420)\frz4{hand}}}nessa foto eu\Ntava linda"),
        (10.08, 11.30, "Hand", rf"{{\pos(540,370)\frz-4{hand}}}deixa que\Neu ajudo"),   # sai antes do close no cartaz
        (12.08, 12.98, "Hand", rf"{{\pos(700,640)\frz-6\fs230{hand}}}fácil."),
        (13.05, 14.95, "Hand", rf"{{\pos(540,1440)\frz3{hand}}}fiscalizando\No serviço"),
        # final
        (16.25, DUR, "Box", rf"{{\pos(540,1265){pop}\fad(120,0)}}NÃO PRECISA MAIS\NME PROCURAR."),
        (17.25, DUR, "BoxPink", rf"{{\pos(540,1505){pop}\fad(120,0)}}É SÓ ME SEGUIR."),
    ]
    lines = [f"Dialogue: 1,{ass_time(s)},{ass_time(e)},{st},,0,0,0,,{txt}" for s, e, st, txt in ev]
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    prep_stills()
    ass = OUTDIR / "legendas-02.ass"
    build_ass(ass)
    inputs, parts = [], []

    def add_input(*args):
        inputs.extend(args)
        return inputs.count("-i") - 1

    for i, (f, ss, t0, speed, o) in enumerate(SHOTS):
        d = (SHOTS[i + 1][2] if i + 1 < len(SHOTS) else DUR) - t0
        if o.get("still"):
            vi = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{d + 0.3:.3f}", "-i", str(f))
            ai = add_input("-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo")
        else:
            vi = ai = add_input("-ss", f"{ss}", "-t", f"{d * speed + 0.3:.3f}", "-i", str(f))
        parts += shot_filters(i, vi, ai, speed, o, d)
    n = len(SHOTS)
    sfx = []
    for j, (t, f, ss, d, g) in enumerate(SFX):
        k = add_input("-ss", f"{ss}", "-t", f"{d}", "-i", str(f))
        ms = int(t * 1000)
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,highpass=f=200,"
                     f"volume={g},afade=t=out:st={d - 0.1:.3f}:d=0.1,adelay={ms}|{ms}[s{j}]")
        sfx.append(f"[s{j}]")
    mi = add_input("-i", str(MUSIC))
    flash = "".join(
        f",drawbox=x=0:y=0:w=iw:h=ih:color=white@{a * k:.2f}:t=fill:enable='between(t,{t + j / FPS:.3f},{t + (j + 1) / FPS - 0.001:.3f})'"
        for t, a in FLASHES for j, k in enumerate((1.0, 0.55, 0.25)))
    fc = ";".join(parts) + (
        ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0{flash}[vc]"
        f";[vc]subtitles='{fpath(ass)}':fontsdir='{fpath(FONTS)}',split=2[vout][vout2]"
        ";" + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[amb]"
        f";[amb]{''.join(sfx)}amix=inputs={1 + len(sfx)}:normalize=0:duration=first,"
        "acompressor=threshold=-24dB:ratio=3:attack=5:release=120,asplit=2[nat][nat2]"
        f";[{mi}:a]aresample=48000,volume=0.55[mus]"
        f";[mus][nat]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,"
        f"aresample=48000,atrim=duration={DUR}[aout]"
        f";[nat2]loudnorm=I=-18:TP=-1.5:LRA=11,aresample=48000,atrim=duration={DUR}[aout2]")
    enc = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-t", f"{DUR}"]
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
           "-map", "[vout]", "-map", "[aout]", *enc, str(OUT),
           "-map", "[vout2]", "-map", "[aout2]", *enc, str(OUT_NAT)]
    subprocess.run(cmd, check=True)
    print(OUT)
    print(OUT_NAT)


if __name__ == "__main__":
    main()
