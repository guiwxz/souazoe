"""Trilha original do Reel 02 "Tchau, cartaz": 120 BPM, Fá maior, ukulele + batida leve.

Tudo é sintetizado aqui (sem samples), então não há questão de direito autoral.
As seções seguem os cortes de build_02.py (1 tempo = 0,5 s):
  0–4 s    intro: ukulele + estalos, virada e um respiro antes do drop
  4–10 s   drop: os cartazes sendo arrancados, um por tempo forte
  10–12 s  respiro: a Zoe "ajudando" (sem bumbo e sem baixo); a música some por um
           instante antes de 12 s, para o rasgo soar sozinho
  12–15,5 s volta: o drop cai no corte para o poste já sem cartaz ("fácil."),
           segue no "fiscalizando" e o último cartaz sai em 15,5 s
  16–19,5 s final: resolve em Fá quando a Zoe aparece em casa (pad + glockenspiel)

Uso (numpy + scipy num venv temporário):
  python editor/trilha_02.py audios/trilha-02.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BEAT = 0.5                      # 120 BPM
BAR = 4 * BEAT
DUR = 19.5
N = int(SR * DUR)
rng = np.random.default_rng(2409)

# acordes por compasso (2 s cada): I–V–vi–IV e fecha em Fá
UKE = {"F": [65, 69, 72, 77], "C": [64, 67, 72, 76], "Dm": [62, 65, 69, 74], "Bb": [65, 70, 74, 77]}
ROOT = {"F": 41, "C": 36, "Dm": 38, "Bb": 34}
PROG = ["F", "C", "Dm", "Bb", "F", "C", "Dm", "Bb", "F", "F"]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def add(bus, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(bus) or i < 0:
        return
    j = min(len(bus), i + len(sig))
    bus[i:j] += gain * sig[: j - i]


def norm(x):
    return x / max(1e-9, np.abs(x).max())


def release(x, sec=0.03):
    r = min(len(x), int(sec * SR))
    x[-r:] *= np.linspace(1, 0, r)
    return x


# ---------- instrumentos ----------
_pl = {}
def pluck(m, dur):
    """Corda dedilhada (aditiva): harmônicos agudos morrem antes, como num ukulele."""
    key = (m, round(dur, 3))
    if key in _pl:
        return _pl[key]
    f, t = hz(m), tt(dur)
    s = np.zeros_like(t)
    for k in range(1, 25):
        if k * f > 9000:
            break
        a = (abs(np.sin(np.pi * k * 0.18)) + 0.05) / k ** 1.1
        s += a * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 6.28)) * np.exp(-(3.2 + 1.5 * k ** 1.3) * t)
    s *= np.minimum(1, t / 0.002)
    nz = int(0.006 * SR)
    s[:nz] += 0.12 * rng.standard_normal(nz) * np.exp(-tt(0.006) * 900)
    _pl[key] = release(norm(s))
    return _pl[key]


def strum(bus, t, chord, dur, up=False, vel=1.0):
    notes = UKE[chord][::-1] if up else UKE[chord]
    if up:
        notes, vel = notes[:3], vel * 0.7
    for i, m in enumerate(notes):
        add(bus, pluck(m, dur), t + i * 0.011, vel * (0.9 + 0.1 * rng.random()))


def bass(m, dur):
    f, t = hz(m), tt(dur)
    s = sum((1 / k) * np.sin(2 * np.pi * k * f * t) * np.exp(-(2.2 + 0.8 * k) * t)
            for k in range(1, 14) if k * f < 1400)
    return release(norm(s * np.minimum(1, t / 0.004)), 0.02)


def kick():
    t = tt(0.4)
    s = np.sin(2 * np.pi * np.cumsum(48 + 115 * np.exp(-t * 28)) / SR) * np.exp(-t * 7.5)
    c = int(0.003 * SR)
    s[:c] += 0.3 * rng.standard_normal(c)
    return np.tanh(1.8 * s)


def clap():
    t = tt(0.35)
    env = np.zeros_like(t)
    for d in (0, 0.009, 0.019):
        i = int(d * SR)
        env[i:] += 0.7 * np.exp(-t[: len(t) - i] * 150)
    env += 0.6 * np.exp(-np.maximum(t - 0.022, 0) * 15) * (t >= 0.022)
    return norm(filt(rng.standard_normal(len(t)) * env, "bandpass", [900, 4200]))


def snare():
    t = tt(0.22)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35)
    nz = filt(rng.standard_normal(len(t)), "bandpass", [1500, 7000]) * np.exp(-t * 22)
    return norm(0.6 * body + nz)


def hat(open_=False):
    t = tt(0.35 if open_ else 0.06)
    return norm(filt(rng.standard_normal(len(t)), "highpass", 7000) * np.exp(-t * (10 if open_ else 70)))


def snap():
    t = tt(0.12)
    s = filt(rng.standard_normal(len(t)), "bandpass", [1500, 5000]) * np.exp(-t * 110)
    return norm(s + 0.4 * np.sin(2 * np.pi * 1850 * t) * np.exp(-t * 160))


def shaker():
    t = tt(0.09)
    return norm(filt(rng.standard_normal(len(t)), "bandpass", [4000, 11000])
                * np.minimum(1, t / 0.015) * np.exp(-t * 45))


def glock(m, dur=1.6):
    f, t = hz(m), tt(dur)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
            for r, a, d in ((1, 1, 2.2), (2.756, 0.35, 6), (5.404, 0.15, 12), (8.933, 0.06, 18)))
    return release(norm(s * np.minimum(1, t / 0.001)))


def pad(chord, dur, att=0.4, rel=0.9):
    t = tt(dur)
    s = np.zeros_like(t)
    for m in UKE[chord]:
        for det in (-0.08, 0.0, 0.08):
            f = hz(m) * 2 ** (det / 12)
            for k in range(1, 16):
                if k * f > 3000:
                    break
                s += (0.9 ** k / k) * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 6.28))
    env = np.minimum(1, t / att) * np.clip((dur - t) / rel, 0, 1)
    return norm(filt(s, "lowpass", 1800) * env)


def crash(dur=2.0):
    t = tt(dur)
    s = filt(rng.standard_normal(len(t)), "highpass", 4500) * np.exp(-t * 2.2)
    for f in (3150, 4430, 5870, 7120):
        s += 0.08 * np.sin(2 * np.pi * f * t) * np.exp(-t * 3)
    return norm(s)


def riser(dur):
    t = tt(dur)
    x = t / dur
    nz = filt(rng.standard_normal(len(t)), "highpass", 1500) * x ** 2
    tone = 0.25 * x * np.sin(2 * np.pi * np.cumsum(250 + 900 * x ** 2) / SR)
    return norm(0.6 * nz + tone)


# ---------- arranjo ----------
bus = {k: np.zeros(N) for k in ("kick", "clap", "hat", "perc", "bass", "uke", "glock", "pad", "fx")}
kicks = []


def chord_at(t):
    return PROG[min(int(t // BAR), len(PROG) - 1)]


def strum_bar(t0, vel, until=None):
    # D . D U . U D U  (colcheias): a "batida de ukulele" clássica
    pat = [(0, False), (2, False), (3, True), (5, True), (6, False), (7, True)]
    for i, (step, up) in enumerate(pat):
        t = t0 + step * BEAT / 2
        if until is not None and t >= until:
            break
        nxt = pat[i + 1][0] if i + 1 < len(pat) else 8
        strum(bus["uke"], t, chord_at(t0), (nxt - step) * BEAT / 2 + 0.08, up, vel)


def groove(t0, t1, fill_at=None):
    t = t0
    while t < t1 - 1e-6:
        beat = round((t % BAR) / BEAT)
        add(bus["kick"], kick(), t); kicks.append(t)
        if beat in (1, 3):
            add(bus["clap"], clap(), t)
        add(bus["hat"], hat(beat == 3), t + BEAT / 2, 0.8 if beat == 3 else 0.55)
        add(bus["hat"], hat(), t + BEAT / 4, 0.2)
        add(bus["hat"], hat(), t + 3 * BEAT / 4, 0.2)
        t += BEAT
    # baixo: F . . F F' . F C'  (saltos de oitava e quinta)
    t = t0
    while t < t1 - 1e-6:
        r = ROOT[chord_at(t)]
        for step, iv, ln in ((0, 0, 1.6), (3, 0, 0.9), (4, 12, 0.9), (6, 0, 0.9), (7, 7, 0.9)):
            ts = t + step * BEAT / 2
            if ts < t1 - 1e-6:
                add(bus["bass"], bass(r + iv, ln * BEAT / 2), ts)
        t += BAR


def roll(t0, t1, gap_at=None):
    """Virada de caixa acelerando (colcheia → semicolcheia → fusa) até o drop."""
    t, v = t0, 0.3
    while t < t1 - 1e-6:
        add(bus["perc"], snare(), t, v)
        frac = (t - t0) / (t1 - t0)
        t += BEAT / 2 if frac < 0.35 else BEAT / 4 if frac < 0.7 else BEAT / 8
        v = min(1.0, v + 0.08)


# intro 0–4
strum_bar(0.0, 0.8)
strum_bar(2.0, 0.8, until=3.6)
for t in (0.5, 1.5, 2.5, 3.5):
    add(bus["perc"], snap(), t, 0.6)
for i in range(32):
    add(bus["perc"], shaker(), i * BEAT / 4, 0.18 if i % 2 else 0.1)
for t in np.arange(2.25, 3.0, BEAT):
    add(bus["hat"], hat(), t, 0.35)
roll(3.0, 3.9)
add(bus["fx"], riser(0.9), 3.0, 0.5)

# drop 4–10
add(bus["fx"], crash(), 4.0, 0.55)
groove(4.0, 10.0)
for t0 in (4.0, 6.0, 8.0):
    strum_bar(t0, 0.9)
roll(9.5, 9.95)

# respiro 10–12: a Zoe ajudando
for t, d in ((10.0, 1.0), (11.0, 0.6)):
    strum(bus["uke"], t, "C", d, vel=0.7)
for i, m in enumerate([79, 84, 88, 84, 79, 84, 88, 89]):        # G5 C6 E6 C6 G5 C6 E6 F6
    add(bus["glock"], glock(m), 10.0 + i * BEAT / 2, 0.8 if i % 2 == 0 else 0.6)
for t in (10.5, 11.5):
    add(bus["perc"], snap(), t, 0.5)
roll(11.25, 11.9)
add(bus["fx"], riser(0.9), 11.0, 0.35)

# volta 12–15,5: o "rasgo da Zoe" cai no drop; fiscalizando; último cartaz em 15,5 s
add(bus["fx"], crash(), 12.0, 0.55)
groove(12.0, 15.5)
strum_bar(12.0, 0.9)
strum_bar(14.0, 0.9, until=15.5)
add(bus["kick"], kick(), 15.5); kicks.append(15.5)
add(bus["clap"], clap(), 15.5, 1.0)
add(bus["fx"], crash(2.5), 15.5, 0.5)
add(bus["bass"], bass(ROOT["Bb"], 0.5), 15.5, 0.9)
strum(bus["uke"], 15.5, "Bb", 0.55, vel=0.8)

# final 16–19,5: a Zoe em casa, resolve em Fá
add(bus["pad"], pad("F", 3.5, att=0.3, rel=1.8), 16.0)
for t, m in ((16.0, 81), (16.25, 84), (16.5, 89), (17.0, 84), (17.5, 81), (18.0, 77)):   # A5 C6 F6 C6 A5 F5
    add(bus["glock"], glock(m, 2.2), t, 0.7)
for i, m in enumerate([65, 69, 72, 77, 72, 69]):                 # arpejo de Fá
    add(bus["uke"], pluck(m, 0.9), 16.75 + i * BEAT / 2, 0.45)
strum(bus["uke"], 16.0, "F", 2.6, vel=0.75)
add(bus["bass"], bass(ROOT["F"], 2.6), 16.0, 0.6)

# ---------- mixagem ----------
sc = np.ones(N)                                     # sidechain do bumbo (efeito "respiração")
for tk in kicks:
    i = int(tk * SR)
    seg = 1 - 0.5 * np.exp(-tt(0.3) * 12)
    j = min(N, i + len(seg))
    sc[i:j] = np.minimum(sc[i:j], seg[: j - i])

gain = {"kick": 0.85, "clap": 0.4, "hat": 0.16, "perc": 0.3, "bass": 0.5,
        "uke": 0.26, "glock": 0.22, "pad": 0.16, "fx": 0.22}
pan = {"hat": (0.8, 1.0), "glock": (1.0, 0.8), "perc": (0.95, 1.0)}
L, R = np.zeros(N), np.zeros(N)
for k, x in bus.items():
    x = x * gain[k]
    if k in ("bass", "uke", "pad"):
        x = x * sc
    if k == "bass":
        x = filt(x, "lowpass", 900)
    gl, gr = pan.get(k, (1.0, 1.0))
    L += gl * x
    R += gr * x
    if k == "uke":                                   # largura: eco curto só num lado
        d = int(0.013 * SR)
        R[d:] += 0.35 * x[:-d]

# respiros antes dos drops (3,9–4,0 s e 11,9–12,0 s, onde o rasgo soa sozinho)
g = np.ones(N)
for t0, t1 in ((3.9, 4.0), (11.9, 12.0)):
    a, b = int(t0 * SR), int(t1 * SR)
    g[a:b] = 0.0
    g[a - 240:a] = np.linspace(1, 0, 240)
# fim: some devagar nos últimos 1,2 s
f0 = int((DUR - 1.2) * SR)
g[f0:] *= np.linspace(1, 0, N - f0) ** 1.5
L, R = L * g, R * g

mix = np.stack([L, R], axis=1)
mix = np.tanh(1.3 * mix / np.abs(mix).max()) / np.tanh(1.3)
mix *= 10 ** (-1 / 20)                               # pico em -1 dBFS; o loudnorm final ajusta
out = sys.argv[1] if len(sys.argv) > 1 else "audios/trilha-02.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print(out)
