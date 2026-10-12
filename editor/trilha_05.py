"""Trilha original do Reel 05 "Os 6 dias da Zoe · Parte 3": tudo sintetizado aqui (sem samples).

Derivada de trilha_04.py (a parte animada do vislumbre: marimba, baixo pluck, bumbo macio, palmas e shaker) e
de trilha_03.py (o piano abafado, o pad, o sino e o reverb). As seções seguem os blocos de build_05.py:
  gancho            o mesmo groove, mas suave sob a voz (sem palmas, bumbo e baixo bem baixos). Do fim de "sete
                    minutos" até o fim da cartela DIA 6 (o respiro): só o pad, sem nenhum ataque
  P2 → P5           "correndo": 120 BPM, a mesma progressão da parte animada do Ep. 2 (Ré · Lá/Dó# · Si m · Sol),
                    com uma marca leve em cada passagem da Zoe numa câmera (o acorde na marimba e um bumbo macio,
                    ~10 dB abaixo do resto, com o duck da voz). A grade é elástica: entre duas passagens cabe um
                    número inteiro de tempos (0,47 a 0,53 s), então cada passagem cai num 1º tempo
  P6                baixa: só o pad, o baixo no 1º tempo e a marimba em semínimas, bem mais baixo
  P7                depois de "seis dias de busca" vira só um pad em Ré e corta de vez antes de "A gente estava
                    muito longe de alcançar ela" (fade de 0,12 s)
  cartela QUI       volta contida: pad + piano abafado em arpejo lento (75 BPM), como no Ep. 1
  spoiler (camera9) abre um pouco: swell, o pad sobe uma oitava, sino e a marimba em colcheias lentas
  fecho             a trilha some em 0,6 s: só o som ambiente
  cartelas          o sino de trilha_03 quando o contador pulsa (6 DIAS, QUI 24/09); na cartela DIA 6, nada

Os tempos vêm de build_05.py (ele chama render() com os valores reais). Rodando sozinho, usa MARKS.

Uso (numpy + scipy):
  python editor/trilha_05.py audios/trilha-05.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trilha_03 as t3   # noqa: E402  instrumentos do Ep. 1
from trilha_03 import SR, add, chime, filt, kick, norm, pad, piano, reverb, tick, tt   # noqa: E402
from trilha_04 import GROOVE, ARP, bass, clap, marimba, swell   # noqa: E402  instrumentos do Ep. 2

BEAT = 0.5                      # 120 BPM na parte "correndo" (o tempo nominal; a grade se ajusta às passagens)
CALM = t3.BEAT                  # 75 BPM na parte contida (quinta)

# marcas em segundos na linha do tempo do Reel (valores de build_05.py)
MARKS = {
    "t0": 0.10,                 # 1º tempo da grade
    "hits": [(11.6, 0.45), (14.5, 1.0), (21.0, 1.0), (23.5, 1.0), (24.9, 1.0), (27.2, 1.0), (28.9, 1.0),
             (35.6, 1.0)],      # passagens da Zoe (tempos fortes): (instante, ganho)
    "baixa": 40.40,             # P6: a trilha baixa
    "pad": 49.75,               # depois de "seis dias de busca": só o pad
    "corte": 55.70,             # antes de "A gente estava muito longe": zera
    "qui": 58.15,               # a cartela da quinta: volta contida
    "spoiler": 71.13,           # camera9: abre um pouco
    "fecho": 72.99,             # só o ambiente
    "end": 76.60,
    "chimes": [48.55, 58.25],
    "gancho": 5.07,             # fim do gancho (início do P2): até aqui o groove é suave, sem pancada sob a voz
    "respiro": (3.92, 5.07),    # o fim de "sete minutos", o gancho parado e a cartela DIA 6: só o pad, sem ataque
}


def grade(t0, hits, fim):
    """A grade elástica: os tempos de t0 a fim, com cada passagem (hits) caindo num tempo e começando um
    compasso novo. Devolve [(instante, índice do tempo no compasso, nº do acorde)]."""
    ancoras = [t0] + [h for h in hits if t0 < h < fim] + [fim]
    out, acorde = [], 0
    for i, (a, b) in enumerate(zip(ancoras, ancoras[1:])):
        n = max(1, round((b - a) / BEAT))
        dt = (b - a) / n
        if i > 0:                                         # a passagem: compasso novo, acorde seguinte
            acorde += 1
        q = 0
        for k in range(n):
            if q == 4:
                q = 0
                acorde += 1
            out.append((a + k * dt, q, acorde, dt))
            q += 1
    return out


ACENTO = 0.3                    # o acento das passagens: 0,3x o ganho de antes (≈ -10 dB)


def macio(s, ataque=0.015, corte=1500):
    """Arredonda o ataque: entrada em rampa de `ataque` s e passa-baixa em `corte` Hz."""
    s = filt(s, "lowpass", corte)
    r = int(ataque * SR)
    s = s.copy()
    s[:r] *= np.linspace(0, 1, r) ** 2
    return s


def render(out, marks=None, acc_out=None):
    """Escreve a trilha em `out`. Com `acc_out`, as marcas das passagens saem num arquivo à parte (o build mistura
    esse acento com o mesmo duck da voz e o mesmo ganho de cada trecho)."""
    mk = dict(MARKS, **(marks or {}))
    n = int(SR * mk["end"])
    names = ("pad", "piano", "chime", "mar", "bass", "kick", "clap", "tick", "fx", "a_mar", "a_kick")
    bus = {k: np.zeros(n) for k in names}
    t0, baixa, padt, corte, qui, spo, fecho = (mk[k] for k in ("t0", "baixa", "pad", "corte", "qui", "spoiler", "fecho"))
    gancho, (r0, r1) = mk["gancho"], mk["respiro"]

    # ---------- "correndo" (do gancho ao P6) e a parte baixa (P6 e o começo do P7)
    g = grade(t0, [h for h, _ in mk["hits"]], padt)
    for i, (tb, q, ac, dt) in enumerate(g):
        root, notes = GROOVE[ac % len(GROOVE)]
        corre = tb < baixa
        suave = tb < gancho                               # no gancho: sem palmas, bumbo e baixo bem baixos
        resp = r0 - 0.05 <= tb < r1                       # o respiro: nenhum ataque, só o pad
        if q == 0:                                        # o pad do compasso
            dur = min(4 * dt + 1.2, padt - tb + 0.8)
            add(bus["pad"], pad([m - 12 for m in notes[1:]] + [notes[3]], dur, att=0.6 if resp else 0.35, rel=0.9),
                tb, 0.35 if corre else 0.5)
            if not resp:
                add(bus["bass"], bass(root, 0.45), tb, (0.35 if suave else 1.0) if corre else 0.8)
        if resp:
            continue
        if not corre:                                     # baixa: a marimba em semínimas, suave
            add(bus["mar"], marimba(notes[ARP[q * 2 % 8]], 0.42), tb, 0.8)
            continue
        for e in range(2):                                # colcheias
            te = tb + e * dt / 2
            if r0 - 0.05 <= te < r1:
                continue
            v = (0.62 if e == 0 else 0.45) * (0.6 if suave else 1.0)
            add(bus["mar"], marimba(notes[ARP[(q * 2 + e) % 8]] + (12 if (q * 2 + e) in (3, 6) else 0), v), te)
            add(bus["tick"], tick(e == 1), te, (0.35 if e else 0.22) * (0.5 if suave else 1.0))
            add(bus["tick"], tick(), te + dt / 4, 0.14 * (0.5 if suave else 1.0))
        if q in (0, 2):
            add(bus["kick"], kick(), tb, (1.0 if q == 0 else 0.75) * (0.15 if suave else 1.0))
        if q in (1, 3) and not suave:
            add(bus["clap"], clap(), tb, 0.8)
        if q == 1:                                        # baixo: 1, o "e" do 2 e o 3
            add(bus["bass"], bass(root, 0.42), tb + dt / 2, 0.7 * (0.35 if suave else 1.0))
        if q == 2:
            add(bus["bass"], bass(root + 12, 0.42), tb, 0.7 * (0.35 if suave else 1.0))

    # as passagens da Zoe: marcadas de leve (barramentos próprios, ~10 dB abaixo do que era): o acorde na marimba e
    # um bumbo macio, com o ataque arredondado (entrada de 15 ms e passa-baixa em 1,5 kHz). Sem sino e sem prato.
    for h, hg in mk["hits"]:
        ac = next((a for (tb, q, a, dt) in g if abs(tb - h) < 1e-6), 0)
        root, notes = GROOVE[ac % len(GROOVE)]
        for m in notes + [notes[1] + 12, notes[3] + 12]:
            add(bus["a_mar"], marimba(m, 0.8), h, ACENTO * 0.7 * hg)
        add(bus["a_kick"], macio(kick()), h, ACENTO * 1.0 * hg)
        add(bus["a_kick"], macio(bass(root, 0.6)), h, ACENTO * 0.9 * hg)

    # P7: só o pad em Ré, de "busca" até o corte
    add(bus["pad"], pad([50, 57, 62, 66, 69], corte - padt + 1.0, att=0.5, rel=0.3), padt - 0.25, 0.75)

    # ---------- a quinta: contida (pad + piano abafado, 75 BPM) até o spoiler
    nbars = int((spo - qui) / (4 * CALM)) + 2
    for b in range(nbars):
        tb = qui + 0.10 + b * 4 * CALM
        if tb >= spo - 0.05:
            break
        root, notes = t3.CHORDS[b % len(t3.CHORDS)]
        add(bus["pad"], pad(notes, min(4 * CALM + 1.6, spo - tb + 1.0)), tb, 0.8)
        for q in range(4):
            tq = tb + q * CALM
            if tq >= spo - 0.1 or (b % 4 == 3 and q == 3):
                continue
            m, v = ((notes[0], .8), (notes[2], .55), (notes[3] + 12 * (b % 2 == 0), .5), (notes[1], .4))[q]
            add(bus["piano"], piano(m, 2.4, v), tq, 1.0)

    # ---------- o spoiler: abre um pouco
    add(bus["fx"], swell(1.2), spo - 1.2, 0.25)
    sdur = fecho - spo + 0.6
    add(bus["pad"], pad([50, 57, 62, 66, 69, 74], sdur, att=0.3, rel=0.6), spo, 0.9)
    add(bus["pad"], pad([69, 74, 78], sdur, att=0.5, rel=0.6), spo, 0.4)
    add(bus["chime"], chime(86, 2.5), spo, 0.6)
    add(bus["chime"], chime(90, 2.0), spo + 0.14, 0.3)
    for k, m in enumerate([62, 66, 69, 74, 78, 74, 69, 66, 62, 66, 69, 74]):
        tk = spo + k * CALM / 2
        if tk < fecho - 0.1:
            add(bus["mar"], marimba(m, 0.5), tk, 0.8)

    for tc in mk["chimes"]:                             # (na cartela DIA 6 não tem: ela entra sem ataque)
        add(bus["chime"], chime(78), tc, 1.0)           # F#5
        add(bus["chime"], chime(85), tc + 0.18, 0.5)    # C#6

    # ---------- mixagem
    gain = {"pad": 0.30, "piano": 0.34, "chime": 0.16, "mar": 0.30, "bass": 0.32, "kick": 0.40,
            "clap": 0.09, "tick": 0.07, "fx": 0.20, "a_kick": 0.40}
    gain["a_mar"] = gain["mar"]

    # envelope geral por seção (com transições curtas): correndo 1,0 · P6 0,55 · pad 0,5 · corte · quinta 0,55 ·
    # spoiler 0,85 · fecho: some em 0,6 s
    tax = np.arange(n) / SR
    ks = [(0.0, 0.0), (0.05, 1.0), (baixa - 0.3, 1.0), (baixa, 0.55), (padt - 0.25, 0.55), (padt, 0.5),
          (corte - 0.12, 0.5), (corte, 0.0), (qui - 0.05, 0.0), (qui + 0.25, 0.55), (spo - 1.2, 0.55),
          (spo, 0.85), (fecho, 0.85), (fecho + 0.6, 0.0), (mk["end"] + 1, 0.0)]
    env = np.interp(tax, [k[0] for k in ks], [k[1] for k in ks])

    def mixdown(keys):
        dry = sum(bus[k] * gain[k] for k in keys)
        wsrc = {"piano": 1.0, "chime": 1.0, "a_chime": 1.0, "pad": 0.1 / gain["pad"], "mar": 0.6, "a_mar": 0.6,
                "clap": 1.0}
        wet = reverb(sum(bus[k] * gain[k] * wsrc[k] for k in keys if k in wsrc) + np.zeros(n))
        L = dry + 0.33 * wet
        R = dry.copy()
        d = int(0.011 * SR)
        R[d:] += 0.33 * wet[:-d]
        return np.stack([L * env, R * env], axis=1)

    def write(path, mix):
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())

    acc_keys = ("a_mar", "a_kick")
    main = mixdown([k for k in names if k not in acc_keys])
    acc = mixdown(acc_keys)
    if acc_out is None:
        mix = main + acc
        mix = np.tanh(1.2 * mix / np.abs(mix).max()) / np.tanh(1.2)
        write(out, mix * 10 ** (-1 / 20))
    else:
        k = 10 ** (-1 / 20) / np.abs(main + acc).max()
        write(out, main * k)
        write(acc_out, acc * k)
    return out


if __name__ == "__main__":
    print(render(sys.argv[1] if len(sys.argv) > 1 else "audios/trilha-05.wav"))
