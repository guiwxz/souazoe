"""Monta o Reel 04 "Os 6 dias da Zoe · Parte 2" (9:16, 30 fps, ~64 s), narrado pela Isabela.

Ep. 2 da série (dias 3, 4 e 5, dom 20 a ter 22/09): "o primeiro vislumbre". Segue o mapa de tempo de
roteiros/serie-6-dias/roteiro.md com os tempos reais da narração (editor/words-04.json).
Base: build_03.py (Ep. 1), copiado e adaptado.

Como funciona:
  1. Áudio: apara o silêncio de audios/dias3e4e5/1..6.ogg e encadeia os parágrafos (PARTS e GAPS). O P1 é
     aberto em dois em 2,44 s (a cartela DIA 3 entra no meio, com fades de 20 ms) e CUTS tira a hesitação
     do P4 (6,34 a 6,56 s). A pausa P4 → P5 (o vislumbre) é calculada para "vislumbre dela" cair no meio
     da travessia da CAM 5. Voz com highpass + afftdn. A trilha (editor/trilha_04.py) é gerada aqui com
     as marcas reais: calma, quase some no golpe e fica animada quando a Zoe entra na Câmera 03; fica por
     baixo da voz com duck (sidechain). Saem duas mixagens em -14 LUFS: com trilha e sem trilha (voz +
     ambiente do fecho).
  2. Imagem: cada quadro é composto em Python (Pillow), plano a plano (SHOTS): o vídeo da busca a pé, os
     prints em cartão (telefones e fotos de perfil borrados), as parecidas com o carimbo NÃO ERA ELA, os
     golpes com a etiqueta GERADA POR IA, as duas câmeras de segurança (quadros na memória, câmera lenta
     com mistura de quadros, zoom que acompanha a Zoe e o círculo lilás; na CAM 5 a notificação do
     celular fica borrada e escura, quase toda fora da janela), o mapa (a linha avança da Fagundes dos
     Reis até a Capitão Eleutério), as fachadas com as câmeras e a Zoe hoje.
  3. Texto (ASS, queimado pelo ffmpeg): legendas em blocos de até 3 palavras com a palavra ativa em
     amarelo, contador de 6 dias (já com 2 cheios), gancho, cartelas, etiquetas de horário e o fecho.

Requisitos: ffmpeg/ffprobe no PATH e um venv com Python 3.9, numpy, scipy e Pillow (o Python padrão da
máquina é 3.7, sem Pillow). As camadas do mapa saem de `python editor/mapa.py ep2-camadas`.
  py -3.9 -m venv <tmp>/venv
  <tmp>/venv/Scripts/pip install numpy scipy Pillow
Uso:
  <tmp>/venv/Scripts/python editor/build_04.py              render completo → saida/video/video4/
  <tmp>/venv/Scripts/python editor/build_04.py 36 52        só um trecho, para conferir → videos/ep2/trecho.mp4
  <tmp>/venv/Scripts/python editor/build_04.py palavras     refaz words-04.json a partir das transcrições em
                                                            videos/ep2/ (se PARTS/GAPS/TRECHOS mudarem)
As palavras vieram do faster-whisper (medium e large-v3, int8, venv 3.9, um arquivo por parágrafo), com a
grafia da fala (TEXTO) e os inícios/fins acertados pelos trechos de voz do envelope de energia (TRECHOS).
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "editor"))
import trilha_04   # noqa: E402  trilha original (numpy + scipy)

DRIVE = ROOT / "drive"
SET = DRIVE / "set26"
DIV = SET / "divulgacao"
D3 = SET / "dia 3e4e5"                               # vários arquivos sem extensão (JPEG/MP4 normais)
VOZ = ROOT / "audios" / "dias3e4e5"                  # a narração do Ep. 2 (1..6.ogg, um por parágrafo)
WORK = ROOT / "videos" / "ep2"                       # cópias de trabalho (não versionadas)
MAPS = ROOT / "videos" / "mapas"                     # camadas de `mapa.py ep2-camadas`
FONTS = ROOT / "editor" / "fonts"
WORDS = ROOT / "editor" / "words-04.json"
MUSIC = ROOT / "audios" / "trilha-04.wav"
OUTDIR = ROOT / "saida" / "video" / "video4"
OUT = OUTDIR / "04-os-6-dias-parte-2.mp4"
OUT_NAT = OUTDIR / "04-os-6-dias-parte-2-sem-musica.mp4"
ASS = OUTDIR / "legendas-04.ass"
W, H, FPS = 1080, 1920, 30
HANDLE = "@souazoe.pf"

# identidade
INK, CREAM, LILAC, PINK, MUTED = (0x17, 0x13, 0x1F), (0xF6, 0xF1, 0xE9), (0xB9, 0xA7, 0xF3), (0xEC, 0x48, 0x99), (0x6E, 0x66, 0x7A)


def ass_c(rgb):
    return "&H{:02X}{:02X}{:02X}&".format(rgb[2], rgb[1], rgb[0])


# ---------------------------------------------------------------- a fala (grafia e trechos de voz)
# o que ela falou (vale para as legendas; o whisper escreveu "zoos", "I…" e "cesta")
TEXTO = {
    1: "No domingo, a gente voltou para Passo Fundo. E foi praticamente o dia todo na rua, com várias pessoas, "
       "a pé e em cinco carros. Mas nada concreto.",
    2: "A partir daí, começamos a receber muitas mensagens e fotos de cachorros parecidos, de gente que achava "
       "que era ela. Tomamos vários sustos, e nessa altura até a gente estava duvidando se era ela ou não.",
    3: "E o golpe estava liberado, porque tivemos várias tentativas, Zoes geradas por IA e gente falando que ia "
       "ficar com ela.",
    # "acesso às" (e não "acessar as", como saiu no medium): a tônica cai no "cé" de a-CES-so, o large-v3 ouve
    # "acesso às" e é o texto do roteiro que ela leu
    4: "Mas foi na terça que a gente começou a ver uma luz no final do túnel. Finalmente, a gente conseguiu "
       "acesso às câmeras dos primeiros passos que ela deu ainda na sexta.",
    5: "Até então, a gente não tinha nenhum vislumbre dela.",
    6: "E a partir disso, a gente começou a seguir todo o percurso dela pelas câmeras.",
}
# trechos de voz de cada arquivo (envelope de energia: -35 dB do pico, pausas ≥ 90 ms): (início, fim, palavras)
# a contagem de palavras de cada trecho foi conferida transcrevendo cada trecho sozinho; no arquivo 1, o vale
# de 2,44 s (o corte do P1, entre "Fundo" e "e foi") também é uma fronteira
TRECHOS = {
    1: [(0.53, 2.44, 8), (2.44, 4.55, 8), (5.00, 7.97, 9), (8.30, 9.33, 3)],
    2: [(0.55, 1.32, 3), (1.42, 3.99, 6), (4.08, 5.73, 5), (5.86, 7.25, 6), (7.69, 9.23, 3), (9.51, 10.99, 6),
        (11.25, 12.77, 7)],
    3: [(0.11, 1.41, 5), (1.52, 2.10, 1), (2.19, 3.90, 3), (4.29, 5.14, 3), (5.25, 6.63, 5), (6.74, 7.59, 4)],
    4: [(0.24, 3.18, 16), (3.69, 6.27, 7), (6.66, 9.51, 9)],
    5: [(0.03, 2.48, 9)],
    6: [(0.25, 3.66, 13), (3.85, 4.55, 2)],
}

# ---------------------------------------------------------------- áudio e linha do tempo
# (arquivo, início, fim) em segundos: a fala sem o silêncio da gravação (≈ 80 ms antes da primeira
# sílaba e ≈ 150 ms depois da última, pelo envelope de energia)
PARTS = [
    (1, 0.45, 2.44),    # P1a: No domingo, a gente voltou para Passo Fundo.   (corte num vale de -33 dB)
    (1, 2.44, 9.48),    # P1b: E foi praticamente o dia todo na rua ... Mas nada concreto.
    (2, 0.47, 12.92),   # P2: A partir daí, começamos a receber ... se era ela ou não.
    (3, 0.03, 7.75),    # P3: E o golpe estava liberado ... gente falando que ia ficar com ela.
    (4, 0.16, 9.66),    # P4: Mas foi na terça ... dos primeiros passos que ela deu ainda na sexta.
    (5, 0.00, 2.63),    # P5: Até então, a gente não tinha nenhum vislumbre dela.
    (6, 0.17, 4.70),    # P6: E a partir disso, a gente começou a seguir todo o percurso dela pelas câmeras.
]
# silêncio tirado de dentro de um arquivo: {arquivo: [(início, fim), ...]}
CUTS = {4: [(6.34, 6.56)]}   # "câmeras" (termina em 6,28) → "dos" (começa em 6,65): a hesitação cai para ~0,15 s
FADES = {0: (0.015, 0.020), 1: (0.020, 0.040)}   # (entrada, saída) por parte; o corte do P1 leva 20 ms dos dois lados
LEAD = 0.20                                      # antes da primeira palavra
GAPS = [1.00, 1.00, 0.45, 1.00, None, 1.00]      # respiro depois de cada parte
#       └ DIA 3 └ DIA 4     └ DIA 5 └ o vislumbre: calculado em _timeline() (≈ 4,5 s)
VISL_SYNC = 0.40     # "dela." termina 0,4 s depois do meio da travessia na CAM 5 ("vislumbre dela" fica em volta)
FACHADA = 1.60       # cada fachada com câmera (#19, #20, #21), a partir de "pelas câmeras"
FECHO = 5.50         # a Zoe hoje, sem voz


def _segments(f, a, b):
    """Trechos do arquivo que entram na montagem: (a, b) menos os CUTS."""
    segs, t = [], a
    for c0, c1 in CUTS.get(f, []):
        if a < c0 < b:
            segs.append((t, c0))
            t = c1
    return segs + [(t, b)]


def _removed(f, t):
    """Quanto silêncio foi tirado do arquivo f antes do instante local t."""
    return sum(min(c1, max(t, c0)) - c0 for c0, c1 in CUTS.get(f, []))


def _dur(i):
    f, a, b = PARTS[i]
    return b - a - _removed(f, b) + _removed(f, a)


# ---------------------------------------------------------------- câmeras de segurança
# #17 Câmera 03 (sex 18/09, 08h43, 368x416, 15 fps) e #18 CAM 5 (08h44, o celular filmando o monitor de
# lado: girado com transpose=2 fica 850x474). `lenta`: [(s, v)] = velocidade v a partir do instante s do
# clipe; `vista`: (largura, altura, centro x, centro y) do cartão na tela. `trilha`: onde a Zoe está
# (s, x, y em px do quadro original), medido por diferença de quadros (na CAM 5, com o quadro estabilizado).
CAMS = {
    "c3": {"src": D3 / "filmagemzoe1", "vf": "null", "size": (368, 416), "load": (0.0, 8.2),
           "ss": 0.0, "se": 8.0, "lenta": [(4.70, 0.5), (6.80, 1.0)],     # ela passa atrás do portão de 5,13 a 6,73 s
           "vista": (980, 1108, 540, 844), "anel": 88, "zoom": (4.6, 5.9, 2.0),     # x 50–1030, y 290–1398
           "trilha": [(5.13, 114, 145), (5.20, 120, 145), (5.33, 127, 146), (5.47, 138, 147), (5.60, 149, 147),
                      (5.73, 161, 149), (5.87, 186, 149), (5.93, 187, 155), (6.07, 212, 158), (6.20, 231, 163),
                      (6.33, 254, 172), (6.47, 300, 171), (6.53, 322, 172), (6.60, 339, 190), (6.73, 364, 196)]},
    "c5": {"src": D3 / "filmagemzoe2", "vf": "transpose=2", "size": (850, 474), "load": (5.2, 8.0),
           "ss": 5.30, "se": 7.80, "lenta": [(5.95, 0.5), (7.55, 1.0)],   # ela atravessa de 5,97 a 7,53 s
           "vista": (1000, 667, 540, 780), "anel": 64, "zoom": (None, 1.3),         # x 40–1040, y 447–1114
           "trilha": [(5.97, 641, 124), (6.10, 621, 129), (6.23, 601, 134), (6.37, 576, 138), (6.50, 545, 145),
                      (6.63, 515, 152), (6.77, 478, 163), (6.90, 430, 173), (7.03, 369, 187), (7.17, 293, 205),
                      (7.30, 205, 230), (7.40, 126, 252), (7.50, 56, 273), (7.53, 42, 279)]},
}
# CAM 5: a notificação do celular ("Empréstimo da Vivo") entra em 5,07 s no topo do quadro girado.
# Última linha da caixa (px) ao longo do tempo, medida quadro a quadro; tudo acima dela fica borrado e escuro.
NOTIF = [(5.00, 0), (5.07, 92), (5.13, 122), (5.20, 138), (5.33, 138), (5.45, 131), (5.60, 122), (5.80, 116),
         (6.00, 113), (6.50, 110), (7.00, 105), (7.30, 104), (7.80, 105), (8.00, 107)]
RAMP = 0.30          # a troca de velocidade (s na linha do tempo), suave
# a janela nunca sai da imagem. Câmera 03: tudo menos a 1ª linha (preta). CAM 5: só a imagem do monitor; o celular
# treme e a borda física do monitor entra pela esquerda e por baixo. MONITOR = (s, 1ª coluna, última linha) de
# imagem, medidas quadro a quadro pelo perfil de brilho (o pior caso em ±0,1 s); a janela fica 3 px para dentro.
CONTEUDO_C3 = (0, 2, 368, 416)
MONITOR = [(5.2, 0, 436), (5.3, 0, 437), (5.4, 0, 437), (5.5, 0, 435), (5.6, 0, 433), (5.7, 0, 432), (5.8, 0, 431),
           (5.9, 0, 430), (6.0, 1, 430), (6.1, 2, 430), (6.2, 2, 429), (6.3, 2, 429), (6.4, 5, 427), (6.5, 10, 426),
           (6.6, 18, 425), (6.7, 23, 424), (6.8, 25, 423), (6.9, 31, 421), (7.0, 34, 418), (7.1, 34, 418),
           (7.2, 34, 418), (7.3, 32, 418), (7.4, 31, 419), (7.5, 31, 418), (7.6, 32, 418), (7.7, 34, 418),
           (7.8, 35, 418), (7.9, 36, 418), (8.0, 36, 418)]


def monitor(s):
    """Limites da imagem do monitor na CAM 5 no instante s: (x0, x1, y1), já 3 px para dentro."""
    ts = [m[0] for m in MONITOR]
    return (float(np.interp(s, ts, [m[1] for m in MONITOR])) + 3, 850 - 3,
            float(np.interp(s, ts, [m[2] for m in MONITOR])) - 3)


def cam_plan(c):
    """Velocidades por trecho: [(s, v)], os instantes τ (desde o início do plano) de cada troca e a duração."""
    ks = [(c["ss"], 1.0)] + c["lenta"]
    taus, tau = [], 0.0
    for i, (s, v) in enumerate(ks):
        taus.append(tau)
        tau += ((ks[i + 1][0] if i + 1 < len(ks) else c["se"]) - s) / v
    return ks, taus, tau


def cam_time(c, tau):
    """Instante do clipe no instante τ do plano. As trocas de velocidade são suaves (smoothstep de RAMP s,
    centrado na troca): fora das rampas o tempo é o mesmo da troca seca."""
    ks, taus, dur = cam_plan(c)
    tau = min(max(tau, 0.0), dur)
    i = max(j for j in range(len(taus)) if taus[j] <= tau + 1e-9)
    s = ks[i][0] + (tau - taus[i]) * ks[i][1]
    for j in range(1, len(ks)):
        u = (tau - taus[j] + RAMP / 2) / RAMP
        if 0 < u < 1:
            s += (ks[j][1] - ks[j - 1][1]) * (RAMP * (u ** 3 - u ** 4 / 2) - max(0.0, tau - taus[j]))
    return min(s, c["se"])


def cam_tau(c, s):
    """O inverso de cam_time (por busca), para sincronizar: em que τ do plano o clipe chega em s."""
    lo, hi = 0.0, cam_plan(c)[2]
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cam_time(c, mid) < s else (lo, mid)
    return lo


def local_final(i, t):
    """Instante final (na linha do tempo do Reel) do instante local t do arquivo da parte i."""
    f, a, _ = PARTS[i]
    return P0[i] + t - a - _removed(f, t) + _removed(f, a)


def _timeline():
    """Início de cada parte. O P5 é posicionado pela travessia na CAM 5 (ver VISL_SYNC)."""
    global P0
    t, P0 = LEAD, []
    for i in range(len(PARTS)):
        if i == 5:
            t18 = t_cam3() + cam_plan(CAMS["c3"])[2]
            meio = t18 + cam_tau(CAMS["c5"], 6.75)                        # ela no meio da rua
            t = meio + VISL_SYNC - (TRECHOS[5][-1][1] - PARTS[5][1])      # "dela." termina aí
        P0.append(round(t, 3))
        t += _dur(i) + ((GAPS[i] or 0) if i < len(GAPS) else 0)
    return P0


def t_cam3():
    """A Câmera 03 começa a rodar em "Finalmente" (início do 2º trecho do P4)."""
    return local_final(4, TRECHOS[4][1][0]) - 0.05


P0 = []
P0 = _timeline()                                             # início de cada parte
P1 = [round(s + _dur(i), 3) for i, s in enumerate(P0)]       # fim de cada parte
GAPS[4] = round(P0[5] - P1[4], 3)
T17 = round(t_cam3(), 3)                                     # Câmera 03
T18 = round(T17 + cam_plan(CAMS["c3"])[2], 3)               # CAM 5
T_MAPA = round(T18 + cam_plan(CAMS["c5"])[2], 3)            # o mapa
T_FACH = round(local_final(6, TRECHOS[6][1][0]) - 0.05, 3)  # as fachadas, em "pelas câmeras"
T_FECHO = round(T_FACH + 3 * FACHADA, 3)
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
    """videos/ep2/palavras-brutas.json (medium) e palavras-large.json (large-v3), tempos de cada arquivo →
    editor/words-04.json na linha do tempo final. A grafia vem de TEXTO. Em cada trecho de voz (TRECHOS), a
    primeira palavra começa no início do trecho e a última termina no fim; as fronteiras de dentro são a
    média dos dois modelos, esticadas linearmente para caber no trecho."""
    raw = [json.loads((WORK / n).read_text(encoding="utf-8")) for n in ("palavras-brutas.json", "palavras-large.json")
           if (WORK / n).exists()]
    loc = {}
    for f, txt in TEXTO.items():
        toks = txt.split()
        runs = [r[str(f)] for r in raw]
        assert all(len(r) == len(toks) == sum(c for *_, c in TRECHOS[f]) for r in runs), f"contagem no arquivo {f}"
        out, i = [], 0
        for a, b, cnt in TRECHOS[f]:
            # fronteiras internas (média dos modelos) e o começo/fim do trecho segundo eles
            inner = [np.mean([(r[i + k]["e"] + r[i + k + 1]["s"]) / 2 for r in runs]) for k in range(cnt - 1)]
            m0 = max(a, np.mean([r[i]["s"] for r in runs]))       # o whisper põe a 1ª palavra do arquivo em 0
            m1 = np.mean([r[i + cnt - 1]["e"] for r in runs])
            if cnt > 1 and m1 - m0 > 0.05:
                inner = [a + (x - m0) * (b - a) / (m1 - m0) for x in inner]
            bounds = [a] + inner + [b]
            for k in range(1, cnt):                                # pelo menos 60 ms por palavra, em ordem
                bounds[k] = min(max(bounds[k], bounds[k - 1] + 0.06), b - 0.06 * (cnt - k))
            out += [{"w": toks[i + k], "s": round(bounds[k], 3), "e": round(bounds[k + 1], 3)} for k in range(cnt)]
            i += cnt
        loc[str(f)] = out
    (WORK / "palavras-locais.json").write_text(json.dumps(loc, ensure_ascii=False, indent=1), encoding="utf-8")
    out = []
    for i, (f, a, b) in enumerate(PARTS):
        for w in loc[str(f)]:
            if a <= (w["s"] + w["e"]) / 2 < b:                     # o P1 vem do mesmo arquivo, em duas partes
                s, e = max(w["s"], a), min(w["e"], b)
                out.append({"w": w["w"], "s": round(local_final(i, s), 3), "e": round(local_final(i, e), 3)})
    WORDS.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(WORDS, len(out), "palavras")


# ---------------------------------------------------------------- mídia
# fotos: chave → (arquivo, recorte em pixels ou None, caixas a borrar em pixels do original)
PHOTOS = {
    "p06": (D3 / "zoeerrada1", None, []),                                  # parecida de roupa
    "p07": (D3 / "zoeerrada15", (0, 209, 736, 1497), [(388, 136, 472, 188)]),  # post: só a foto; "Elisa" borrado
    "p09": (D3 / "zoeerrada3", None, [(298, 225, 380, 288)]),              # o número da casa (91A) borrado
    "p05": (D3 / "zoeerrada", None, []),                                   # à noite
    "p11": (D3 / "IMG-20260923-WA0046.jpg", None, []),                     # no portão
    "p08": (D3 / "zoeerrada2", None, []),                                  # pela janela do carro
    "ceu": (D3 / "IMG-20260922-WA0187.jpg", None, []),                     # terça: céu aberto
}
# prints em cartão: chave → (arquivo, recorte, caixas a borrar (px do original), largura na tela, centro, rotação)
CARDS = {
    "planalto": (DIV / "Screenshot_20260928_152949_Instagram.jpg", (0, 225, 1080, 1965),   # do @ até a data
                 [(285, 1515, 805, 1700)], 720, (520, 880), -1.0),                        # os dois telefones
    # os golpes: menores, para a foto do cachorro (e a etiqueta) ficar acima das legendas
    "golpe1": (D3 / "golpe1", (0, 80, 739, 1440), [(118, 84, 530, 178)], 600, (520, 840), 1.2),   # foto e número
    "golpe2": (D3 / "golpe 2", (0, 80, 739, 1440), [(118, 84, 500, 178)], 600, (520, 840), -1.2),
    "sv19": (D3 / "IMG-20260922-WA0258.jpg", (0, 530, 899, 1500), [], 860, (520, 820), 0.8),   # o monitor
    "sv20": (D3 / "IMG-20260922-WA0259.jpg", (0, 210, 739, 1280), [], 780, (520, 860), -1.0),  # sem a data e o endereço
    "sv21": (D3 / "IMG-20260922-WA0260.jpg", (0, 210, 739, 1235), [], 780, (520, 860), 1.0),
    # (no fim do zoom de 4%, nenhum cartão sobe além de y ≈ 265, abaixo do contador)
}
# etiqueta GERADA POR IA: canto de cima à esquerda da foto do cachorro no print (px do original)
IA_TAG = {"golpe1": (38, 510), "golpe2": (38, 1005)}
# vídeos: chave → (arquivo, filtro para 1080x1920)
COVER = f"scale=-2:{H}:flags=lanczos,crop={W}:{H}"
VIDS = {
    "busca": (D3 / "VID-20260920-WA0017.mp4", COVER),       # a busca a pé, dom 20/09 (vertical pela rotação)
    "parecida": (D3 / "VID-20260920-WA0002.mp4", COVER),    # a mais parecida, deitada na rua
    "hoje": (SET / "IMG_8418.MOV", f"scale={W}:{H}:flags=lanczos"),   # a Zoe hoje, close (4K)
}
HOJE_SS = 5.5            # o rosto mais alto no quadro e sem movimento (5,5 a 11 s)


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def blur_boxes(im, boxes):
    """Borra cada caixa de verdade (box blur de 20 px, três passadas, como o boxblur=20:3 do build_03)."""
    for b in boxes:
        reg = im.crop(b)
        for _ in range(3):
            reg = reg.filter(ImageFilter.BoxBlur(20))
        im.paste(reg, b[:2])
    return im


def prep():
    WORK.mkdir(parents=True, exist_ok=True)
    need = ["ep2-a-grande.png", "ep2-a-rota.png", "ep2-a-interrogacao-1.png", "ep2-a-interrogacao-2.png",
            "ep2-credito.png", "ep2-camadas.json"]
    if not all((MAPS / n).exists() for n in need):
        import mapa   # noqa: E402  (Chrome headless)
        mapa.ep2_camadas(MAPS)
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


def ease_arr(u):
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def solid(rgb):
    return cached(("solid", rgb), lambda: Image.new("RGB", (W, H), rgb))


def font(size, bold=False):
    return cached(("pil", size, bold), lambda: ImageFont.truetype(
        str(FONTS / ("Poppins-Bold.ttf" if bold else "Poppins-ExtraBold.ttf")), size))


def photo(key):
    def load():
        path, crop, boxes = PHOTOS[key]
        im = blur_boxes(Image.open(path).convert("RGB"), boxes)
        if crop:
            im = im.crop(crop)
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


def on_screen(cx, cy, s, rot, dx, dy):
    """Onde cai na tela um ponto a (dx, dy) do centro de uma camada colocada por place()."""
    th = math.radians(rot)
    return cx + s * (math.cos(th) * dx + math.sin(th) * dy), cy + s * (-math.sin(th) * dx + math.cos(th) * dy)


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


def tag_img(text, size, fg, bg, border=None, pad=(30, 16), r=14):
    """Etiqueta (texto em Poppins ExtraBold numa caixa de cantos arredondados) → RGBA."""
    f = font(size)
    x0, y0, x1, y1 = f.getbbox(text)
    bw = 5 if border else 0
    w, h = x1 - x0 + 2 * pad[0] + 2 * bw, round(size * 0.72) + 2 * pad[1] + 2 * bw
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 4 + w - 1, 4 + h - 1), r, fill=bg, outline=border, width=bw)
    cap = f.getbbox("H")                              # centra pela altura da maiúscula
    d.text((4 + (w - (x1 - x0)) / 2 - x0, 4 + (h - (cap[3] - cap[1])) / 2 - cap[1]), text, font=f, fill=fg)
    return im


def pop(t, t_in, d=0.16, k=0.35):
    """Escala e opacidade de uma entrada com tranco (carimbo)."""
    u = (t - t_in) / d
    if u < 0:
        return 0.0, 0.0
    return (1.0 + k * (1 - ease(u)) if u < 1 else 1.0), min(1.0, u * 2)


# ---------------------------------------------------------------- planos: fotos e vídeos
def f_foto(o, t, t0, t1):
    """Foto com zoom lento: `z` (início, fim) sobre a caixa de cobertura; `f` é o ponto que fica parado.
    `stamp`: carimbo NÃO ERA ELA 0,3 s depois da entrada."""
    u = (t - t0) / (t1 - t0)
    im = photo(o["src"])
    x0, y0, bw, bh = cover_box(*im.size, *o.get("c", (0.5, 0.5)))
    z = lerp(*o.get("z", (1.0, 1.06)), u)
    fx, fy = o.get("f", (0.5, 0.5))
    w2, h2 = bw / z, bh / z
    X, Y = x0 + (bw - w2) * fx, y0 + (bh - h2) * fy
    fr = im.resize((W, H), Image.BICUBIC, box=(X, Y, X + w2, Y + h2), reducing_gap=2.0)
    return stamp(fr, t, t0) if o.get("stamp") else fr


STAMP_POS, STAMP_ROT = (500, 1372), 4.0     # abaixo das legendas (y=1180), longe dos 130 px da direita


def stamp(fr, t, t0):
    """O carimbo NÃO ERA ELA (ink com borda e texto rosa), entrando com um tranco 0,3 s depois do plano."""
    s, a = pop(t, t0 + 0.3)
    if a <= 0:
        return fr
    lay = cached("stamp", lambda: tag_img("NÃO ERA ELA", 54, PINK, INK + (240,), border=PINK, pad=(32, 18)))
    out = fr.convert("RGBA")
    out.alpha_composite(fade_alpha(place(lay, *STAMP_POS, s, STAMP_ROT), a))
    return out.convert("RGB")


def f_ink(o, t, t0, t1):
    return solid(INK)


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


def f_video(o, t, t0, t1):
    """Vídeo em tela cheia a partir de `ss`. `z`: zoom lento (início, fim) em torno de `f`; `grad`: degradê
    do gancho; `fade`: entra saindo do preto; `stamp`: carimbo NÃO ERA ELA."""
    if "_rd" not in o:
        path, vf = VIDS[o["vid"]]
        o["_rd"] = Reader(path, o["ss"] + o.get("_off", 0), t1 - t0, W, H, vf)
    fr = o["_rd"].read()
    if "z" in o:
        z = lerp(*o["z"], (t - t0) / (t1 - t0))
        fx, fy = o.get("f", (0.5, 0.5))
        w2, h2 = W / z, H / z
        X, Y = (W - w2) * fx, (H - h2) * fy
        fr = fr.resize((W, H), Image.BICUBIC, box=(X, Y, X + w2, Y + h2))
    if o.get("grad"):
        fr = grad_top(fr)
    if "fade" in o:
        fr = darken(fr, ease((t - t0) / o["fade"]))
    return stamp(fr, t, t0) if o.get("stamp") else fr


# ---------------------------------------------------------------- planos: prints em cartão
CARD_Z = (1.0, 1.04)  # zoom lento e contínuo em cada print
XF = 0.3              # crossfade entre um print e o próximo


def card_layer(key):
    def make():
        path, crop, boxes, dw, _, _ = CARDS[key]
        im = blur_boxes(Image.open(path).convert("RGB"), boxes)
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


def card_frame(key, z, t=None, t0=None):
    """O print inteiro, em cartão (com sombra) sobre ink, na escala z. Nos golpes, a etiqueta GERADA POR IA
    presa no canto da foto do cachorro (acompanha o zoom e a rotação do cartão)."""
    path, crop, _, dw, (cx, cy), rot = CARDS[key]
    fr = solid(INK).convert("RGBA")
    lay = card_layer(key)
    fr.alpha_composite(place(lay, cx, cy, z, rot))
    if key in IA_TAG and t is not None:
        s, a = pop(t, t0 + 0.35)
        if a > 0:
            tag = cached("iatag", lambda: tag_img("GERADA POR IA", 38, INK, LILAC + (255,), pad=(22, 13), r=10))
            k = dw / (crop[2] - crop[0])
            px, py = IA_TAG[key]
            # canto de cima à esquerda da etiqueta a 24 px (do original) da quina da foto; 110 = margem da camada
            lx = 110 + (px + 24 - crop[0]) * k + tag.width / 2
            ly = 110 + (py + 24 - crop[1]) * k + tag.height / 2
            X, Y = on_screen(cx, cy, z, rot, lx - lay.width / 2, ly - lay.height / 2)
            fr.alpha_composite(fade_alpha(place(tag, X, Y, z * s, rot - 2.5), a))
    return fr.convert("RGB")


def f_cartao(o, t, t0, t1):
    """Um print por vez, com um zoom lento e contínuo (CARD_Z). `xf` = (cartão, início, fim) do plano
    anterior, que sai num crossfade de XF s continuando o próprio zoom."""
    fr = card_frame(o["card"], lerp(*CARD_Z, (t - t0) / (t1 - t0)), t, t0)
    if "xf" in o and t - t0 < XF:
        key, p0, p1 = o["xf"]
        fr = Image.blend(card_frame(key, lerp(*CARD_Z, (t - p0) / (p1 - p0)), t, p0), fr, ease((t - t0) / XF))
    return fr


# ---------------------------------------------------------------- planos: câmeras de segurança
def cam_frames(key):
    """Todos os quadros do trecho `load` do clipe na memória (uint8), com os instantes reais (pts)."""
    def load():
        c = CAMS[key]
        w, h = c["size"]
        pts = np.array([float(x) for x in subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "frame=pts_time", "-of", "csv=p=0",
             str(c["src"])], capture_output=True, text=True, check=True).stdout.split()])
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(c["src"]), "-vf", c["vf"], "-fps_mode", "passthrough",
                              "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        keep, ts = [], []
        for t in pts:
            buf = p.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            if c["load"][0] - 0.2 <= t <= c["load"][1] + 0.2:
                keep.append(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
                ts.append(t)
        p.stdout.read()
        p.wait()
        return np.stack(keep), np.array(ts)
    return cached(("camfr", key), load)


def notif_bottom(s):
    return float(np.interp(s, [a for a, _ in NOTIF], [b for _, b in NOTIF]))


def cam_image(key, s):
    """O quadro no instante s do clipe: mistura dos dois quadros vizinhos (câmera lenta sem tranco). Na CAM 5,
    tudo acima da notificação (e a própria) sai borrado e escuro."""
    frs, ts = cam_frames(key)
    i = int(np.clip(np.searchsorted(ts, s, side="right") - 1, 0, len(ts) - 2))
    a = float(np.clip((s - ts[i]) / (ts[i + 1] - ts[i]), 0, 1))
    img = frs[i].astype(np.float32) * (1 - a) + frs[i + 1].astype(np.float32) * a
    if key == "c5":
        yb = notif_bottom(s)
        if yb > 0:
            top = int(min(yb + 30, img.shape[0]))
            band = Image.fromarray(img[:top].astype(np.uint8)).filter(ImageFilter.GaussianBlur(14))
            band = np.asarray(band, np.float32) * 0.22
            y = np.arange(top, dtype=np.float32)[:, None, None]
            m = np.clip((yb + 10 - y) / 6, 0, 1)            # sólido até 4 px abaixo da caixa, some em 6 px
            img[:top] = img[:top] * (1 - m) + band * m
    return Image.fromarray(img.astype(np.uint8))


def cam_track(key):
    """A trilha da Zoe suavizada: (instantes, x, y) numa grade fina (Câmera 03: polinômio de grau 3, porque
    a medição pula nas grades do portão; CAM 5: média móvel curta)."""
    def make():
        tr = np.array(CAMS[key]["trilha"], float)
        ts = np.linspace(tr[0, 0], tr[-1, 0], 200)
        if key == "c3":
            xs = np.polyval(np.polyfit(tr[:, 0], tr[:, 1], 3), ts)
            ys = np.polyval(np.polyfit(tr[:, 0], tr[:, 2], 3), ts)
        else:
            k = np.ones(3) / 3
            xs = np.interp(ts, tr[:, 0], np.convolve(np.pad(tr[:, 1], 1, mode="edge"), k, "valid"))
            ys = np.interp(ts, tr[:, 0], np.convolve(np.pad(tr[:, 2], 1, mode="edge"), k, "valid"))
        return ts, xs, ys
    return cached(("track", key), make)


def her(key, s):
    ts, xs, ys = cam_track(key)
    return float(np.interp(s, ts, xs)), float(np.interp(s, ts, ys))


def cam_window(key, s):
    """Janela (x0, y0, x1, y1) do quadro original mostrada no cartão. Câmera 03: começa no quadro inteiro e
    fecha devagar (zoom 2x) acompanhando a Zoe. CAM 5: janela 3:2 um pouco fechada, que acompanha a
    travessia e fica abaixo da notificação."""
    def path(zoom=True, cap=None, ref=False):
        c = CAMS[key]
        iw, ih = c["size"]
        vw, vh = c["vista"][:2]
        tr = c["trilha"]
        grid = np.arange(c["ss"] - 0.1, c["se"] + 0.1, 1 / 120)
        out = []
        for gi, g in enumerate(grid):
            hx, hy = her(key, min(max(g, tr[0][0]), tr[-1][0]))
            if key == "c3":
                qx0, qy0, qx1, qy1 = CONTEUDO_C3
                z0, z1, zm = c["zoom"]
                u = ease((g - z0) / (z1 - z0))
                z = 1 + (zm - 1) * u
                wh = min(qy1 - qy0, (qx1 - qx0) * vh / vw) / z        # a maior janela do cartão dentro da imagem
                ww = wh * vw / vh
                cx, cy = lerp((qx0 + qx1) / 2, hx, u), lerp((qy0 + qy1) / 2, hy, u)
                top, bot, lo, hi = qy0, qy1, qx0 + ww / 2, qx1 - ww / 2
            else:
                # zoom lento (1,0 → 1,3) durante a câmera lenta, acompanhando a travessia
                u = ease((g - c["lenta"][0][0]) / (c["lenta"][1][0] - c["lenta"][0][0]))
                zl = 1 + (c["zoom"][1] - 1) * u if zoom else 1.0
                wh = lerp(312, 290, ease((g - c["ss"]) / (c["se"] - c["ss"]))) / zl   # cabe entre a faixa e a borda
                # até 50 px (sem zoom) da faixa escura à vista; com o zoom, a faixa fica presa (cap, em px da
                # tela) ao que o caminho de antes mostrava em cada instante
                yb = notif_bottom(g) + 10
                a_ = 0.0 if cap is None else cap[gi] * 1.5 / vw        # faixa permitida = a_ · wh (px do quadro)
                if ref:                                                # o caminho de antes (só para a faixa)
                    mx0, mx1, bot = 8, iw - 8, 440
                else:
                    mx0, mx1, bot = monitor(g)
                    if cap is not None:                                # sem espaço entre a faixa e a borda de baixo:
                        wh = min(wh, bot - 70, (bot - yb) / (1 - a_))  # fecha um pouco mais (a faixa não cresce)
                top = max(70, yb - (50 if cap is None else a_ * wh))
                ww = 1.5 * wh
                lo, hi = mx0 + ww / 2, mx1 - ww / 2
                cx = hx
                cy = hy + (0.1 * wh if ref else 0.0)                   # ela no centro
            cx = min(max(cx, lo), hi)
            cy = min(max(cy, top + wh / 2), bot - wh / 2)
            out.append((cx, cy, ww, wh, top, bot, lo, hi))
        arr = np.array(out)
        # suaviza o caminho (gaussiana de 0,12 s do clipe, simétrica: sem atraso) e prende de novo
        sig = 0.12 * 120
        hw = int(3 * sig)
        k = np.exp(-0.5 * (np.arange(-hw, hw + 1) / sig) ** 2)
        k /= k.sum()
        for j in (0, 1):
            arr[:, j] = np.convolve(np.pad(arr[:, j], len(k) // 2, mode="edge"), k, "valid")
        # (a suavização não pode levar a janela para fora da imagem nem para cima da faixa permitida)
        arr[:, 0] = np.minimum(np.maximum(arr[:, 0], arr[:, 6]), arr[:, 7])
        arr[:, 1] = np.minimum(np.maximum(arr[:, 1], arr[:, 4] + arr[:, 3] / 2), arr[:, 5] - arr[:, 3] / 2)
        if key == "c5" and zoom and cap is None:
            # a faixa do caminho de antes (sem zoom, sem folga), em px da tela: com o zoom, nunca mais que ela
            g0, a0 = path(zoom=False, ref=True)
            yb = np.array([notif_bottom(g) for g in g0]) + 10
            cap = np.maximum(0, yb - (a0[:, 1] - a0[:, 3] / 2)) * vw / a0[:, 2]
            return path(zoom=True, cap=cap)
        return grid, arr
    grid, arr = cached(("win", key), path)
    cx, cy, ww, wh = (float(np.interp(s, grid, arr[:, j])) for j in range(4))
    return cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2


def cam_base(key):
    """Fundo ink com a sombra do cartão e a máscara de cantos arredondados."""
    def make():
        vw, vh, vx, vy = CAMS[key]["vista"]
        x0, y0 = vx - vw / 2, vy - vh / 2
        base = solid(INK).convert("RGBA")
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 30, x0 + vw, y0 + vh + 30), 26, fill=170)
        base.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 0)] * 3, sh.filter(ImageFilter.GaussianBlur(40)))))
        mask = Image.new("L", (vw, vh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, vw - 1, vh - 1), 26, fill=255)
        return base.convert("RGB"), mask, (round(x0), round(y0))
    return cached(("cambase", key), make)


def ring_img(r):
    """Círculo lilás com brilho, raio r (px da tela)."""
    def make():
        ss, size = 3, int(2 * r + 60)
        m = Image.new("L", (size * ss, size * ss), 0)
        c = size * ss / 2
        ImageDraw.Draw(m).ellipse((c - r * ss, c - r * ss, c + r * ss, c + r * ss), outline=255, width=7 * ss)
        m = m.resize((size, size), Image.LANCZOS)
        glow = m.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.8))
        a = Image.fromarray(np.maximum(np.asarray(m), np.asarray(glow)))
        lay = Image.new("RGBA", (size, size), LILAC + (0,))
        lay.putalpha(a)
        return lay
    return cached(("ring", r), make)


def f_cam(o, t, t0, t1):
    """Câmera de segurança em cartão: velocidade (cam_time), janela (cam_window) e o círculo na Zoe."""
    key = o["cam"]
    c = CAMS[key]
    s = cam_time(c, t - t0)
    x0, y0, x1, y1 = cam_window(key, s)
    vw, vh, _, _ = c["vista"]
    base, mask, (bx, by) = cam_base(key)
    view = cam_image(key, s).resize((vw, vh), Image.BICUBIC, box=(x0, y0, x1, y1))
    fr = base.copy()
    fr.paste(view, (bx, by), mask)
    tr = c["trilha"]
    a = ease((s - tr[0][0]) / 0.12) * (1 - ease((s - tr[-1][0] + 0.05) / 0.2))
    if a > 0:
        hx, hy = her(key, min(max(s, tr[0][0]), tr[-1][0]))
        X, Y = bx + (hx - x0) * vw / (x1 - x0), by + (hy - y0) * vh / (y1 - y0)
        # o círculo fica dentro do cartão (quando ela sai pela borda, ele sai junto)
        ring = ring_img(c["anel"])
        lay = Image.new("RGBA", (W, H))
        lay.alpha_composite(fade_alpha(ring, a), (round(X - ring.width / 2), round(Y - ring.height / 2)))
        clip = Image.new("L", (W, H), 0)
        clip.paste(mask, (bx, by))
        lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel("A")), np.asarray(clip))))
        fr = fr.convert("RGBA")
        fr.alpha_composite(lay)
        fr = fr.convert("RGB")
    return fr


# ---------------------------------------------------------------- planos: o mapa
# Vista A do Ep. 1 (mesmo centro e âncora), com a rota inteira até mapa.FIM_EP2 numa camada só.
def mj():
    return cached("mapjson", lambda: json.loads((MAPS / "ep2-camadas.json").read_text(encoding="utf-8")))


def map_img(name, mode="RGB"):
    return cached(("map", name), lambda: Image.open(MAPS / name).convert(mode))


def m_grande(k):
    """Vista "grande" (3x a área) com zoom-out k ≥ 1 em torno da âncora."""
    k = min(max(k, 1.0), 3.0)
    (gx, gy), (ax, ay) = mj()["grande_anchor"], mj()["anchor"]
    return map_img("ep2-a-grande.png").resize(
        (W, H), Image.BICUBIC, box=(gx - ax * k, gy - ay * k, gx + (W - ax) * k, gy + (H - ay) * k),
        reducing_gap=2.0)


def scaled_layer(layer, f):
    """Camada 1x (WxH) reduzida por f em torno da âncora do mapa."""
    if abs(f - 1) < 1e-4:
        return layer
    ax, ay = mj()["anchor"]
    return layer.transform((W, H), Image.AFFINE, (1 / f, 0, ax - ax / f, 0, 1 / f, ay - ay / f),
                           resample=Image.BICUBIC)


def route_arc():
    """Comprimento (px, vista A) da rota até cada vértice: [0, ..., total]."""
    def make():
        pts = mj()["rota"]
        acc = [0.0]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            acc.append(acc[-1] + math.hypot(x2 - x1, y2 - y1))
        return acc
    return cached("arc", make)


def route_point(d):
    """Ponto da rota a d px do começo."""
    pts, acc = mj()["rota"], route_arc()
    d = min(max(d, 0), acc[-1])
    i = max(j for j in range(len(acc) - 1) if acc[j] <= d)
    u = (d - acc[i]) / (acc[i + 1] - acc[i])
    return lerp(pts[i][0], pts[i + 1][0], u), lerp(pts[i][1], pts[i + 1][1], u)


def route_reveal(lim):
    """A rota revelada até `lim` px do começo, com a ponta cortada na perpendicular (borda macia) e um ponto
    rosa na ponta (como o fim da linha no Ep. 1). Cada pixel recebe a posição, ao longo da rota, do trecho
    mais próximo."""
    def prep_route():
        lay = map_img("ep2-a-rota.png", "RGBA")
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
        return box, arr, arc
    box, arr, arc = cached("route", prep_route)
    a = arr[..., 3] * np.clip((lim - arc) / 8 + 0.5, 0, 1)
    out = arr.copy()
    out[..., 3] = a.astype(np.uint8)
    full = Image.new("RGBA", (W, H))
    full.alpha_composite(Image.fromarray(out), box[:2])
    L = route_arc()[-1]
    if lim < L + 8:                                   # a ponta: o mesmo ponto rosa do fim da rota (r ≈ 10,5)
        x, y = route_point(lim - 4)
        ss, r = 4, 10.5
        m = Image.new("L", (40 * ss, 40 * ss), 0)
        ImageDraw.Draw(m).ellipse((20 * ss - r * ss, 20 * ss - r * ss, 20 * ss + r * ss, 20 * ss + r * ss), fill=255)
        dot = Image.new("RGBA", (40, 40), PINK + (0,))
        dot.putalpha(m.resize((40, 40), Image.LANCZOS))
        full.alpha_composite(dot, (round(x - 20), round(y - 20)))
    return full


def question(fr, t, which, t_in, f=1.0, a=1.0, s_extra=1.0):
    """O "?" (1: no fim do Ep. 1; 2: no fim novo), entrando com um tranco em t_in."""
    if t < t_in or a <= 0:
        return
    def prep_q():
        lay = map_img(f"ep2-a-interrogacao-{which}.png", "RGBA")
        box = lay.getchannel("A").getbbox()
        return lay.crop(box), box
    q, box = cached(("q", which), prep_q)
    u = (t - t_in) / 0.35
    pop_ = 1.0 if u >= 1 else 0.6 + 0.4 * ease(u) + 0.12 * math.sin(math.pi * min(u, 1))
    s = pop_ * f * s_extra
    ax, ay = mj()["anchor"]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    cx, cy = ax + (cx - ax) * f, ay + (cy - ay) * f
    qq = q.resize((max(1, round(q.width * s)), max(1, round(q.height * s))), Image.BICUBIC)
    fr.alpha_composite(fade_alpha(qq, a * min(1, (t - t_in) / 0.12)),
                       (round(cx - qq.width / 2), round(cy - qq.height / 2)))


def credit(fr):
    fr.alpha_composite(map_img("ep2-credito.png", "RGBA"))
    return fr.convert("RGB")


def f_mapa(o, t, t0, t1):
    """P6: o mapa do Ep. 1 já desenhado até a Fagundes dos Reis, com o "?". O "?" some, a linha avança
    pela Lava Pés até a Capitão Eleutério e o "?" novo entra no fim. O mapa abre devagar (5%)."""
    k = 1 + 0.05 * ease((t - t0) / (t1 - t0))
    fr = m_grande(k).convert("RGBA")
    L = route_arc()[-1]
    d0 = mj()["frac_fim_ep1"] * L
    l0, l1 = o["linha"]
    lim = lerp(d0 + 4, L + 50, ease((t - l0) / (l1 - l0)))
    fr.alpha_composite(scaled_layer(route_reveal(lim), 1 / k))
    q1 = o["q1"]
    question(fr, t, 1, -1, f=1 / k, a=1 - ease((t - q1) / 0.3), s_extra=1 - 0.3 * ease((t - q1) / 0.3))
    question(fr, t, 2, o["q2"], f=1 / k)
    return credit(fr)


def f_hoje(o, t, t0, t1):
    """Fecho: a Zoe hoje, em close. Entra saindo do preto."""
    if "_rd" not in o:
        path, vf = VIDS["hoje"]
        o["_rd"] = Reader(path, HOJE_SS + o.get("_off", 0), t1 - t0, W, H, vf)
    return darken(o["_rd"].read(), ease((t - t0) / o.get("fade", 0.8)))


# ---------------------------------------------------------------- a montagem (SHOTS)
def shots():
    """(início, função, opções): cada plano vai até o início do próximo. Os tempos vêm das palavras."""
    varias = cue("com várias") - 0.05
    zoes = cue("Zoes geradas") - 0.05
    m = T_MAPA
    sus = [                                                        # as parecidas: uma por vez, a mais parecida por último
        (P0[2], {"src": "p06", "f": (0.59, 0.37)}),                 # "A partir daí, começamos a"
        (cue("receber") - 0.05, {"src": "p07", "f": (0.62, 0.55)}),  # "receber muitas mensagens e"
        (cue("fotos de") - 0.05, {"src": "p09", "f": (0.72, 0.48)}),  # "fotos de cachorros parecidos,"
        (cue("de gente") - 0.05, {"src": "p05", "f": (0.45, 0.5)}),  # "de gente que achava que era ela."
        (cue("Tomamos") - 0.05, {"src": "p11", "f": (0.35, 0.45)}),  # "Tomamos vários sustos,"
        (cue("e nessa") - 0.05, {"src": "p08", "f": (0.58, 0.40)}),  # "e nessa altura até a gente"
    ]
    return [
        # gancho (P1a) — "No domingo, a gente voltou para Passo Fundo." — a busca a pé, com o título
        (0.0, f_video, {"vid": "busca", "ss": 0.0, "grad": True}),
        # cartela DIA 3 · DOM 20/09 (a pausa aberta no meio do P1)
        (P1[0], f_ink, {}),
        # a rua (P1b) — "E foi praticamente o dia todo na rua," — o vídeo continua de onde parou
        (P0[1], f_video, {"vid": "busca", "ss": P1[0]}),
        # "com várias pessoas, a pé e em cinco carros. Mas nada concreto." — a Rádio Planalto, 20/09
        (varias, f_cartao, {"card": "planalto"}),
        # cartela DIA 4 · SEG 21/09
        (P1[1], f_ink, {}),
        # os sustos (P2)
        *[(t, f_foto, dict(o, stamp=True)) for t, o in sus],
        # "estava duvidando se era ela ou não." — a mais parecida (vídeo, olhando para a câmera)
        (cue("estava duvidando") - 0.05, f_video, {"vid": "parecida", "ss": 0.25, "z": (1.0, 1.05),
                                                   "f": (0.4, 0.3), "stamp": True}),
        # o golpe (P3) — "E o golpe estava liberado, porque tivemos várias tentativas,"
        (P0[3], f_cartao, {"card": "golpe1"}),
        # "Zoes geradas por IA e gente falando que ia ficar com ela."
        (zoes, f_cartao, {"card": "golpe2", "xf": ("golpe1", P0[3], zoes)}),
        # cartela DIA 5 · TER 22/09
        (P1[3], f_ink, {}),
        # a terça (P4) — "Mas foi na terça que a gente começou a ver uma luz no final do túnel."
        (P0[4], f_foto, {"src": "ceu", "z": (1.0, 1.08), "f": (0.5, 0.2)}),
        # "Finalmente, ..." — a Câmera 03 roda do início; ela passa em câmera lenta no vislumbre (sem voz)
        (T17, f_cam, {"cam": "c3"}),
        # até então (P5) — a CAM 5, com a travessia em câmera lenta
        (T18, f_cam, {"cam": "c5"}),
        # o percurso (P6) — o mapa: a linha avança uma rua
        (m, f_mapa, {"q1": m + 0.30, "linha": (m + 0.55, m + 2.05), "q2": m + 2.10}),
        # "pelas câmeras." e a música: as fachadas com a câmera circulada, uma por vez
        (T_FACH, f_cartao, {"card": "sv19"}),
        (T_FACH + FACHADA, f_cartao, {"card": "sv20", "xf": ("sv19", T_FACH, T_FACH + FACHADA)}),
        (T_FACH + 2 * FACHADA, f_cartao, {"card": "sv21", "xf": ("sv20", T_FACH + FACHADA, T_FACH + 2 * FACHADA)}),
        # fecho: a Zoe hoje, em close
        (T_FECHO, f_hoje, {"fade": 0.8}),
    ]


# ---------------------------------------------------------------- texto (ASS)
LIBASS_EM = 0.558      # no libass, o "em" da Poppins é ~0,558 x Fontsize (medido: a maiúscula tem ~0,41)
CAP_Y, CAP_MAXW = 1180, 800        # legendas: centro em x=540, sem entrar nos 130 px da direita
YEL, WHT = r"{\c&H00D7FF&}", r"{\c&HFFFFFF&}"
# contador: 6 segmentos no topo, abaixo da interface do Instagram (y ≈ 230)
SEG_X0, SEG_X1, SEG_Y, SEG_H, SEG_GAP = 130, 950, 252, 10, 14
SEG_W = (SEG_X1 - SEG_X0 - 5 * SEG_GAP) / 6


def tw(txt, fs, bold=False, spacing=0):
    """Largura aproximada do texto no libass (Poppins ExtraBold, ou Bold)."""
    return font(200, bold).getlength(txt) * fs * LIBASS_EM / 200 + spacing * len(txt)


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
SOLTAS = {w: 1.2 for w in ("a", "o", "e", "de", "da", "do", "dos", "na", "no", "pra", "para", "com", "um", "uma",
                           "uns", "as", "os", "se", "em", "por", "pelas", "às")}
SOLTAS.update({w: 0.4 for w in ("que", "eu", "ia", "já", "não", "só", "mas", "quando", "ela", "era", "até")})


def cap_chunks(words):
    """Blocos de até 3 palavras que caibam na largura. Quebra na pontuação e nas pausas da fala e,
    dentro de cada frase, escolhe a divisão com menos blocos, evitando bloco que termina em palavra
    solta e bloco de uma palavra curta."""
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


def FILLS():
    """Quando cada segmento do contador enche: nas cartelas DIA 3, DIA 4 e DIA 5."""
    return [P1[0] + 0.15, P1[1] + 0.20, P1[3] + 0.20]


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

    # --- legendas: toda a fala; nenhum bloco entra numa cartela (corta no início dela)
    cartelas = [P1[0], P1[1], P1[3]]
    chunks = cap_chunks(_WORDS)
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else DUR
        last_end = nxt if nxt - ch[-1]["e"] < 0.6 else ch[-1]["e"] + 0.35
        last_end = min([last_end] + [c for c in cartelas if c > ch[0]["s"]])
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

    # --- contador de dias: 6 segmentos; os dias 1 e 2 (Ep. 1) já cheios; enche nas cartelas
    def seg(i):
        return SEG_X0 + i * (SEG_W + SEG_GAP)
    for i in range(6):
        add(0, DUR, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(CREAM)}\1a&HBF&\fad(250,0)\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 0)
    for i in range(2):
        add(0, DUR, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(LILAC)}\fad(250,0)\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
    for i, tf in enumerate(FILLS(), start=2):
        x = seg(i)
        clip0 = rf"\clip({x:.0f},{SEG_Y - 20},{x:.0f},{SEG_Y + SEG_H + 20})"
        clip1 = rf"\clip({x:.0f},{SEG_Y - 20},{x + SEG_W:.0f},{SEG_Y + SEG_H + 20})"
        add(tf, DUR, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}{clip0}\t(0,450,{clip1})\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
        add(tf, tf + 1.2, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}\1a&H60&\blur8{clip0}"
            rf"\t(0,450,{clip1})\fad(0,500)\p1}}" + rrect(SEG_W, SEG_H, SEG_H / 2), 1)

    # --- gancho no topo (até o fim da cartela DIA 3, como no Ep. 1)
    pop_ = r"\fad(0,150)\fscx102\fscy102\t(0,160,\fscx100\fscy100)"
    add(0, P0[1], "Hook", rf"{{\pos(540,{327 + 0.0605 * 170:.0f}){pop_}}}OS 6 DIAS DA ZOE", 4)
    add(0, P0[1], "HookSub", rf"{{\pos(540,{403 + 0.0605 * 93:.0f}){pop_}}}PARTE 2", 4)

    # --- cartelas
    for (t0, t1), dia, data in (((P1[0], P0[1]), "DIA 3", "DOM 20/09"),
                                ((P1[1], P0[2]), "DIA 4", "SEG 21/09"),
                                ((P1[3], P0[4]), "DIA 5", "TER 22/09")):
        add(t0 + 0.04, t1, "Dia", r"{\move(540,905,540,880,0,220)\fad(120,90)}" + dia, 2)
        add(t0 + 0.12, t1, "Data", r"{\move(540,1060,540,1040,0,220)\fad(120,90)}" + data, 2)

    # --- etiquetas de horário nas câmeras (a da Câmera 03 entra em "ainda na sexta"; a da CAM 5 fica à
    # esquerda, porque ela entra pelo alto, à direita)
    # (a da Câmera 03 desce 24 px: o cartão começa logo abaixo do contador, e ela não pode encostar nele)
    for t_in, t_out, txt, x, dy, (_, vh, _, vy) in (
            (cue("ainda na sexta"), T18, "SEX 18/09 · 08H43", 780, 28, CAMS["c3"]["vista"]),
            (T18 + 0.15, T_MAPA, "SEX 18/09 · 08H44", 300, 4, CAMS["c5"]["vista"])):
        y = vy - vh / 2 + dy
        add(t_in, t_out, "Chip", rf"{{\pos({x},{y:.0f})\frz3\fad(80,150)\fscx112\fscy112"
            rf"\t(0,120,\fscx100\fscy100)}}" + txt, 4)

    # --- fecho: PARTE 3 · DIA 6 → e o @ (um pouco mais baixo que no Ep. 1, para não cobrir o focinho)
    ft, fs = "PARTE 3 · DIA 6", 84
    txt_w = tw(ft, fs, spacing=1)
    aw, ah, gap, padx, bh = 66, 48, 26, 46, 136
    bw = txt_w + gap + aw + 2 * padx
    yc = 1340
    bx, by = 540 - bw / 2, yc - bh / 2
    t_in = T_FECHO + 0.55
    add(t_in, DUR, "Draw", rf"{{\pos({bx:.1f},{by:.1f})\1c{ass_c(INK)}\1a&H1A&\fad(250,0)\p1}}" + rrect(bw, bh, 22), 5)
    add(t_in, DUR, "Fecho", rf"{{\an4\pos({bx + padx:.1f},{yc + 2})\fad(250,0)}}" + ft, 6)
    add(t_in, DUR, "Draw", rf"{{\pos({bx + padx + txt_w + gap:.1f},{yc - ah / 2:.1f})\1c{ass_c(PINK)}"
        rf"\fad(250,0)\p1}}" + arrow(aw, ah, 13), 6)
    add(t_in + 0.3, DUR, "Handle", rf"{{\pos(540,{by + bh + 58:.0f})\fad(300,0)}}" + HANDLE, 6)

    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


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


def zoe_entra():
    """Quando a Zoe aparece na Câmera 03 (linha do tempo): a virada da trilha."""
    return T17 + cam_tau(CAMS["c3"], CAMS["c3"]["trilha"][0][0])


def music_marks():
    return {
        "t0": 0.10,
        "golpe_in": P0[3] - 0.10,       # quase some no P3
        "golpe_out": P1[3] + 0.05,      # volta na cartela DIA 5
        "lift": T17,                    # "Finalmente": o pad abre
        "open": zoe_entra(),            # a Zoe entra no quadro: parte animada, com o acento
        "fecho": T_FECHO,
        "end": DUR,
        "chimes": FILLS(),              # o contador enchendo
    }


MUSIC_DB = -8.0         # trilha em relação à voz, antes do duck (a voz tira ~6 dB dela)
AMB_DB = 8.0            # ambiente do fecho (o som original é bem baixo)
MUSIC_ACC = ROOT / "audios" / "trilha-04-acento.wav"   # o acento da entrada da Zoe, fora do duck
SEM_VOZ_DB = -19.5      # média (volumedetect) da trilha nos trechos sem voz, no mix final
ACENTO_DB = 7.0         # o acento da entrada da Zoe, acima do nível da trilha (fora do duck)
RAMPA = 0.30            # o ganho sobe ao sair a voz e desce ao entrar a voz nesse tempo
LIMITE = {"mix": 0.80, "mix-sem-musica": 0.84}   # teto do limitador (com trilha: ≤ -1,5 dBFS de true peak)


def sem_voz():
    """Onde a trilha sobe: do fim da voz da P4 até a P5 (o vislumbre) e do fim da voz da P6 até o fim."""
    return (P1[4] - 0.15, P0[5]), P1[6] - 0.15


def janelas():
    """Onde medir (as janelas da revisão): o vislumbre em duas metades (a 1ª com o acento) e as fachadas
    depois da P6, sem as rampas. Cada uma tem o seu ganho."""
    m = round(P1[4] + 1.9, 1)                     # ≈ 44,0 s
    return {"A1": (round(P1[4], 1), m), "A2": (m, round(P0[5] - 0.2, 1)),
            "B": (round(P1[6] + 0.14, 1), round(T_FECHO - 0.06, 1))}


def mean_db(path, spans):
    """Média de cada trecho como no volumedetect: 10·log10 da média do quadrado das amostras."""
    import wave
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768
    x = x.reshape(-1, 2)
    return [10 * math.log10(np.mean(x[int(a * sr):int(b * sr)] ** 2) + 1e-12) for a, b in spans]


def normalize(src, dst, lim):
    """-14 LUFS (ganho linear medido + limitador), com uma segunda passada se o limitador puxar o nível."""
    i, _ = loudness(src)
    g = -14 - i
    for _ in range(3):
        ff(["-i", src, "-af", f"volume={g:.2f}dB,alimiter=limit={lim}:attack=3:release=60:level=disabled",
            "-c:a", "pcm_s16le", dst])
        li, lp = loudness(dst)
        if abs(li + 14) < 0.05 or lim == LIMITE["mix-sem-musica"]:   # a versão sem trilha fica como era
            break
        g += -14 - li
    return li, lp


def build_audio():
    """voz.wav → mixagem com trilha e sem trilha, as duas em -14 LUFS. Na com trilha, a trilha sobe só nos
    trechos sem voz (sem_voz), até a média de SEM_VOZ_DB; sob a voz o duck fica como era."""
    voz, pre, pre_nat = WORK / "voz.wav", WORK / "mix-pre.wav", WORK / "mix-sem-musica-pre.wav"
    ins, fc = [], []
    for k, (f, a, b) in enumerate(PARTS):
        ins += ["-i", VOZ / f"{f}.ogg"]
        d = _dur(k)
        segs = _segments(f, a, b)
        if len(segs) == 1:
            src = f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS"
        else:                             # tira o silêncio de dentro (CUTS), com fades curtos nas emendas
            names = "".join(f"[c{k}_{j}]" for j in range(len(segs)))
            fc.append(f"[{k}:a]asplit={len(segs)}{names}")
            for j, (s0, s1) in enumerate(segs):
                fc.append(f"[c{k}_{j}]atrim=start={s0}:end={s1},asetpts=PTS-STARTPTS,"
                          f"afade=t=in:d=0.01,afade=t=out:st={s1 - s0 - 0.01:.3f}:d=0.01[t{k}_{j}]")
            src = "".join(f"[t{k}_{j}]" for j in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1"
        fi, fo = FADES.get(k, (0.015, 0.040))
        fc.append(f"{src},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"
                  f"afade=t=in:d={fi},afade=t=out:st={d - fo:.3f}:d={fo}[p{k}]")
    gaps = [LEAD] + [P0[k] - P1[k - 1] for k in range(1, len(PARTS))]
    for k, g in enumerate(gaps):
        fc.append(f"aevalsrc=0:s=48000:d={g:.4f},aformat=sample_fmts=fltp:channel_layouts=mono[g{k}]")
    seq = "".join(f"[g{k}][p{k}]" for k in range(len(PARTS)))
    fc.append(f"{seq}concat=n={2 * len(PARTS)}:v=0:a=1,highpass=f=80,afftdn=nf=-25,"
              f"acompressor=threshold=0.1:ratio=2.5:attack=10:release=150,apad=whole_dur={DUR}[v]")
    ff([*ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", DUR, "-c:a", "pcm_s16le", voz])

    trilha_04.render(MUSIC, music_marks(), acc_out=MUSIC_ACC)
    vi, _ = loudness(voz)
    mi, _ = loudness(MUSIC)
    mg = vi + MUSIC_DB - mi
    ms = int(T_FECHO * 1000)
    amb = (f"[2:a]aresample=48000,aformat=channel_layouts=stereo,highpass=f=120,lowpass=f=9000,"
           f"volume={AMB_DB}dB,afade=t=in:d=0.8,afade=t=out:st={FECHO - 1.3:.2f}:d=1.2,adelay={ms}|{ms},"
           f"apad=whole_dur={DUR}[amb]")
    hoje = ["-ss", HOJE_SS, "-t", FECHO, "-i", VIDS["hoje"][0]]
    (a0, a1), b0 = sem_voz()
    win = janelas()
    mix, mix_nat = WORK / "mix.wav", WORK / "mix-sem-musica.wav"

    m = win["A2"][0]

    def com_trilha(g):
        """A voz empurra a trilha para baixo (sidechain); depois do duck, o ganho dos trechos sem voz entra e sai
        em RAMPA s (no vislumbre, g["A1"] passa para g["A2"] em 1 s em volta do meio; depois da P6, g["B"]).
        O acento vem à parte, sem duck, ACENTO_DB acima da trilha."""
        k1, k2, kb = (10 ** (g[n] / 20) - 1 for n in ("A1", "A2", "B"))
        up = (f"1+clip((t-{a0:.3f})/{RAMPA},0,1)*clip(({a1:.3f}-t)/{RAMPA},0,1)"
              f"*({k1:.4f}+({k2 - k1:.4f})*clip((t-{m - 0.5:.3f})/1.0,0,1))"
              f"+{kb:.4f}*clip((t-{b0:.3f})/{RAMPA},0,1)")
        fc = (f"[0:a]pan=stereo|c0=c0|c1=c0,asplit=2[v][key];"
              f"[1:a]aresample=48000,volume={mg:.2f}dB[m];"
              f"[m][key]sidechaincompress=threshold=0.02:ratio=2.5:attack=25:release=400:makeup=1,"
              f"volume='{up}':eval=frame[md];{amb};"
              f"[3:a]aresample=48000,volume={mg + ACENTO_DB:.2f}dB[acc];"
              f"[v][md][amb][acc]amix=inputs=4:normalize=0:duration=first[out]")
        ff(["-i", voz, "-i", MUSIC, *hoje, "-i", MUSIC_ACC, "-filter_complex", fc, "-map", "[out]", "-t", DUR,
            "-c:a", "pcm_s16le", pre])
        li, lp = normalize(pre, mix, LIMITE["mix"])
        names = list(win)
        return li, lp, dict(zip(names, mean_db(mix, [win[n] for n in names])))

    g = {"A1": 6.0, "A2": 7.5, "B": 7.0}
    for it in range(6):                   # acerta cada ganho até a média de cada trecho sem voz bater
        li, lp, med = com_trilha(g)
        print("  trilha sem voz, passada", it + 1, " | ".join(
            f"{n} {win[n][0]:.1f}–{win[n][1]:.1f} s: {g[n]:+.1f} dB → {med[n]:.1f} dB" for n in win))
        if all(abs(med[n] - SEM_VOZ_DB) < 0.2 for n in win):
            break
        for n in win:
            g[n] += SEM_VOZ_DB - med[n]
    print(f"{mix.name}: {li:.1f} LUFS, pico {lp:.1f} dBFS (voz {vi:.1f} LUFS, trilha {mg:+.1f} dB, sem voz "
          + ", ".join(f"{n} {g[n]:+.1f}" for n in win) + " dB)")
    # sem trilha: voz + ambiente do fecho (como no Ep. 1)
    fc = f"[0:a]pan=stereo|c0=c0|c1=c0[v];{amb.replace('[2:a]', '[1:a]')};[v][amb]amix=inputs=2:normalize=0:duration=first[out]"
    ff(["-i", voz, *hoje, "-filter_complex", fc, "-map", "[out]", "-t", DUR, "-c:a", "pcm_s16le", pre_nat])
    li, lp = normalize(pre_nat, mix_nat, LIMITE["mix-sem-musica"])
    print(f"{mix_nat.name}: {li:.1f} LUFS, pico {lp:.1f} dBFS")
    return mix, mix_nat


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
    nomes = ["P1a", "P1b", "P2", "P3", "P4", "P5", "P6"]
    print("linha do tempo:", " | ".join(f"{n} {a:.2f}-{b:.2f}" for n, a, b in zip(nomes, P0, P1)),
          f"| câm. 03 {T17:.2f} | CAM 5 {T18:.2f} | mapa {T_MAPA:.2f} | fachadas {T_FACH:.2f} "
          f"| fecho {T_FECHO:.2f} | fim {DUR:.2f}")
    t5 = T18 + cam_tau(CAMS["c5"], CAMS["c5"]["trilha"][0][0]), T18 + cam_tau(CAMS["c5"], CAMS["c5"]["trilha"][-1][0])
    print(f"vislumbre: pausa P4→P5 {GAPS[4]:.2f} s | 'vislumbre dela' {cue('vislumbre'):.2f}-{cue('dela.', end=True):.2f}"
          f" | travessia na CAM 5 {t5[0]:.2f}-{t5[1]:.2f} | a Zoe entra na Câmera 03 em {zoe_entra():.2f}")
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
