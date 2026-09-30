"""Trilha original do Reel 04 "Os 6 dias da Zoe · Parte 2": duas partes, tudo sintetizado aqui (sem samples).

Derivada de trilha_03.py (reaproveita o piano abafado, o pad, o bumbo, o shaker, o sino e o reverb de lá).
As seções seguem os blocos de build_04.py:
  início → P3      calma, como no Ep. 1: pad + piano abafado em arpejo lento (75 BPM, Ré maior)
  P3 (o golpe)     quase some: só o pad, bem baixo (sem zerar)
  cartela DIA 5    volta a calma; de "Finalmente" até o vislumbre o pad abre uma oitava e sobe um swell
  o vislumbre      muda de caráter quando a Zoe entra no quadro da Câmera 03: 104 BPM, marimba em
                   colcheias, baixo pluck (Ré · Lá/Dó# · Si m · Sol), bumbo macio, palmas e shaker leves,
                   com um acento (acorde cheio + sino) na entrada dela
  P5, P6, mapa     segue a parte animada (o duck sob a voz é feito no build, por sidechain)
  fecho            resolve: o groove para e fica um acorde de Ré com a marimba desacelerando, sumindo no fim
  cartelas         o sino suave de trilha_03 quando o contador enche (DIA 3, DIA 4 e DIA 5)

Os tempos vêm de build_04.py (ele chama render() com os valores reais). Rodando sozinho, usa MARKS.

Uso (numpy + scipy no venv 3.9):
  python editor/trilha_04.py audios/trilha-04.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trilha_03 as t3   # noqa: E402  instrumentos do Ep. 1
from trilha_03 import SR, add, chime, filt, hz, kick, norm, pad, piano, reverb, tick, tt   # noqa: E402

BEAT = t3.BEAT                  # 75 BPM na parte calma
BAR = 4 * BEAT
BEAT2 = 60 / 104                # 104 BPM na parte animada
BAR2 = 4 * BEAT2

# marcas em segundos na linha do tempo do Reel (valores de build_04.py)
MARKS = {
    "t0": 0.10,              # origem da grade calma
    "golpe_in": 24.0,        # a trilha quase some (P3)
    "golpe_out": 31.9,       # volta na cartela DIA 5
    "lift": 36.3,            # "Finalmente": o pad abre
    "open": 41.9,            # a Zoe entra no quadro da Câmera 03: começa a parte animada (1º tempo)
    "fecho": 58.7,
    "end": 64.2,
    "chimes": [2.3, 10.4, 32.0],
}

CHORDS = t3.CHORDS              # Dmaj9 · Gmaj9 · Bm11 · G/A (parte calma)
# parte animada: baixo descendo Ré · Dó# · Si · Sol e as vozes da marimba (MIDI)
GROOVE = [
    (38, [62, 66, 69, 74]),     # Ré
    (37, [61, 64, 69, 73]),     # Lá/Dó#
    (35, [59, 62, 66, 71]),     # Si m
    (31, [59, 62, 67, 71]),     # Sol
]
ARP = [0, 2, 1, 3, 2, 1, 3, 2]  # ordem das vozes nas colcheias
MELODY = [(0, 78), (1.5, 81), (3, 83), (6, 81), (7.5, 78), (8, 76), (11, 74), (12.5, 76), (13, 78)]  # (tempo, nota) em 4 compassos


# ---------- instrumentos novos ----------
_cache = {}


def marimba(m, vel=1.0, dur=1.1):
    """Marimba: fundamental + parciais de barra (3,93x e 9,2x) que morrem rápido, com o toque da baqueta."""
    key = (m, round(vel, 2))
    if key not in _cache:
        f, t = hz(m), tt(dur)
        s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 5.5)
             + 0.35 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t * 16)
             + 0.07 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t * 40))
        rng = np.random.default_rng(m)
        s += 0.08 * filt(rng.standard_normal(len(t)), "lowpass", 3000) * np.exp(-t * 300)
        s *= np.minimum(1, t / 0.002)
        r = int(0.05 * SR)
        s[-r:] *= np.linspace(1, 0, r)
        _cache[key] = norm(s) * vel
    return _cache[key]


def bass(m, dur=0.5):
    """Baixo pluck: seno + 2ª harmônica, ataque curto e decaimento rápido."""
    t = tt(dur)
    s = np.sin(2 * np.pi * hz(m) * t) + 0.35 * np.sin(4 * np.pi * hz(m) * t) + 0.1 * np.sin(6 * np.pi * hz(m) * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t * 5)
    r = int(0.04 * SR)
    env[-r:] *= np.linspace(1, 0, r)
    return norm(filt(s * env, "lowpass", 700))


def clap():
    t = tt(0.18)
    rng = np.random.default_rng(5)
    n = filt(rng.standard_normal(len(t)), "bandpass", [900, 3200])
    env = np.zeros_like(t)
    for d in (0.0, 0.009, 0.018):                      # três batidas curtas, como mãos
        env += np.where(t >= d, np.exp(-(t - d) * 90), 0)
    env += 0.4 * np.exp(-t * 22)
    return norm(n * env)


def swell(dur):
    """Ruído filtrado subindo (para a virada do vislumbre)."""
    t = tt(dur)
    rng = np.random.default_rng(9)
    n = rng.standard_normal(len(t))
    lo = filt(n, "bandpass", [400, 1800])
    hi = filt(n, "bandpass", [1800, 7000])
    u = t / dur
    return norm((lo * (1 - u) + hi * u) * u ** 2.2)


def crash(dur=2.2):
    t = tt(dur)
    rng = np.random.default_rng(13)
    return norm(filt(rng.standard_normal(len(t)), "highpass", 5000) * np.exp(-t * 2.6) * np.minimum(1, t / 0.003))


# ---------- arranjo ----------
def render(out, marks=None, acc_out=None):
    """Escreve a trilha em `out`. Com `acc_out`, o acento da entrada da Zoe sai num arquivo à parte (o build
    mistura esse acento sem o duck da voz, para ele soar inteiro mesmo encostado no fim da P4)."""
    mk = dict(MARKS, **(marks or {}))
    n = int(SR * mk["end"])
    names = ("pad", "piano", "chime", "mar", "bass", "kick", "clap", "tick", "fx", "a_mar", "a_chime", "a_fx")
    bus = {k: np.zeros(n) for k in names}
    t0, g_in, g_out, lift, op, fecho = (mk[k] for k in ("t0", "golpe_in", "golpe_out", "lift", "open", "fecho"))

    # parte calma: um acorde por compasso até a virada
    nbars = int((op - t0) / BAR) + 1
    for b in range(-1, nbars):
        tb = t0 + b * BAR
        if tb >= op:
            break
        root, notes = CHORDS[b % len(CHORDS)]
        dur = min(BAR + 1.6, op - tb + 0.6)             # o pad solta na virada
        add(bus["pad"], pad(notes, dur), tb, 1.0)
        if tb + BAR > lift:                             # "Finalmente": o pad abre uma oitava
            add(bus["pad"], pad([m + 12 for m in notes[1:]], dur, att=0.8), max(tb, lift), 0.45)
        for q in range(4):
            tq = tb + q * BEAT
            if tq >= op - 0.05 or g_in - 0.2 <= tq < g_out:   # no golpe fica só o pad
                continue
            if b % 4 == 3 and q == 3:                   # respiro a cada 4 compassos
                continue
            m, v = ((notes[0], .8), (notes[2], .55), (notes[3] + 12 * (b % 2 == 0), .5), (notes[1], .4))[q]
            add(bus["piano"], piano(m, 2.4, v), tq, 1.0)
    for tc in mk["chimes"]:
        add(bus["chime"], chime(78), tc, 1.0)           # F#5
        add(bus["chime"], chime(85), tc + 0.18, 0.5)    # C#6
    add(bus["fx"], swell(1.6), op - 1.6, 0.30)          # sobe até a entrada dela

    # parte animada: do "open" até o fecho
    nb2 = int(np.ceil((fecho - op) / BAR2))
    for b in range(nb2):
        tb = op + b * BAR2
        root, notes = GROOVE[b % len(GROOVE)]
        add(bus["pad"], pad([m - 12 for m in notes[1:]] + [notes[3]], BAR2 + 1.2, att=0.4, rel=0.9), tb, 0.35)
        for e in range(8):                              # colcheias
            te = tb + e * BEAT2 / 2
            if te >= fecho - 0.02:
                break
            v = 0.62 if e % 2 == 0 else 0.45
            add(bus["mar"], marimba(notes[ARP[e]] + (12 if e in (3, 6) else 0), v), te)
            add(bus["tick"], tick(e % 2 == 1), te, 0.35 if e % 2 else 0.22)
            add(bus["tick"], tick(), te + BEAT2 / 4, 0.14)
            if e in (0, 4):
                add(bus["kick"], kick(), te, 1.0 if e == 0 else 0.75)
            if e in (2, 6):
                add(bus["clap"], clap(), te, 0.8)
            if e in (0, 3, 4):                          # baixo: 1, o "e" do 2 e o 3
                add(bus["bass"], bass(root + (12 if e == 4 else 0), 0.42), te, 1.0 if e == 0 else 0.7)
    # a melodia (marimba aguda + sino), uma frase a cada 4 compassos, a partir do 2º compasso
    for k in range(nb2 // 4 + 1):
        for beat, m in MELODY:
            tm = op + k * 4 * BAR2 + beat * BEAT2
            if op + BAR2 - 0.01 <= tm < fecho - 0.3:
                add(bus["mar"], marimba(m, 0.5), tm)
                add(bus["chime"], chime(m + 12, 1.2), tm, 0.12)
    # o acento: a Zoe entra no quadro (barramentos próprios, para poder sair à parte)
    for m in GROOVE[0][1] + [74, 78, 81]:
        add(bus["a_mar"], marimba(m, 0.8), op, 0.8)
    add(bus["a_chime"], chime(86), op, 0.8)             # D6
    add(bus["a_chime"], chime(90), op + 0.12, 0.4)      # F#6
    add(bus["a_fx"], crash(), op, 0.22)

    # fecho: resolve em Ré, a marimba desacelerando
    fdur = mk["end"] - fecho
    add(bus["pad"], pad([50, 57, 62, 66, 69], fdur + 0.5, att=0.6, rel=2.2), fecho, 0.9)
    add(bus["bass"], bass(38, 2.5), fecho, 0.9)
    for i, (dt, m) in enumerate(((0.0, 62), (0.45, 66), (1.0, 69), (1.7, 74), (2.6, 78))):
        add(bus["mar"], marimba(m, 0.55 - 0.05 * i, dur=1.6), fecho + dt)
    add(bus["chime"], chime(86, 3.0), fecho + 2.6, 0.5)

    # ---------- mixagem ----------
    gain = {"pad": 0.30, "piano": 0.34, "chime": 0.16, "mar": 0.30, "bass": 0.32, "kick": 0.40,
            "clap": 0.09, "tick": 0.07, "fx": 0.20}
    for k in ("mar", "chime", "fx"):
        gain["a_" + k] = gain[k]

    # envelope geral: entrada suave, o golpe quase some, o fecho mais baixo e o fim sumindo
    tax = np.arange(n) / SR
    g = np.ones(n)
    g *= np.clip(tax / 0.4, 0, 1)
    down = np.clip((tax - g_in) / 0.6, 0, 1) * (1 - np.clip((tax - g_out) / 0.4, 0, 1))
    g *= 1 - 0.70 * down                                 # -10 dB no golpe (e sem o piano)
    g *= np.where(tax >= fecho, 0.6, 1.0)
    fo = int((mk["end"] - 1.8) * SR)
    g[fo:] *= np.linspace(1, 0, n - fo) ** 1.5

    def mixdown(keys):
        """Os barramentos `keys` em estéreo (seco + reverb, com o envelope geral)."""
        dry = sum(bus[k] * gain[k] for k in keys)
        wsrc = {"piano": 1.0, "chime": 1.0, "a_chime": 1.0, "pad": 0.1 / gain["pad"], "mar": 0.6, "a_mar": 0.6,
                "clap": 1.0}
        wet = reverb(sum(bus[k] * gain[k] * wsrc[k] for k in keys if k in wsrc) + np.zeros(n))
        L = dry + 0.33 * wet
        R = dry.copy()
        d = int(0.011 * SR)
        R[d:] += 0.33 * wet[:-d]
        return np.stack([L * g, R * g], axis=1)

    def write(path, mix):
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())

    acc_keys = ("a_mar", "a_chime", "a_fx")
    main = mixdown([k for k in names if k not in acc_keys])
    acc = mixdown(acc_keys)
    if acc_out is None:                                  # uma trilha só, com o acento dentro
        mix = main + acc
        mix = np.tanh(1.2 * mix / np.abs(mix).max()) / np.tanh(1.2)
        write(out, mix * 10 ** (-1 / 20))                # pico em -1 dBFS; o build ajusta o nível
    else:                                                # duas faixas na mesma escala (sem saturação)
        k = 10 ** (-1 / 20) / np.abs(main + acc).max()
        write(out, main * k)
        write(acc_out, acc * k)
    return out


if __name__ == "__main__":
    print(render(sys.argv[1] if len(sys.argv) > 1 else "audios/trilha-04.wav"))
