"""Trilha original do Reel 03 "Os 6 dias da Zoe · Parte 1": 75 BPM, Ré maior, piano abafado + pad.

Tudo é sintetizado aqui (sem samples), então não há questão de direito autoral. Contida e
contemporânea: nada de drama, tristeza ou "motivacional". As seções seguem os blocos de
build_03.py (1 tempo = 0,8 s; a grade é deslocada para que "Na sexta mesmo" caia num 1º tempo):
  início → P5    calma: pad + piano em arpejo lento (Dmaj9 · Gmaj9 · Bm11 · G/A, 1 acorde por compasso)
  P5 → P6        pulso: bumbo macio, piano repetido em colcheias, shaker; semicolcheias na lista
                 "jornal, rádio, grupos..." até "Na sexta mesmo"
  cartelas       um sino suave quando o contador enche (DIA 1 e DIA 2)
  P7 (o corte)   a música zera de uma vez, junto com a imagem, e fica fora do P7 e do P8
  fecho          volta bem baixinha: pad em Ré e três notas de piano, sumindo no fim

Os tempos vêm de build_03.py (ele chama render() com os valores reais). Rodando sozinho, usa MARKS.

Uso (numpy + scipy no venv 3.9):
  python editor/trilha_03.py audios/trilha-03.wav
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BEAT = 0.8                      # 75 BPM
BAR = 4 * BEAT

# marcas em segundos na linha do tempo do Reel (valores de build_03.py)
MARKS = {
    "t0": 0.10,             # origem da grade (1º tempo do compasso 0)
    "pulse": 25.70,         # entra o pulso (P5)
    "noise": 30.50,         # semicolcheias ("jornal, rádio, ...")
    "friday": 35.30,        # "Na sexta mesmo" (1º tempo)
    "cut": 45.20,           # tudo corta (início do P7)
    "fecho": 62.70,         # volta baixinha (fecho)
    "end": 68.20,
    "chimes": [2.60, 38.10],  # contador enchendo nas cartelas
}

# acordes (1 por compasso): baixo + vozes do pad/piano (MIDI)
CHORDS = [
    (38, [57, 61, 64, 66]),     # Dmaj9
    (43, [59, 62, 66, 69]),     # Gmaj9
    (35, [57, 62, 64, 66]),     # Bm11
    (45, [55, 59, 62, 66]),     # G/A
]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def norm(x):
    return x / max(1e-9, np.abs(x).max())


def add(bus, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(bus) or i + len(sig) <= 0:
        return
    s0 = max(0, -i)
    j = min(len(bus), i + len(sig))
    bus[max(i, 0):j] += gain * sig[s0: j - i]


# ---------- instrumentos ----------
_cache = {}


def piano(m, dur, vel=1.0):
    """Piano abafado ("felt"): parciais levemente inarmônicas, agudos morrendo rápido, ataque macio."""
    key = (m, round(dur, 2), round(vel, 2))
    if key in _cache:
        return _cache[key]
    f, t = hz(m), tt(dur)
    rng = np.random.default_rng(m)
    s = np.zeros_like(t)
    for k in range(1, 14):
        fk = k * f * np.sqrt(1 + 0.0004 * k * k)
        if fk > 7000:
            break
        a = (0.6 + 0.4 * vel) / k ** (2.2 - 0.6 * vel)
        s += a * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-(1.1 + 0.9 * k) * t)
    s *= np.minimum(1, t / 0.006)                     # o feltro amacia o ataque
    thump = filt(rng.standard_normal(len(t)), "lowpass", 600) * np.exp(-t * 60) * 0.05
    s = filt(s + thump, "lowpass", 2600 + 1500 * vel)
    r = min(len(s), int(0.25 * SR))
    s[-r:] *= np.linspace(1, 0, r)
    _cache[key] = norm(s) * vel
    return _cache[key]


def pad(notes, dur, att=1.2, rel=1.5):
    t = tt(dur)
    rng = np.random.default_rng(len(notes) + int(dur * 10))
    s = np.zeros_like(t)
    for m in notes:
        for det in (-0.07, 0.0, 0.07):
            f = hz(m) * 2 ** (det / 12)
            for k in range(1, 10):
                if k * f > 2500:
                    break
                s += (0.8 ** k / k) * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 6.28))
    s *= 1 + 0.08 * np.sin(2 * np.pi * 0.23 * t)        # respiração lenta
    env = np.minimum(1, t / att) * np.clip((dur - t) / rel, 0, 1)
    return norm(filt(s, "lowpass", 1400) * env)


def sub(m, dur):
    t = tt(dur)
    s = np.sin(2 * np.pi * hz(m) * t) + 0.25 * np.sin(4 * np.pi * hz(m) * t)
    env = np.minimum(1, t / 0.03) * np.exp(-t * 1.4)
    r = min(len(s), int(0.08 * SR))
    env[-r:] *= np.linspace(1, 0, r)
    return norm(s * env)


def kick():
    t = tt(0.35)
    s = np.sin(2 * np.pi * np.cumsum(46 + 60 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
    return norm(filt(s, "lowpass", 180))


def tick(open_=False):
    t = tt(0.12 if open_ else 0.05)
    rng = np.random.default_rng(7 if open_ else 3)
    return norm(filt(rng.standard_normal(len(t)), "bandpass", [5000, 11000])
                * np.minimum(1, t / 0.004) * np.exp(-t * (35 if open_ else 90)))


def chime(m, dur=2.5):
    f, t = hz(m), tt(dur)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
            for r, a, d in ((1, 1, 1.6), (2.0, 0.25, 3.5), (3.01, 0.08, 7), (5.4, 0.03, 12)))
    return norm(s * np.minimum(1, t / 0.003))


def reverb(x, sec=2.2, seed=11):
    """Reverb simples: convolução com ruído decaindo (sala média, escura)."""
    rng = np.random.default_rng(seed)
    t = tt(sec)
    ir = filt(rng.standard_normal(len(t)), "lowpass", 3500) * np.exp(-t * 6.9 / sec)
    ir[: int(0.012 * SR)] = 0                           # pré-delay
    return fftconvolve(x, ir / np.sqrt((ir ** 2).sum()))[: len(x)]


# ---------- arranjo ----------
def render(out, marks=None):
    mk = dict(MARKS, **(marks or {}))
    n = int(SR * mk["end"])
    bus = {k: np.zeros(n) for k in ("pad", "piano", "sub", "kick", "tick", "chime")}
    t0, cut, fecho = mk["t0"], mk["cut"], mk["fecho"]

    def chord(bar):
        return CHORDS[bar % len(CHORDS)]

    nbars = int((cut - t0) / BAR) + 1
    for b in range(-1, nbars):
        tb = t0 + b * BAR
        root, notes = chord(b)
        add(bus["pad"], pad(notes, BAR + 1.6), tb, 1.0)
        if tb + BAR > mk["pulse"]:
            add(bus["sub"], sub(root, BAR), max(tb, mk["pulse"]), 1.0)
        for q in range(4):
            tq = tb + q * BEAT
            if tq < mk["pulse"] - 1e-3:
                # arpejo lento: um toque por tempo (e um respiro no último tempo a cada 4 compassos)
                if b % 4 == 3 and q == 3:
                    continue
                m, v = ((notes[0], .8), (notes[2], .55), (notes[3] + 12 * (b % 2 == 0), .5), (notes[1], .4))[q]
                add(bus["piano"], piano(m, 2.4, v), tq, 1.0)
                continue
            # pulso: bumbo no 1 e no 3, piano repetindo em colcheias, a melodia no 1º tempo
            if q in (0, 2):
                add(bus["kick"], kick(), tq, 1.0 if q == 0 else 0.8)
            if q == 0:
                add(bus["piano"], piano(notes[3] + 12, 2.0, 0.55), tq, 1.0)
            for e in range(2):
                te = tq + e * BEAT / 2
                add(bus["piano"], piano(notes[1] if e == 0 else notes[2], 0.9, 0.42 - 0.08 * e), te)
                add(bus["tick"], tick(e == 1), te, 0.5 if e == 1 else 0.3)
                # a lista: semicolcheias até "Na sexta mesmo"
                if mk["noise"] <= te < mk["friday"]:
                    add(bus["tick"], tick(), te + BEAT / 4, 0.28)
    # "Na sexta mesmo": acorde cheio no 1º tempo
    root, notes = chord(int(round((mk["friday"] - t0) / BAR)))
    for m in notes + [notes[0] + 12]:
        add(bus["piano"], piano(m, 2.6, 0.7), mk["friday"], 0.6)
    for tc in mk["chimes"]:
        add(bus["chime"], chime(78), tc, 1.0)            # F#5
        add(bus["chime"], chime(85), tc + 0.18, 0.5)     # C#6

    # fecho: pad em Ré e três notas, tudo bem baixo
    fdur = mk["end"] - fecho
    add(bus["pad"], pad(CHORDS[0][1], fdur, att=1.4, rel=2.0), fecho, 0.8)
    for i, m in enumerate((66, 69, 74)):                  # F#4 A4 D5
        add(bus["piano"], piano(m, 3.0, 0.45), fecho + 0.6 + i * 1.2, 1.0)

    # ---------- mixagem ----------
    gain = {"pad": 0.30, "piano": 0.34, "sub": 0.30, "kick": 0.45, "tick": 0.07, "chime": 0.16}
    dry = sum(bus[k] * g for k, g in gain.items())
    wet = reverb(bus["piano"] * gain["piano"] + bus["chime"] * gain["chime"] + bus["pad"] * 0.1)
    L = dry + 0.35 * wet
    R = dry.copy()
    d = int(0.011 * SR)                                   # largura: o eco curto do reverb num lado
    R[d:] += 0.35 * wet[:-d]

    # o corte do P7: zera de uma vez (15 ms para não estalar) e só volta no fecho
    g = np.ones(n)
    a, b = int(cut * SR), int(fecho * SR)
    g[a:b] = 0.0
    g[a - 720:a] = np.linspace(1, 0, 720)
    g[: int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))   # entrada suave
    fo = int((mk["end"] - 1.8) * SR)                          # fim: some nos últimos 1,8 s
    g[fo:] *= np.linspace(1, 0, n - fo) ** 1.5
    # no fecho a trilha fica bem mais baixa que no resto
    g[b:] *= 0.55
    L, R = L * g, R * g

    mix = np.stack([L, R], axis=1)
    mix = np.tanh(1.2 * mix / np.abs(mix).max()) / np.tanh(1.2)
    mix *= 10 ** (-1 / 20)                                 # pico em -1 dBFS; o build ajusta o nível
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    return out


if __name__ == "__main__":
    print(render(sys.argv[1] if len(sys.argv) > 1 else "audios/trilha-03.wav"))
