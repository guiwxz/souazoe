"""Monta o Reel 05 "Os 6 dias da Zoe · Parte 3" (9:16, 30 fps, ~76 s), narrado pela Isabela.

Ep. 3 (último) da série (dia 6 e a quinta, qua 23 e qui 24/09): "2 km em 7 minutos". Segue o mapa de tempo
de roteiros/serie-6-dias/roteiro.md com os tempos reais da narração (editor/words-05.json).
Base: build_04.py (Ep. 2), copiado e adaptado.

Como funciona:
  1. Áudio: apara o silêncio de audios/dia6/1..9.ogg (PARTS) e encadeia os parágrafos com as cartelas e os
     blocos de câmera sem voz entre eles (_timeline). CUTS encurta a pausa antes de "A gente estava muito longe" (P7). Voz
     com highpass + afftdn. A trilha (editor/trilha_05.py) é gerada aqui com as marcas reais: "correndo"
     desde o gancho, com um tempo forte em cada passagem da Zoe; baixa no P6; vira pad no P7 e corta antes
     de "A gente estava muito longe"; volta contida na quinta e abre um pouco no spoiler. Fica por baixo da
     voz com duck (sidechain). Saem duas mixagens em -14 LUFS: com trilha e sem trilha (voz + ambiente do
     fecho).
  2. Imagem: cada quadro é composto em Python (Pillow + OpenCV), plano a plano (shots()). As câmeras de
     segurança entram em cartão: os vídeos de celular filmando a tela (camera1, camera2, camera8) e a
     gravação de tela da camera9 são estabilizados por homografia (SIFT + RANSAC, quadro a quadro até um
     quadro de referência; cache em videos/ep3/) e a janela do cartão é definida no quadro de referência,
     sempre dentro da imagem da câmera. Câmera lenta com mistura de quadros (nunca abaixo de 0,6x) e zoom
     moderado. O mapa (camadas de `mapa.py ep3-camadas`) é desenhado aqui: a rota rosa vai sendo revelada
     (`rota_ruas`, em metros), a vista acompanha a ponta, o horário da última câmera vai na ponta da linha
     e os nomes das ruas acendem quando a Isabela fala cada um.
  3. Texto (ASS, queimado pelo ffmpeg): legendas em blocos de até 3 palavras com a palavra ativa em
     amarelo, contador de 6 dias (já com 5 cheios), gancho, cartelas, números grandes, etiquetas de horário
     e o fecho.

Requisitos: ffmpeg/ffprobe no PATH e um venv com Python 3.9+ e numpy, scipy, Pillow e opencv-python-headless
(o OpenCV só estabiliza as câmeras filmadas com o celular). As camadas do mapa saem de
`python editor/mapa.py ep3-camadas` (o build chama sozinho se faltar alguma).
Uso:
  <venv>/python editor/build_05.py              render completo → saida/video/video5/
  <venv>/python editor/build_05.py 36 52        só um trecho, para conferir → videos/ep3/trecho.mp4
  <venv>/python editor/build_05.py palavras     refaz words-05.json a partir de videos/ep3/palavras-small.json
                                                (se PARTS, a linha do tempo ou TRECHOS mudarem)
  <venv>/python editor/build_05.py quadros 3.2 41.5 ...   só os quadros (PNG em videos/ep3/quadros/)
  <venv>/python editor/build_05.py audio        só refaz as duas mixagens e troca o áudio dos MP4 já renderizados
As palavras vieram do faster-whisper (small, int8, um arquivo por parágrafo), com a grafia da fala (TEXTO) e
os inícios/fins acertados pelos trechos de voz do envelope de energia (TRECHOS).
"""
import difflib
import json
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "editor"))

DRIVE = ROOT / "drive"
SET = DRIVE / "set26"
D6 = SET / "dia 6e7"                                  # câmeras renomeadas pelo Guilherme (várias sem extensão)
VOZ = ROOT / "audios" / "dia6"                        # a narração do Ep. 3 (1..9.ogg, um por parágrafo)
WORK = ROOT / "videos" / "ep3"                        # cópias de trabalho (não versionadas)
MAPS = ROOT / "videos" / "mapas"                      # camadas de `mapa.py ep3-camadas`
FONTS = ROOT / "editor" / "fonts"
WORDS = ROOT / "editor" / "words-05.json"
MUSIC = ROOT / "audios" / "trilha-05.wav"
MUSIC_ACC = ROOT / "audios" / "trilha-05-acento.wav"  # as marcas das passagens (mixadas à parte, com o duck)
OUTDIR = ROOT / "saida" / "video" / "video5"
OUT = OUTDIR / "05-os-6-dias-parte-3.mp4"
OUT_NAT = OUTDIR / "05-os-6-dias-parte-3-sem-musica.mp4"
ASS = OUTDIR / "legendas-05.ass"
W, H, FPS = 1080, 1920, 30
HANDLE = "@souazoe.pf"

# identidade
INK, CREAM, LILAC, PINK, MUTED = (0x17, 0x13, 0x1F), (0xF6, 0xF1, 0xE9), (0xB9, 0xA7, 0xF3), (0xEC, 0x48, 0x99), (0x6E, 0x66, 0x7A)


def ass_c(rgb):
    return "&H{:02X}{:02X}{:02X}&".format(rgb[2], rgb[1], rgb[0])


# ================================================================ ONDE A ZOE APARECE (fácil de trocar)
# Segundos de cada arquivo (relógio do arquivo, não do Reel), medidos por diferença de quadros (com o quadro
# estabilizado nas gravações de celular) e conferidos a olho em quadros ampliados (tiras em videos/ep3/zoe-*.jpg).
# Cada plano em CAMS (ss/se, a janela e, onde há círculo, a trilha) foi acertado dentro desses intervalos; mudar um
# intervalo aqui não move o plano sozinho, mas confere() avisa (antes do render) se algum plano sair do intervalo
# da sua câmera e se alguma janela sair da imagem.
ZOE = {
    # confirmados pelo Guilherme (06/10); entre parênteses, o que a diferença de quadros achou antes
    "camera1": (8.0, 11.0),                           # (7,7 a 10,8) corre pelo outro lado da rua, lá no alto do quadro
    "camera2-cam2": (13.75, 16.45),                   # CAM 2: atravessa a Lava Pés, nítida (a travessia do bloco)
    "camera2-cam1": (11.60, 12.70),                   # CAM 1: desce a rua lá do fundo (P6)
    "camera2-lixeira": (22.90, 23.98),                # a vista da lixeira azul (a CAM 2 com zoom, de ré no DVR): atravessa na diagonal (P6)
    "camera3": (19.45, 21.70),                        # atravessa na frente do carro branco (08:45:57) e some rua acima
    "camera4": (25.45, 27.35),                        # no alto do quadro, atrás dos carros (08:46:31 a 33)
    "camera5": (9.97, 11.70),                         # atravessa e sobe (08:46:33)
    "camera6": (2.97, 4.43),                          # sobe a rua em direção à avenida (08:46:37)
    "camera7": (2.0, 10.0),                           # (2,4 a 5,0 bem visível) entra por baixo e vira um pontinho rua acima
    "camera8": (7.0, 9.0),                            # (6,6 a 8,6) o vulto escuro descendo junto ao meio-fio (08:50:4x)
    "camera9": (2.0, 3.0),                            # (2,0 a 3,3) sai de trás do arbusto e entra na faixa de sombra
}

# ================================================================ a fala (grafia e trechos de voz)
# o que ela falou (vale para as legendas; o whisper escreveu "Coronela", "Morou", "Daliola", "seguiu a teta em",
# "mapiou" e "Tinha um visto")
TEXTO = {
    1: "É inacreditável o que essa cachorra fez. Foram dois quilômetros em sete minutos.",
    2: "Na quarta e quinta, com a ajuda da Secretaria de Segurança, a gente foi seguindo o caminho dela, "
       "câmera por câmera. As imagens eram da sexta-feira de manhã, logo depois que ela fugiu.",
    3: "Ela subiu toda Lava Pés e dobrou na Coronel Chicuta, indo pra avenida.",
    4: "Ela atravessou a Avenida Brasil, desceu pela Quinze até a Morom e seguiu até a Teixeira Soares.",
    5: "Dali, ela desceu em direção à Independência e foi reto, até o final da rua.",
    6: "E a gente ficava abismado vendo aquilo. Como é que nenhum carro pegou ela? Foram várias ruas "
       "movimentadas, inclusive a avenida principal.",
    7: "Foram seis dias de busca, e tudo que a gente mapeou foram só os primeiros dez minutos de fuga dela, "
       "lá na sexta-feira. A gente estava muito longe de alcançar ela.",
    8: "Na quinta, antes da gente conseguir descobrir pra que lado ela foi, veio uma ligação. Tinham visto a "
       "Zoe no Instituto Menino Deus, a uns dois quilômetros dali.",
    9: "E aí, todo o nosso foco foi pra lá.",
}
# trechos de voz de cada arquivo (envelope de energia: -35 dB do pico em janelas de 10 ms, pausas ≥ 90 ms):
# (início, fim, palavras). As pausas curtas dentro de uma palavra (o /k/ de "quinta", o /f/ de "foi" e de
# "foco") foram juntadas; o sopro de 5,41 a 5,56 s no arquivo 2 é respiração (centroide ~3 kHz, -25 dB).
TRECHOS = {
    1: [(0.43, 2.12, 7), (2.39, 4.10, 6)],
    2: [(0.23, 5.07, 21), (5.66, 8.75, 12)],
    3: [(0.54, 3.67, 10), (3.76, 4.53, 3)],
    4: [(0.58, 2.20, 5), (2.33, 3.85, 6), (4.20, 5.58, 6)],
    5: [(0.32, 2.66, 10), (2.94, 3.69, 5)],
    6: [(0.57, 2.43, 7), (2.81, 4.38, 7), (4.48, 7.62, 8)],
    7: [(0.39, 1.81, 5), (1.91, 6.08, 15), (6.54, 7.33, 3), (8.63, 10.68, 8)],
    8: [(0.16, 0.95, 2), (1.07, 3.32, 9), (3.42, 3.66, 1), (4.06, 4.85, 3), (5.46, 7.70, 8), (7.81, 9.05, 5)],
    9: [(0.29, 0.76, 2), (0.88, 1.52, 3), (1.64, 1.95, 1), (2.07, 2.47, 3)],
}

# ================================================================ áudio e linha do tempo
# (arquivo, início, fim) em segundos: a fala sem o silêncio da gravação (≈ 80 ms antes da primeira sílaba e
# ≈ 150 ms depois da última, pelo envelope de energia)
PARTS = [
    (1, 0.35, 4.39),    # P1: É inacreditável ... sete minutos.   (até o fim do arquivo: o "s" final de "minutos"
                        # vai de 4,27 a 4,39 s, depois de ~150 ms de quase silêncio, e a gravação termina com ele soando)
    (2, 0.15, 8.90),    # P2: Na quarta e quinta ... logo depois que ela fugiu.
    (3, 0.46, 4.68),    # P3: Ela subiu toda Lava Pés ... indo pra avenida.
    (4, 0.50, 5.68),    # P4: Ela atravessou a Avenida Brasil ... Teixeira Soares.
    (5, 0.24, 3.82),    # P5: Dali, ela desceu ... até o final da rua.
    (6, 0.49, 7.77),    # P6: E a gente ficava abismado ... a avenida principal.
    (7, 0.31, 10.83),   # P7: Foram seis dias de busca ... muito longe de alcançar ela.
    (8, 0.08, 9.20),    # P8: Na quinta, antes da gente ... a uns dois quilômetros dali.
    (9, 0.21, 2.62),    # P9: E aí, todo o nosso foco foi pra lá.
]
# silêncio tirado de dentro de um arquivo: {arquivo: [(início, fim), ...]}
CUTS = {7: [(7.62, 8.17)]}   # "sexta-feira." (termina em 7,33) → "A gente" (começa em 8,63): a pausa cai de 1,30 para 0,75 s
FADES = {0: (0.015, 0.025)}  # (entrada, saída) por parte; padrão (0,015, 0,040). P1: o "s" truncado termina sem degrau
# O "s" final de "Soares" (P4): a gravação (4.ogg) termina quando ele começa (a vogal "-are" vai até 5,53 s, ~150 ms de
# silêncio e só o começo do "s", de 5,65 a 5,69 s). O P4 vai até 5,68 s (com o começo natural do "s") e continua com a
# parte estável do "s" final de "minutos" (1.ogg, 4,305 a 4,392 s; antes de 4,305 há um ruído grave), da própria Isabela, com uma emenda cruzada de 12 ms
# e saída de 30 ms. O nível segue o "S" inicial de "Soares" (4.ogg, 5,33 a 5,40 s, -27,0 dBFS) menos os 2,2 dB que,
# no 1.ogg, separam o "S" de "sete" do "s" final de "minutos": +1,9 dB sobre o trecho de origem.
# {parte: (arquivo, início, fim, ganho em dB, emenda cruzada, saída)}
ENXERTO = {3: (1, 4.305, 4.392, 1.9, 0.012, 0.030)}
LEAD = 0.20                  # antes da primeira palavra
FECHO = 2.80                 # a Zoe em casa, sem voz (o trecho em que ela olha para a câmera, de olhos abertos)


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


def _ext(i):
    """Quanto o enxerto (ENXERTO) alonga a voz da parte i (a linha do tempo não anda: sai do respiro seguinte)."""
    if i not in ENXERTO:
        return 0.0
    _, a, b, _, x, _ = ENXERTO[i]
    return b - a - x


# ================================================================ câmeras de segurança
# Cada câmera entra num cartão (`vista`: largura, altura, centro x, centro y na tela). O trecho do arquivo vai
# de `ss` a `se`; `lenta`: [(s, v)] = velocidade v a partir do instante s do arquivo (nunca abaixo de 0,6x).
# `estab`: estabiliza por homografia até o quadro `ref` (s do arquivo), procurando pontos em `mask` (px).
# `janela`: [(s, cx, cy, largura)] no quadro de referência (a altura sai da proporção do cartão), com troca
# suave entre as chaves; `rot`: giro da janela (graus, sentido anti-horário na tela). `trilha`: onde a Zoe está
# (s, x, y no quadro de referência), medida por diferença de quadros: só serve ao círculo (`anel`, raio em px
# da tela) e só nas câmeras em que ela é pequena demais para achar sozinho. `borrar`: caixas (px do quadro de
# referência) sempre borradas (placas). `chip`: a etiqueta de horário no canto do cartão.
VISTA = (1000, 667, 540, 790)           # 3:2, margens iguais (40 px), entre o contador e as legendas
CAMS = {
    # camera1 (CAM 3, Lava Pés, celular filmando o monitor): o relógio em close, em "sexta-feira de manhã"
    # camera1 (CAM 3, Lava Pés, celular filmando o monitor): ela corre pelo outro lado da rua, lá no alto do
    # quadro, passando por trás do relógio (08:44:55); em 9,2 s o celular se aproxima do monitor, e a 2ª parte
    # (c1b) segue com a imagem maior. As duas em velocidade real, com o círculo (ela é minúscula)
    "c1": {"src": D6 / "camera1 - rua lava pes", "size": (848, 474), "ss": 7.70, "se": 9.10,
           "estab": {"ref": 8.4, "mask": (0, 20, 760, 450)},
           "janela": [(7.70, 545, 180, 470), (9.10, 450, 180, 470)],
           "chip": "SEX 18/09 · 08H44",
           "anel": 46,
           "trilha": [(7.80, 666, 55), (7.87, 644, 55), (7.93, 632, 53), (8.00, 609, 53), (8.07, 590, 52),
                      (8.13, 553, 50), (8.20, 538, 50), (8.27, 518, 49), (8.33, 494, 48), (8.40, 474, 47),
                      (8.47, 454, 48), (8.53, 432, 47), (8.60, 412, 47), (8.67, 391, 48), (8.73, 373, 49),
                      (8.80, 356, 49), (8.87, 343, 50), (8.93, 327, 52), (9.00, 308, 53), (9.07, 288, 55)]},
    "c1b": {"src": D6 / "camera1 - rua lava pes", "size": (848, 474), "ss": 9.62, "se": 10.80,
            "estab": {"ref": 10.4, "mask": (0, 20, 848, 450)},
            "janela": [(9.62, 330, 197, 480), (10.80, 278, 208, 480)],
            "chip": "SEX 18/09 · 08H44",
            "anel": 46,
            "trilha": [(9.75, 291, 95), (9.82, 271, 98), (9.88, 257, 99), (9.95, 245, 102), (10.02, 234, 104),
                       (10.08, 221, 106), (10.15, 209, 108), (10.22, 198, 110), (10.28, 187, 111), (10.35, 176, 113),
                       (10.42, 169, 114), (10.48, 156, 116), (10.55, 150, 118), (10.62, 138, 120), (10.68, 132, 121),
                       (10.75, 122, 123)]},
    # camera2, CAM 2 (Lava Pés): a travessia mais nítida, logo depois de "logo depois que ela fugiu"
    "c2a": {"src": D6 / "camera2 - lava pes", "size": (848, 478), "ss": 13.78, "se": 15.30,
            "lenta": [(13.80, 0.75), (14.70, 1.0)],
            "estab": {"ref": 14.3, "mask": (40, 0, 848, 470)},
            "janela": [(13.78, 560, 205, 560), (14.50, 540, 200, 540), (15.30, 495, 192, 520)],
            "chip": "SEX 18/09"},
    # camera3 (Coronel Chicuta, 08:45:57): atravessa na frente do carro branco
    "c3": {"src": D6 / "camera3 - rua coronel chicuta.mp4", "size": (736, 480), "ss": 19.40, "se": 20.95,
           "lenta": [(19.45, 0.8), (20.35, 1.0)],
           "janela": [(19.40, 330, 232, 600)],
           "chip": "SEX 18/09 · 08H45"},
    # camera4 (FRENTE DIREITA, 08:46:31 a 33): vem pela rua, no alto do quadro
    "c4": {"src": D6 / "camera4 - rua coronel chicuta.mp4", "size": (848, 478), "ss": 25.85, "se": 27.05,
           "lenta": [(25.90, 0.85)],
           # o zoom acompanha a corrida dela pelo alto do quadro (sem círculo: ampliada, ela aparece sozinha)
           "janela": [(25.85, 470, 178, 528), (27.05, 584, 178, 528)],
           "borrar": [(424, 82, 462, 100)],          # a placa do carro bege
           "chip": "SEX 18/09 · 08H46",
           "trilha": [(25.47, 395, 14), (25.60, 409, 17), (25.73, 423, 21), (25.87, 443, 24), (26.00, 464, 29),
                      (26.13, 489, 32), (26.27, 516, 40), (26.40, 547, 47), (26.53, 583, 56), (26.67, 622, 68),
                      (26.80, 664, 80), (26.93, 706, 97), (27.07, 765, 117), (27.20, 805, 138), (27.33, 842, 158)]},
    # camera5 (FRENTE ESQUERDA, o mesmo prédio e o mesmo instante): atravessa e sobe
    "c5": {"src": D6 / "camera5 - coronel chicuta.mp4", "size": (848, 478), "ss": 9.98, "se": 11.05,
           "lenta": [(10.0, 0.85)],
           "janela": [(9.98, 330, 228, 660)],        # sem o letreiro da loja (com telefone), à direita
           "chip": "SEX 18/09 · 08H46"},
    # camera6 (CAM 3 Intelbras, chegando na Av. Brasil, 08:46:37)
    "c6": {"src": D6 / "camera6 - coronel chicuta chegando na avbrasil", "size": (1024, 576), "ss": 2.92,
           "se": 4.35, "lenta": [(2.97, 0.8), (3.90, 1.0)],
           "janela": [(2.92, 380, 260, 760), (4.35, 400, 232, 690)],
           "chip": "SEX 18/09 · 08H46"},
    # camera7 (Camera 02, chegando na Av. Brasil, 08:46:43): entra por baixo e corre rua acima
    # camera7 (Camera 02, chegando na Av. Brasil): a passagem toda vai de 2 a 10 s, e ela vira um pontinho rua
    # acima; entra só o começo, onde ela é maior (velocidade real, sem círculo), com um zoom leve acompanhando
    "c7": {"src": D6 / "camera7 - chegando na av brasil.mp4", "size": (1280, 720), "ss": 2.30, "se": 4.80,
           "janela": [(2.30, 560, 360, 1076), (3.20, 560, 360, 1076), (4.80, 620, 404, 840)],
           "chip": "SEX 18/09 · 08H46",
           "trilha": [(2.42, 20, 633), (2.50, 49, 623), (2.58, 103, 610), (2.67, 142, 599), (2.75, 189, 584),
                      (2.83, 219, 572), (2.92, 262, 559), (3.00, 286, 551), (3.08, 319, 539), (3.17, 340, 528),
                      (3.25, 367, 519), (3.33, 385, 512), (3.42, 408, 503), (3.50, 423, 496), (3.58, 444, 488),
                      (3.67, 456, 484), (3.75, 475, 476), (3.83, 488, 470), (3.92, 506, 464), (4.00, 516, 462),
                      (4.08, 528, 457), (4.17, 537, 453), (4.25, 549, 448), (4.33, 558, 445), (4.42, 567, 441),
                      (4.50, 574, 437), (4.58, 583, 434)]},
    # camera8 (Teixeira Soares, celular filmando o app de outra câmera, 08:50): estabilizada e desvirada
    "c8": {"src": D6 / "camera8 - teixeira soares", "size": (576, 1024), "ss": 7.00, "se": 9.00,
           "estab": {"ref": 5.0, "mask": (60, 150, 560, 820)},
           "janela": [(7.00, 396, 372, 310)], "rot": 37.0,
           "chip": "SEX 18/09 · 08H50",
           # ela desce junto ao meio-fio, minúscula na imagem do app: leva o círculo
           "anel": 46,
           "trilha": [(6.63, 383, 272), (6.83, 386, 276), (7.03, 396, 285), (7.23, 403, 289), (7.43, 414, 301),
                      (7.63, 424, 309), (7.93, 435, 321), (8.33, 454, 342), (8.53, 464, 360), (8.63, 470, 368),
                      (8.77, 477, 379), (8.90, 485, 391), (9.00, 489, 395), (9.07, 490, 401)]},
    # P6 ("abismado"): as outras vistas da camera2 (Lava Pés), na velocidade real ou só um pouco lentas. A vista
    # dos 28 a 30 s é a mesma CAM 2 do c2a, ampliada no DVR (a mesma passagem): não entra, para não repetir.
    # c2d: a CAM 1, de longe: ela desce a rua lá do fundo e atravessa (o celular treme: janela andando)
    "c2d": {"src": D6 / "camera2 - lava pes", "size": (848, 478), "ss": 11.35, "se": 12.70,
            "lenta": [(11.45, 0.75)],
            "estab": {"ref": 12.0, "mask": (260, 0, 848, 470)},
            "janela": [(11.35, 540, 170, 560), (12.00, 470, 190, 560), (12.70, 380, 240, 560)],
            "chip": "SEX 18/09"},
    # c2b: a vista da lixeira azul: ela atravessa na diagonal
    # (nessa parte da gravação o DVR estava sendo rebobinado: ela anda de rabo para a frente. "reverso" toca o
    # trecho de trás para a frente, e ela corre de cabeça para a frente, da direita para a esquerda. Medido no
    # quadro da CAM 2, o rebobinar era a ~1x (400 px/s contra 408 px/s no c2a), então a velocidade fica natural.
    # É o mesmo momento do c2a, visto com o zoom do DVR.)
    "c2b": {"src": D6 / "camera2 - lava pes", "size": (848, 478), "ss": 22.85, "se": 23.98, "reverso": True,
            "lenta": [(22.90, 0.8)],
            "estab": {"ref": 23.3, "mask": (0, 0, 848, 430)},
            "janela": [(22.85, 410, 215, 560), (23.40, 470, 225, 560), (24.10, 520, 235, 560)],
            "chip": "SEX 18/09"},
    # camera9 (Instituto Menino Deus, qui 24/09): o spoiler
    # (sai de trás do arbusto em 2 s e entra na faixa de sombra do gramado em 3 s): a mais difícil de ver,
    # leva o círculo; câmera lenta leve (0,8x)
    "c9": {"src": D6 / "camera9 - instituto menino deus", "size": (384, 848), "ss": 1.70, "se": 3.30,
           "lenta": [(1.70, 0.8)],
           "estab": {"ref": 2.5, "mask": (0, 60, 384, 848)},
           "janela": [(1.70, 192, 324, 310)],
           "vista": (1000, 1200, 540, 900),
           "chip": "QUI 24/09",
           "anel": 46,
           "trilha": [(1.86, 236, 329), (2.06, 232, 330), (2.26, 226, 328), (2.46, 222, 328), (2.59, 213, 324),
                      (2.74, 207, 324), (2.88, 201, 321), (3.01, 199, 321), (3.18, 194, 320), (3.31, 190, 318)]},
}
RAMP = 0.30          # a troca de velocidade (s na linha do tempo), suave


def anel_ativo(key):
    """O círculo lilás vai só onde ela é pequena demais para achar sozinho (camera1, camera8 e camera9)."""
    c = CAMS[key]
    return "anel" in c and "trilha" in c


def vista(key):
    return CAMS[key].get("vista", VISTA)


def cam_plan(c):
    """Velocidades por trecho: [(s, v)], os instantes τ (desde o início do plano) de cada troca e a duração."""
    ks = [(c["ss"], 1.0)] + [k for k in c.get("lenta", []) if k[0] > c["ss"]]
    if c.get("lenta") and c["lenta"][0][0] <= c["ss"]:
        ks[0] = (c["ss"], c["lenta"][0][1])
    taus, tau = [], 0.0
    for i, (s, v) in enumerate(ks):
        taus.append(tau)
        tau += ((ks[i + 1][0] if i + 1 < len(ks) else c["se"]) - s) / v
    return ks, taus, tau


def cam_time(c, tau):
    """Instante do arquivo no instante τ do plano. As trocas de velocidade são suaves (smoothstep de RAMP s,
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
    """O inverso de cam_time (por busca), para sincronizar: em que τ do plano o arquivo chega em s."""
    lo, hi = 0.0, cam_plan(c)[2]
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cam_time(c, mid) < s else (lo, mid)
    return lo


def cam_dur(key):
    return cam_plan(CAMS[key])[2]


# ---------------------------------------------------------------- quadros e estabilização
_camcache = {}
_cache = {}


def cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def cam_frames(key):
    """Os quadros do trecho do arquivo (ss − 0,4 a se + 0,4) na memória (uint8 RGB) e os instantes reais (pts).
    A janela de referência da estabilização também entra."""
    if key in _camcache:
        return _camcache[key]
    c = CAMS[key]
    w, h = c["size"]
    a = min(c["ss"], c.get("estab", {}).get("ref", c["ss"])) - 0.4
    b = max(c["se"], c.get("estab", {}).get("ref", c["se"])) + 0.4
    pts = np.array([float(x.split(",")[0]) for x in subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "frame=pts_time", "-of", "csv=p=0",
         str(c["src"])], capture_output=True, text=True, check=True).stdout.split() if x.split(",")[0]])
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(c["src"]), "-fps_mode", "passthrough", "-an",
                          "-t", f"{b + 0.3:.3f}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    keep, ts = [], []
    for t in pts:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        if a <= t <= b:
            keep.append(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
            ts.append(t)
    p.stdout.read()
    p.stdout.close()
    p.wait()
    _camcache[key] = (np.stack(keep), np.array(ts))
    return _camcache[key]


def release(key):
    for k in [k for k in _camcache if k == key or (isinstance(k, tuple) and k[1] == key)]:
        del _camcache[k]


def estab(key):
    """Homografias (n, 3, 3) que levam cada quadro de cam_frames(key) ao quadro de referência. Identidade nas
    câmeras fixas. SIFT com teste de razão (0,7) e RANSAC (2,5 px); os quadros que falham (menos de 25 pontos
    coerentes) são interpolados, e a série é suavizada de leve (gaussiana de 1 quadro). Cache em WORK."""
    ck = ("H", key)
    if ck in _camcache:
        return _camcache[ck]
    c = CAMS[key]
    frs, ts = cam_frames(key)
    if "estab" not in c:
        _camcache[ck] = np.repeat(np.eye(3)[None], len(ts), axis=0)
        return _camcache[ck]
    e = c["estab"]
    sig = f"{c['src'].name}|{ts[0]:.4f}|{ts[-1]:.4f}|{len(ts)}|{e['ref']}|{e['mask']}"
    cache = WORK / f"estab-{key}.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if str(z["sig"]) == sig:
            _camcache[ck] = z["H"]
            return _camcache[ck]
    import cv2   # noqa: E402  (só aqui: as câmeras filmadas com o celular)
    sift = cv2.SIFT_create(4000)
    fl = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
    gray = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in frs]
    iref = int(np.argmin(np.abs(ts - e["ref"])))
    mask = np.zeros(gray[0].shape, np.uint8)
    x0, y0, x1, y1 = e["mask"]
    mask[y0:y1, x0:x1] = 255
    kr, dr = sift.detectAndCompute(gray[iref], mask)
    Hs, ok = [], []
    for i, g in enumerate(gray):
        if i == iref:
            Hs.append(np.eye(3))
            ok.append(True)
            continue
        ki, di = sift.detectAndCompute(g, None)
        good = []
        if di is not None and len(ki) > 10:
            good = [m for m, n in fl.knnMatch(di, dr, k=2) if m.distance < 0.7 * n.distance]
        Hm, inl = None, 0
        if len(good) > 25:
            A = np.float32([ki[m.queryIdx].pt for m in good])
            B = np.float32([kr[m.trainIdx].pt for m in good])
            Hm, msk = cv2.findHomography(A, B, cv2.RANSAC, 2.5)
            inl = int(msk.sum()) if msk is not None else 0
        if Hm is None or inl < 25:
            Hs.append(np.full((3, 3), np.nan))
            ok.append(False)
        else:
            Hs.append(Hm / Hm[2, 2])
            ok.append(True)
    H_ = np.array(Hs)
    good = np.array(ok)
    for r in range(3):
        for q in range(3):
            v = H_[:, r, q]
            v[~good] = np.interp(np.flatnonzero(~good), np.flatnonzero(good), v[good])
            k = np.exp(-0.5 * (np.arange(-3, 4) / 1.0) ** 2)
            k /= k.sum()
            H_[:, r, q] = np.convolve(np.pad(v, 3, mode="edge"), k, "valid")
    print(f"  estabilização {key}: {good.sum()}/{len(good)} quadros (os outros interpolados)")
    np.savez(cache, H=H_, sig=np.array(sig))
    _camcache[ck] = H_
    return H_


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def janela(key, s):
    """(cx, cy, largura) da janela no quadro de referência no instante s do arquivo. Duas chaves: smoothstep;
    mais de duas: interpolação linear suavizada (gaussiana de 0,18 s), para a janela andar sem parar em cada
    chave."""
    ks = CAMS[key]["janela"]
    if s <= ks[0][0] or len(ks) == 1:
        return ks[0][1:]
    if len(ks) == 2:
        (s0, *a), (s1, *b) = ks
        u = ease((s - s0) / (s1 - s0))
        return tuple(lerp(p, q, u) for p, q in zip(a, b))

    def make():
        grid = np.arange(ks[0][0] - 0.6, ks[-1][0] + 0.6, 1 / 120)
        sig = 0.18 * 120
        k = np.exp(-0.5 * (np.arange(-int(3 * sig), int(3 * sig) + 1) / sig) ** 2)
        k /= k.sum()
        cols = []
        for j in range(1, 4):
            v = np.interp(grid, [q[0] for q in ks], [q[j] for q in ks])
            cols.append(np.convolve(np.pad(v, len(k) // 2, mode="edge"), k, "valid"))
        return grid, cols
    grid, cols = cached(("jan", key), make)
    return tuple(float(np.interp(s, grid, c)) for c in cols)


def janela_A(key, s):
    """Matriz 3x3: quadro de referência → pixels do cartão (translada, gira `rot` e escala)."""
    vw, vh = vista(key)[:2]
    cx, cy, ww = janela(key, s)
    th = math.radians(CAMS[key].get("rot", 0.0))
    k = vw / ww
    c, sn = math.cos(th) * k, math.sin(th) * k
    # u = c·(x−cx) + sn·(y−cy) + vw/2 ;  v = −sn·(x−cx) + c·(y−cy) + vh/2
    return np.array([[c, sn, vw / 2 - c * cx - sn * cy],
                     [-sn, c, vh / 2 + sn * cx - c * cy],
                     [0, 0, 1.0]])


def cantos(key, s):
    """Os 4 cantos da janela no quadro de referência."""
    vw, vh = vista(key)[:2]
    Ai = np.linalg.inv(janela_A(key, s))
    return [(Ai @ np.array([u, v, 1.0]))[:2] for u, v in ((0, 0), (vw, 0), (vw, vh), (0, vh))]


def cam_card(key, s):
    """O cartão (vw x vh, RGB) no instante s do arquivo: os dois quadros vizinhos, cada um levado ao quadro de
    referência pela sua homografia e daí à janela, misturados (câmera lenta sem tranco). Placas borradas."""
    import cv2   # noqa: E402
    frs, ts = cam_frames(key)
    Hs = estab(key)
    vw, vh = vista(key)[:2]
    A = janela_A(key, s)
    i = int(np.clip(np.searchsorted(ts, s, side="right") - 1, 0, len(ts) - 2))
    a = float(np.clip((s - ts[i]) / (ts[i + 1] - ts[i]), 0, 1))
    out = None
    for j, wgt in ((i, 1 - a), (i + 1, a)):
        if wgt < 1e-3:
            continue
        im = cv2.warpPerspective(frs[j], A @ Hs[j], (vw, vh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        out = im.astype(np.float32) * wgt if out is None else out + im.astype(np.float32) * wgt
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    for b in CAMS[key].get("borrar", []):
        pts = [(A @ np.array([x, y, 1.0]))[:2] for x, y in ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        box = (max(0, int(min(xs)) - 4), max(0, int(min(ys)) - 4), min(vw, int(max(xs)) + 5), min(vh, int(max(ys)) + 5))
        if box[2] > box[0] and box[3] > box[1]:
            reg = img.crop(box)
            for _ in range(3):
                reg = reg.filter(ImageFilter.BoxBlur(10))
            img.paste(reg, box[:2])
    return img


def confere_janelas(key, dentro=None):
    """Confere, quadro a quadro, se a janela fica dentro da imagem do arquivo (pela homografia inversa) e, se
    `dentro` (polígono no quadro de referência) for dado, dentro da área útil. Devolve a pior folga (px)."""
    c = CAMS[key]
    frs, ts = cam_frames(key)
    Hs = estab(key)
    w, h = c["size"]
    pior = 1e9
    for i, t in enumerate(ts):
        if not (c["ss"] - 0.05 <= t <= c["se"] + 0.05):
            continue
        Hi = np.linalg.inv(Hs[i])
        for x, y in cantos(key, t):
            p = Hi @ np.array([x, y, 1.0])
            u, v = p[0] / p[2], p[1] / p[2]
            pior = min(pior, u, v, w - u, h - v)
    return pior


def area_util(key, margem=6):
    """Máscara (h x w, bool) do que fica à vista no quadro de referência em todos os quadros do plano:
    a interseção dos quadros do arquivo levados ao quadro de referência, com `margem` px para dentro."""
    import cv2   # noqa: E402
    c = CAMS[key]
    frs, ts = cam_frames(key)
    Hs = estab(key)
    w, h = c["size"]
    m = np.ones((h, w), np.uint8)
    base = np.zeros((h, w), np.uint8)
    base[margem:h - margem, margem:w - margem] = 1
    for i, t in enumerate(ts):
        if c["ss"] - 0.05 <= t <= c["se"] + 0.05:
            m &= cv2.warpPerspective(base, Hs[i], (w, h), flags=cv2.INTER_NEAREST)
    return m.astype(bool)


# ================================================================ a linha do tempo
SEGURA = 0.63        # o gancho fica parado (rota inteira + 2 KM · 7 MIN) depois de "sete minutos" (com o "s" final,
                     # a cartela DIA 6 entra em 4,87 s, ~0,8 s depois do fim da vogal de "minutos")
DIA6 = 1.00          # cartela DIA 6 · QUA 23/09 (entre o P1 e o P2)
QUI = 1.00           # cartela QUI 24/09 (entre o P7 e o P8)
LEAD_P3 = 0.30       # o mapa entra antes da voz do P3 (a linha já começa a andar)
MAPA_INTER = 0.90    # cada mapa entre as câmeras da Chicuta
OVL_P4 = 0.80        # o P4 ("Ela atravessou a...") começa no fim da camera7
OVL_P5 = 0.35        # o P5 ("Dali, ela...") começa no fim da camera8
RESPIRO = 0.35       # P5 → P6 e P6 → P7
RESPIRO_P9 = 0.30    # P8 → P9
SPOILER_GAP = 0.15   # P9 → camera9


def local_final(i, t):
    """Instante final (na linha do tempo do Reel) do instante local t do arquivo da parte i."""
    f, a, _ = PARTS[i]
    return P0[i] + t - a - _removed(f, t) + _removed(f, a)


def _timeline():
    """Início de cada parte (P0) e de cada bloco sem voz (T)."""
    T = {}
    t = LEAD
    P0[0] = t; t += _dur(0)                                  # P1, o gancho no mapa
    t += SEGURA
    T["dia6"] = t; t += DIA6
    P0[1] = t; t += _dur(1)                                  # P2
    T["sv1"] = P0[1]
    T["c1b"] = t - cam_dur("c1b")                            # a camera1 termina junto com o P2 ("...fugiu.")
    T["c1"] = T["c1b"] - cam_dur("c1")                       # e começa em "...da sexta-feira de manhã"
    T["c2a"] = t; t += cam_dur("c2a")                        # a CAM 2 da Lava Pés, sem voz
    T["m3"] = t; t += LEAD_P3
    P0[2] = t; t += _dur(2)                                  # P3 no mapa
    t += 0.10
    T["c3"] = t; t += cam_dur("c3")
    T["ma"] = t; t += MAPA_INTER
    T["c4"] = t; t += cam_dur("c4")
    T["c5"] = t; t += cam_dur("c5")
    T["mb"] = t; t += MAPA_INTER
    T["c6"] = t; t += cam_dur("c6")
    T["c7"] = t; t += cam_dur("c7")
    T["m4"] = t
    P0[3] = t - OVL_P4; t = P0[3] + _dur(3)                  # P4 (começa na camera7, segue no mapa)
    t += 0.10
    T["c8"] = t; t += cam_dur("c8")
    T["m5"] = t
    P0[4] = t - OVL_P5; t = P0[4] + _dur(4)                  # P5 no mapa
    t += RESPIRO
    P0[5] = t; t += _dur(5)                                  # P6: câmeras + mapa
    T["c2b"] = P0[5] - 0.05                                  # "E a gente ficava abismado vendo aquilo."
    T["c2d"] = T["c2b"] + cam_dur("c2b")                     # "Como é que nenhum carro pegou ela?"
    T["m6"] = T["c2d"] + cam_dur("c2d")                      # "Foram várias ruas movimentadas..." (o mapa até a quinta)
    t += RESPIRO
    P0[6] = t; t += _dur(6)                                  # P7 no mapa
    T["qui"] = t; t += QUI
    P0[7] = t; t += _dur(7)                                  # P8 no mapa
    t += RESPIRO_P9
    P0[8] = t; t += _dur(8)                                  # P9: o satélite
    t += SPOILER_GAP
    T["c9"] = t; t += cam_dur("c9")
    T["fecho"] = t
    T["fim"] = t + FECHO
    return {k: round(v, 3) for k, v in T.items()}


P0 = [0.0] * len(PARTS)
T = _timeline()
P0 = [round(x, 3) for x in P0]
P1 = [round(s + _dur(i) + _ext(i), 3) for i, s in enumerate(P0)]       # fim da voz de cada parte
DUR = round(T["fim"] * FPS) / FPS
NFRAMES = int(round(DUR * FPS))

_WORDS = json.loads(WORDS.read_text(encoding="utf-8")) if WORDS.exists() else []


def _norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^\w]", "", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))


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


# trocas na grafia do whisper (small) → a fala, antes de alinhar com TEXTO
WHISPER_FIX = {"coronela": "coronel", "morou": "morom", "mapiou": "mapeou", "para": "pra"}


# a última palavra do arquivo termina no fim do som que entra (o "s" final, que fica fora dos TRECHOS de voz)
FIM_PALAVRA = {1: lambda: PARTS[0][2], 4: lambda: PARTS[3][2] + _ext(3)}


def palavras():
    """videos/ep3/palavras-small.json (tempos de cada arquivo) → editor/words-05.json na linha do tempo final.
    A grafia vem de TEXTO; as palavras do whisper são casadas com as do texto (difflib) e, onde não casam
    ("Daliola" = "Dali, ela"; "a teta em" = "até a"; "Tinha um" = "Tinham"), o intervalo é repartido pelo
    tamanho das palavras. Em cada trecho de voz (TRECHOS), a primeira palavra começa no início do trecho e a
    última termina no fim; as fronteiras de dentro vêm do whisper, esticadas linearmente para caber."""
    raw = json.loads((WORK / "palavras-small.json").read_text(encoding="utf-8"))
    loc = {}
    for f, txt in TEXTO.items():
        toks = txt.split()
        ws = []
        for w in raw[str(f)]["words"]:                     # "sexta" + "-feira" → "sexta-feira"
            if w["w"].startswith("-") and ws:
                ws[-1] = {"w": ws[-1]["w"] + w["w"], "s": ws[-1]["s"], "e": w["e"]}
            else:
                ws.append(dict(w))
        wn = [WHISPER_FIX.get(_norm(w["w"]), _norm(w["w"])) for w in ws]
        tn = [_norm(x) for x in toks]
        se = [None] * len(toks)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wn, tn, autojunk=False).get_opcodes():
            if op == "equal":
                for k in range(i2 - i1):
                    se[j1 + k] = (ws[i1 + k]["s"], ws[i1 + k]["e"])
            elif op in ("replace", "insert"):
                if op == "replace":
                    a, b = ws[i1]["s"], ws[i2 - 1]["e"]
                else:                                       # palavra que o whisper não ouviu: divide a anterior
                    a = ws[i1 - 1]["s"] if i1 > 0 else 0.0
                    b = ws[i1 - 1]["e"] if i1 > 0 else ws[0]["s"]
                    if i1 > 0:
                        j1 -= 1
                pesos = [len(tn[j]) + 1 for j in range(j1, j2)]
                acc = a
                for j, pw in zip(range(j1, j2), pesos):
                    nxt = acc + (b - a) * pw / sum(pesos)
                    se[j] = (acc, nxt)
                    acc = nxt
        assert all(x is not None for x in se), f"arquivo {f}: palavra sem tempo"
        assert sum(c for *_, c in TRECHOS[f]) == len(toks), f"contagem no arquivo {f}"
        out, i = [], 0
        for a, b, cnt in TRECHOS[f]:
            inner = [(se[i + k][1] + se[i + k + 1][0]) / 2 for k in range(cnt - 1)]
            m0 = max(a, se[i][0])                           # o whisper adianta o começo de cada arquivo
            m1 = se[i + cnt - 1][1]
            if cnt > 1 and m1 - m0 > 0.05:
                inner = [a + (x - m0) * (b - a) / (m1 - m0) for x in inner]
            bounds = [a] + inner + [b]
            for k in range(1, cnt):                         # pelo menos 60 ms por palavra, em ordem
                bounds[k] = min(max(bounds[k], bounds[k - 1] + 0.06), b - 0.06 * (cnt - k))
            out += [{"w": toks[i + k], "s": round(bounds[k], 3), "e": round(bounds[k + 1], 3)} for k in range(cnt)]
            i += cnt
        loc[str(f)] = out
    (WORK / "palavras-locais.json").write_text(json.dumps(loc, ensure_ascii=False, indent=1), encoding="utf-8")
    for f, fim in FIM_PALAVRA.items():
        loc[str(f)][-1]["e"] = fim()
    out = []
    for i, (f, a, b) in enumerate(PARTS):
        for w in loc[str(f)]:
            if a <= (w["s"] + w["e"]) / 2 < b:
                s, e = max(w["s"], a), min(w["e"], b + _ext(i))
                out.append({"w": w["w"], "s": round(local_final(i, s), 3), "e": round(local_final(i, e), 3)})
    WORDS.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(WORDS, len(out), "palavras")


# ================================================================ utilidades de imagem
def solid(rgb):
    return cached(("solid", rgb), lambda: Image.new("RGB", (W, H), rgb))


def font(size, bold=False):
    return cached(("pil", size, bold), lambda: ImageFont.truetype(
        str(FONTS / ("Poppins-Bold.ttf" if bold else "Poppins-ExtraBold.ttf")), size))


def darken(im, k):
    return im if k >= 0.999 else Image.blend(solid((0, 0, 0)), im, max(k, 0.0))


def fade_alpha(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * max(a, 0))))
    return out


def kf(keys, t):
    """Valor no instante t a partir de chaves [(t, valor)], com smoothstep entre elas (valor: número ou tupla)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(a, tuple):
                return tuple(lerp(p, q, u) for p, q in zip(a, b))
            return lerp(a, b, u)
    return keys[-1][1]


def spaced_text(text, size, fill, stroke=0, stroke_fill=INK, spacing=3, bold=True):
    """Texto com espaçamento entre letras (como o letter-spacing do SVG) → RGBA justo."""
    f = font(size, bold)
    pad = stroke + 4
    wdt = sum(f.getlength(ch) + spacing for ch in text) - spacing + 2 * pad
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(math.ceil(wdt)), asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for ch in text:
        d.text((x, pad), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += f.getlength(ch) + spacing
    return im


# ================================================================ o mapa
ANC = (540, 760)          # onde o centro da vista cai na tela (na vista que acompanha, é perto da ponta)


def mj():
    return cached("mapjson", lambda: json.loads((MAPS / "ep3-camadas.json").read_text(encoding="utf-8")))


def nivel(nome, f=1):
    """A base de um nível (RGB), reduzida f vezes (1, 2 ou 4) para os zooms abertos."""
    def load():
        info = next(n for n in mj()["niveis"] if n["nome"] == nome)
        im = Image.open(MAPS / info["arquivo"]).convert("RGB")
        return im if f == 1 else nivel(nome, f // 2).reduce(2)
    return cached(("nivel", nome, f), load)


ROTA_L = None


def rota_arc():
    return mj()["acc"]


def rota_pt(d):
    """Ponto (m) da rota a d metros do início e a direção (unitária) do trecho."""
    pts, acc = mj()["rota"], rota_arc()
    d = min(max(d, 0.0), acc[-1])
    i = max(j for j in range(len(acc) - 1) if acc[j] <= d + 1e-9)
    i = min(i, len(acc) - 2)
    u = (d - acc[i]) / max(acc[i + 1] - acc[i], 1e-9)
    (x1, y1), (x2, y2) = pts[i], pts[i + 1]
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    return (x1 + (x2 - x1) * u, y1 + (y2 - y1) * u), ((x2 - x1) / L, (y2 - y1) / L)


def rota_suave(d):
    """O centro da vista que acompanha a ponta: a média da rota entre 140 m antes e 40 m depois de d (sem
    tranco nas esquinas)."""
    ps = [rota_pt(d + u)[0] for u in np.linspace(-140, 40, 13)]
    return (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))


def m2s(v, x, y):
    cx, cy, k = v
    return ANC[0] + (x - cx) * k, ANC[1] + (y - cy) * k


def _amostra(nome, v):
    """A vista v = (cx, cy, k) recortada de um nível: a parte que cai dentro da imagem é reamostrada (com
    filtro) e o resto fica ink."""
    info = next(n for n in mj()["niveis"] if n["nome"] == nome)
    s, (lax, lay) = info["s"], info["anchor"]
    cx, cy, k = v
    f = 1
    while f < 4 and s / (2 * f) >= k:
        f *= 2
    im = nivel(nome, f)
    sf = s / f
    bx0 = (lax + (cx - ANC[0] / k) * s) / f
    by0 = (lay + (cy - ANC[1] / k) * s) / f
    bw, bh = W / k * sf, H / k * sf
    bx1, by1 = bx0 + bw, by0 + bh
    ix0, iy0, ix1, iy1 = max(bx0, 0), max(by0, 0), min(bx1, im.width), min(by1, im.height)
    if ix0 <= 0 and iy0 <= 0 and ix1 >= im.width and iy1 >= im.height and False:
        pass
    if bx0 >= 0 and by0 >= 0 and bx1 <= im.width and by1 <= im.height:
        return im.resize((W, H), Image.BICUBIC, box=(bx0, by0, bx1, by1), reducing_gap=2.0)
    out = solid(INK).copy()
    if ix1 <= ix0 or iy1 <= iy0:
        return out
    tx0, ty0 = (ix0 - bx0) / bw * W, (iy0 - by0) / bh * H
    tx1, ty1 = (ix1 - bx0) / bw * W, (iy1 - by0) / bh * H
    sw, sh = max(1, round(tx1) - round(tx0)), max(1, round(ty1) - round(ty0))
    out.paste(im.resize((sw, sh), Image.BICUBIC, box=(ix0, iy0, ix1, iy1), reducing_gap=2.0), (round(tx0), round(ty0)))
    return out


def base_mapa(v):
    """A base na vista v: o nível "perto" nas vistas próximas, "meio" nas abertas e "cidade" na cidade inteira,
    com uma mistura curta entre um e outro (sem salto)."""
    k = v[2]
    if k >= 0.66:
        return _amostra("perto", v)
    if k >= 0.58:
        return Image.blend(_amostra("meio", v), _amostra("perto", v), (k - 0.58) / 0.08)
    if k >= 0.19:
        return _amostra("meio", v)
    if k >= 0.16:
        return Image.blend(_amostra("cidade", v), _amostra("meio", v), (k - 0.16) / 0.03)
    return _amostra("cidade", v)


def rota_largura(k):
    """Espessura da linha (px): 14 na vista próxima (como nos Ep. 1 e 2), mais fina nas vistas abertas."""
    return 14.0 * min(1.0, max(0.5, (k / 1.3) ** 0.6))


def desenha_rota(fr, v, d, ponta=True):
    """A rota rosa (com brilho) revelada até d metros: o começo em cream (a esquina da fuga) e a ponta em rosa.
    Desenhada a 2x e reduzida (borda macia)."""
    pts, acc = mj()["rota"], rota_arc()
    d = min(d, acc[-1])
    ps = [p for p, a in zip(pts, acc) if a < d] + [rota_pt(d)[0]]
    xy = [m2s(v, *p) for p in ps]
    w = rota_largura(v[2])
    # brilho: a linha 2,2x mais grossa, borrada, a 55%
    glow = Image.new("L", (W, H), 0)
    dg = ImageDraw.Draw(glow)
    dg.line(xy, fill=255, width=max(1, round(w * 2.2)), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(10)).point(lambda a: int(a * 0.55))
    fr.paste(Image.new("RGB", (W, H), PINK), (0, 0), glow)
    ss = 2
    lay = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    xy2 = [(x * ss, y * ss) for x, y in xy]
    if len(xy2) > 1:
        dl.line(xy2, fill=PINK + (255,), width=round(w * ss), joint="curve")
    r0 = w * 1.05 * ss
    x0, y0 = xy2[0]
    dl.ellipse((x0 - r0, y0 - r0, x0 + r0, y0 + r0), fill=CREAM + (255,), outline=PINK + (255,), width=round(4.5 * ss))
    if ponta:
        r1 = w * 0.75 * ss
        x1, y1 = xy2[-1]
        dl.ellipse((x1 - r1, y1 - r1, x1 + r1, y1 + r1), fill=PINK + (255,))
    lay = lay.resize((W, H), Image.LANCZOS)
    fr.paste(lay, (0, 0), lay)


def chip_img(text, size=34):
    """A etiqueta do horário na ponta da linha: caixa lilás, texto ink (como os chips das câmeras)."""
    def make():
        f = font(size)
        x0, y0, x1, y1 = f.getbbox(text)
        padx, pady = 16, 11
        cap = f.getbbox("H")
        wb, hb = x1 - x0 + 2 * padx, (cap[3] - cap[1]) + 2 * pady
        im = Image.new("RGBA", (wb + 12, hb + 12), (0, 0, 0, 0))
        sh = Image.new("L", im.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle((6, 9, 6 + wb, 9 + hb), 10, fill=150)
        im.putalpha(sh.filter(ImageFilter.GaussianBlur(3)))
        im = Image.composite(Image.new("RGBA", im.size, INK + (255,)), im, sh.filter(ImageFilter.GaussianBlur(3)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((6, 6, 6 + wb, 6 + hb), 10, fill=LILAC + (255,))
        d.text((6 + padx - x0, 6 + pady - cap[1]), text, font=f, fill=INK + (255,))
        return im
    return cached(("chip", text, size), make)


def rotulo_img(texto, aceso):
    """O nome de uma rua girado no ângulo dela: cream com contorno ink (como nos mapas do mapa.py); aceso, com
    um brilho lilás por trás."""
    def make():
        im = spaced_text(texto, 29, CREAM + (255,), stroke=4, spacing=3)
        if aceso:
            m = im.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda a: min(255, int(a * 1.6)))
            gl = Image.new("RGBA", im.size, LILAC + (0,))
            gl.putalpha(m)
            gl.alpha_composite(im)
            im = gl
        return im
    return cached(("rot", texto, aceso), make)


def desenha_rotulos(fr, v, estados, t):
    """estados: {chave: (opacidade, t_aceso)}. O nome de cada rua aparece quando a Isabela fala o nome, com um
    brilho lilás que se apaga devagar (o nome fica a 90%). Um t_aceso de antes do plano = nome já aceso."""
    for r in mj()["rotulos"]:
        if r["chave"] not in estados:
            continue
        op, t_on = estados[r["chave"]]
        if op <= 0.01 or t_on is None or t < t_on:
            continue
        ang = r["ang"]
        X, Y = m2s(v, r["x"], r["y"])
        if r["lado"]:
            th = math.radians(ang)
            X, Y = X - math.sin(th) * 36 * r["lado"], Y + math.cos(th) * 36 * r["lado"]
        if X < -300 or X > W + 300 or Y < -300 or Y > H + 300:
            continue
        lit = ease((t - t_on) / 0.25)
        brilho = max(0.0, 1 - max(0.0, t - t_on - 0.4) / 1.4) * lit
        base = cached(("rotb", r["chave"]), lambda: rotulo_img(r["texto"], False).rotate(-ang, resample=Image.BICUBIC, expand=True))
        a = op * 0.92 * lit
        fr.paste(fade_alpha(base, a), (round(X - base.width / 2), round(Y - base.height / 2)), fade_alpha(base, a))
        if brilho > 0.01:
            gl = cached(("rotg", r["chave"]), lambda: rotulo_img(r["texto"], True).rotate(-ang, resample=Image.BICUBIC, expand=True))
            fr.paste(fade_alpha(gl, op * brilho), (round(X - gl.width / 2), round(Y - gl.height / 2)), fade_alpha(gl, op * brilho))


def rotulos_na_tela(o, v, t):
    """Os nomes de rua visíveis no instante t: [(X, Y, ângulo, meia-largura, meia-altura)] (o retângulo do texto,
    sem a margem transparente da imagem)."""
    out = []
    rop = kf(o["rot_op"], t) if "rot_op" in o else 1.0
    for r in mj()["rotulos"]:
        t_on = o.get("rotulos", {}).get(r["chave"])
        if t_on is None or t < t_on or rop <= 0.01:
            continue
        X, Y = m2s(v, r["x"], r["y"])
        if r["lado"]:
            th = math.radians(r["ang"])
            X, Y = X - math.sin(th) * 36 * r["lado"], Y + math.cos(th) * 36 * r["lado"]
        bx = cached(("rotbox", r["chave"]), lambda: rotulo_img(r["texto"], False).getchannel("A").point(
            lambda a: 255 if a > 60 else 0).getbbox())
        out.append((X, Y, r["ang"], (bx[2] - bx[0]) / 2, (bx[3] - bx[1]) / 2))
    return out


def _dist_ret(px, py, cx, cy, hw, hh):
    """Distância de pontos (arrays) a um retângulo alinhado (centro cx, cy; meias medidas hw, hh)."""
    return np.hypot(np.maximum(np.abs(px - cx) - hw, 0), np.maximum(np.abs(py - cy) - hh, 0))


HORA_ANG = np.radians(np.arange(0, 360, 15))     # posições candidatas da etiqueta em volta da ponta


def hora_trajeto(o, t0, t1):
    """Onde vai a etiqueta do horário em cada quadro do plano: o ângulo (em volta da ponta da linha) que não encosta
    na linha nem num nome de rua (folga de 8 px) e fica fora das legendas, preferindo o lado de sempre (o lado
    `hora_lado` da linha) e mudando o mínimo de um quadro para o outro (programação dinâmica). Devolve (instantes,
    ângulos), já suavizados."""
    def make():
        ts = np.arange(t0, t1 + 1e-6, 1 / FPS)
        im = chip_img("08H44")
        hw, hh = im.width / 2 - 6, im.height / 2 - 6
        lado = o.get("hora_lado", 1)
        custos, geo = [], []

        def bate(g, th):
            """A etiqueta no ângulo th encosta na linha ou num nome de rua?"""
            X, Y, lx, ly, wl, rx, ry = g
            ux, uy = math.cos(th), math.sin(th)
            off = 26 + (hw + 6) * abs(ux) + (hh + 6) * abs(uy)
            cx, cy = X + ux * off, Y + uy * off
            return (np.min(_dist_ret(lx, ly, cx, cy, hw, hh)) < wl
                    or (len(rx) and np.min(_dist_ret(rx, ry, cx, cy, hw, hh)) < 8)), cx, cy
        for t in ts:
            d = o["d"](t) if callable(o["d"]) else kf(o["d"], t)
            v = vista_em(o["vista"], t, d)
            (x, y), _ = rota_pt(d)
            X, Y = m2s(v, x, y)
            # a linha já desenhada, em pontos a cada ~3 px
            pts, acc = mj()["rota"], rota_arc()
            ps = [m2s(v, *p) for p, a in zip(pts, acc) if a < d] + [(X, Y)]
            lx, ly = [], []
            for (x1, y1), (x2, y2) in zip(ps, ps[1:]):
                n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 3))
                lx.append(np.linspace(x1, x2, n))
                ly.append(np.linspace(y1, y2, n))
            lx = np.concatenate(lx) if lx else np.array([X])
            ly = np.concatenate(ly) if ly else np.array([Y])
            wl = rota_largura(v[2]) / 2 + 8
            # os nomes de rua, em pontos (o contorno e o meio)
            rx, ry = [], []
            for RX, RY, ang, rw, rh in rotulos_na_tela(o, v, t):
                a = math.radians(ang)
                us, vs = np.meshgrid(np.linspace(-rw, rw, 40), np.linspace(-rh, rh, 5))
                rx.append(RX + us.ravel() * math.cos(a) - vs.ravel() * math.sin(a))
                ry.append(RY + us.ravel() * math.sin(a) + vs.ravel() * math.cos(a))
            rx = np.concatenate(rx) if rx else np.zeros(0)
            ry = np.concatenate(ry) if ry else np.zeros(0)
            # o lado de sempre: perpendicular à direção dos últimos 80 m, no lado `lado`
            (xa, ya), _ = rota_pt(d - 80)
            dx, dy = x - xa, y - ya
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            if nx * lado < 0 or (abs(nx) < 0.2 and ny > 0):
                nx, ny = -nx, -ny
            pref = math.atan2(ny, nx)
            g = (X, Y, lx, ly, wl, rx, ry)
            geo.append(g)
            c = []
            for th in HORA_ANG:
                colide, cx, cy = bate(g, th)
                k = 1000.0 if colide else 0.0
                if cy + hh > 1120 or cy - hh < 300 or cx - hw < 20 or cx + hw > W - 20:   # legendas, contador, bordas
                    k += 300
                dang = abs((th - pref + math.pi) % (2 * math.pi) - math.pi)
                c.append(k + 20 * dang)
            custos.append(c)
        custos = np.array(custos)
        n, m = custos.shape
        # programação dinâmica: custo de mudar de ângulo entre quadros vizinhos (proporcional ao salto)
        dif = np.abs((HORA_ANG[:, None] - HORA_ANG[None, :] + math.pi) % (2 * math.pi) - math.pi)
        troca = 60 * dif
        acum, de = custos[0].copy(), np.zeros((n, m), int)
        for i in range(1, n):
            tot = acum[:, None] + troca
            de[i] = np.argmin(tot, axis=0)
            acum = tot[de[i], np.arange(m)] + custos[i]
        idx = [int(np.argmin(acum))]
        for i in range(n - 1, 0, -1):
            idx.append(int(de[i][idx[-1]]))
        idx.reverse()
        bruto = np.unwrap(HORA_ANG[idx])
        k = np.exp(-0.5 * (np.arange(-4, 5) / 2.0) ** 2)            # suaviza (~0,07 s) sem atraso
        k /= k.sum()
        ang = np.convolve(np.pad(bruto, 4, mode="edge"), k, "valid")
        for i, g in enumerate(geo):                                  # onde a suavização encosta, fica o ângulo escolhido
            if bate(g, ang[i])[0] and not bate(g, bruto[i])[0]:
                ang[i] = bruto[i]
        return ts, ang
    return cached(("hora", round(t0, 3)), make)


def desenha_hora(fr, v, d, texto, t_troca, t, ang):
    """O horário da última câmera vista, preso à ponta da linha no ângulo `ang` (hora_trajeto), com um tranco
    quando muda."""
    if not texto:
        return
    (x, y), _ = rota_pt(d)
    X, Y = m2s(v, x, y)
    im = chip_img(texto)
    u = (t - t_troca) / 0.22
    s = 1.0 if u >= 1 or u < 0 else 1.0 + 0.25 * (1 - ease(u))
    a = 1.0 if u >= 1 else max(0.0, min(1.0, u * 2.5)) if u >= 0 else 1.0
    if abs(s - 1) > 1e-3:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.BICUBIC)
    nx, ny = math.cos(ang), math.sin(ang)
    off = 26 + im.width / 2 * abs(nx) + im.height / 2 * abs(ny)
    cxp, cyp = X + nx * off, Y + ny * off
    fr.paste(fade_alpha(im, a), (round(cxp - im.width / 2), round(cyp - im.height / 2)), fade_alpha(im, a))


def desenha_interrogacao(fr, v, t_in, t, a=1.0):
    """O "?" lilás da série, logo depois do fim da Teixeira Soares, no prolongamento do último trecho."""
    if t < t_in or a <= 0.01:
        return
    q = cached("q", lambda: spaced_text("?", 190, LILAC + (255,), spacing=0, bold=False))
    (x, y), (dx, dy) = rota_pt(mj()["acc"][-1])
    X, Y = m2s(v, x, y)
    u = (t - t_in) / 0.35
    pop_ = 1.0 if u >= 1 else 0.6 + 0.4 * ease(u) + 0.12 * math.sin(math.pi * min(u, 1))
    qq = q.resize((max(1, round(q.width * pop_ * 0.8)), max(1, round(q.height * pop_ * 0.8))), Image.BICUBIC)
    cx, cy = X + dx * 80, Y + dy * 80 + 12
    al = a * min(1.0, (t - t_in) / 0.12)
    fr.paste(fade_alpha(qq, al), (round(cx - qq.width / 2), round(cy - qq.height / 2)), fade_alpha(qq, al))


def desenha_menino_deus(fr, v, t_in, t):
    """O Instituto Menino Deus: ponto lilás com brilho e o nome embaixo, acendendo em t_in."""
    if t < t_in:
        return
    u = (t - t_in) / 0.45
    a = min(1.0, u * 2.0)
    s = 1.0 if u >= 1 else 0.5 + 0.5 * ease(u) + 0.15 * math.sin(math.pi * min(u, 1))
    X, Y = m2s(v, *mj()["menino_deus"])

    def make():
        ss, R = 4, 70
        m = Image.new("L", (2 * R * ss, 2 * R * ss), 0)
        ImageDraw.Draw(m).ellipse(((R - 44) * ss, (R - 44) * ss, (R + 44) * ss, (R + 44) * ss), fill=255)
        glow = m.resize((2 * R, 2 * R), Image.LANCZOS).filter(ImageFilter.GaussianBlur(12)).point(lambda x: int(x * 0.45))
        dot = Image.new("L", (2 * R * ss, 2 * R * ss), 0)
        ImageDraw.Draw(dot).ellipse(((R - 16) * ss, (R - 16) * ss, (R + 16) * ss, (R + 16) * ss), fill=255)
        dot = dot.resize((2 * R, 2 * R), Image.LANCZOS)
        lay = Image.new("RGBA", (2 * R, 2 * R), LILAC + (0,))
        lay.putalpha(Image.fromarray(np.maximum(np.asarray(glow), np.asarray(dot))))
        return lay
    mk = cached("md", make)
    mk2 = mk.resize((round(mk.width * s), round(mk.height * s)), Image.BICUBIC) if abs(s - 1) > 1e-3 else mk
    fr.paste(fade_alpha(mk2, a), (round(X - mk2.width / 2), round(Y - mk2.height / 2)), fade_alpha(mk2, a))
    nome = cached("mdnome", lambda: spaced_text("INSTITUTO MENINO DEUS", 30, LILAC + (255,), stroke=4, spacing=3))
    an = max(0.0, min(1.0, (t - t_in - 0.12) / 0.3))
    fr.paste(fade_alpha(nome, an), (round(X - nome.width / 2), round(Y + 40)), fade_alpha(nome, an))


def credito(fr):
    c = cached("cred", lambda: spaced_text("© OpenStreetMap", 16, MUTED + (190,), spacing=0, bold=True))
    fr.paste(c, (W - 24 - c.width, H - 24 - c.height), c)


def vista_de(spec, d):
    """Uma chave de vista em (cx, cy, k): ("segue", k) acompanha a ponta; ("fixa", cx, cy, k) é parada."""
    if spec[0] == "segue":
        cx, cy = rota_suave(d)
        return cx, cy + spec[2] if len(spec) > 2 else cy, spec[1]
    return spec[1], spec[2], spec[3]


def vista_em(keys, t, d):
    """Interpola as chaves de vista [(t, spec)] no instante t (o zoom em escala logarítmica)."""
    if t <= keys[0][0] or len(keys) == 1:
        return vista_de(keys[0][1], d)
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / max(t1 - t0, 1e-6))
            va, vb = vista_de(a, d), vista_de(b, d)
            return (lerp(va[0], vb[0], u), lerp(va[1], vb[1], u), math.exp(lerp(math.log(va[2]), math.log(vb[2]), u)))
    return vista_de(keys[-1][1], d)


def f_mapa(o, t, t0, t1):
    """Um plano de mapa. o: "d" [(t, metros)] da linha revelada; "vista" [(t, spec)]; "hora" [(t, texto)] da
    ponta; "rotulos" {chave: t_aceso ou None}; "rot_op" [(t, opacidade)] dos nomes; "q" (t_in, t_out) do "?";
    "md" t do Instituto; "escuro" [(t, quanto)] (o mapa escurece sob os números grandes)."""
    d = o["d"](t) if callable(o["d"]) else kf(o["d"], t)
    v = vista_em(o["vista"], t, d)
    fr = base_mapa(v)
    esc = kf(o["escuro"], t) if "escuro" in o else 0.0
    rop = kf(o["rot_op"], t) if "rot_op" in o else 1.0
    if "rotulos" in o and rop > 0.01:
        desenha_rotulos(fr, v, {k: (rop, tt) for k, tt in o["rotulos"].items() if tt is not None}, t)
    desenha_rota(fr, v, d, ponta=o.get("ponta", True))
    if "hora" in o:
        hs = [h for h in o["hora"] if h[0] <= t]
        if hs:
            ts_, angs = hora_trajeto(o, t0, t1)
            desenha_hora(fr, v, d, hs[-1][1], hs[-1][0], t, float(np.interp(t, ts_, angs)))
    if "q" in o:
        qi, qo = o["q"]
        desenha_interrogacao(fr, v, qi, t, a=1.0 - ease((t - qo) / 0.4) if qo else 1.0)
    if "md" in o:
        desenha_menino_deus(fr, v, o["md"], t)
    credito(fr)
    if esc > 0.005:
        fr = Image.blend(fr, solid(INK), esc)
    return grad_top(fr, 0.75, 560) if o.get("topo", True) else fr


# ================================================================ planos: câmeras de segurança em cartão
def cam_base(key):
    """Fundo ink com a sombra do cartão e a máscara de cantos arredondados."""
    def make():
        vw, vh, vx, vy = vista(key)
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
    """O círculo lilás (traço de 7 px, raio r em px da tela) com um contorno ink a 40% por fora (4 px, borda
    macia), para destacar tanto no fundo claro (camera1) quanto no escuro (camera9)."""
    def make():
        ss, size = 4, int(2 * r + 40)
        c = size * ss / 2

        def anel(r0, r1):
            m = Image.new("L", (size * ss, size * ss), 0)
            d = ImageDraw.Draw(m)
            d.ellipse((c - r1 * ss, c - r1 * ss, c + r1 * ss, c + r1 * ss), fill=255)
            d.ellipse((c - r0 * ss, c - r0 * ss, c + r0 * ss, c + r0 * ss), fill=0)
            return m.resize((size, size), Image.LANCZOS)
        lil = anel(r - 3.5, r + 3.5)                                  # o traço lilás (7 px)
        ink = anel(r + 3.5, r + 7.5).filter(ImageFilter.GaussianBlur(0.8)).point(lambda v: int(v * 0.40))
        lay = Image.new("RGBA", (size, size), INK + (0,))
        lay.putalpha(ink)
        top = Image.new("RGBA", (size, size), LILAC + (0,))
        top.putalpha(lil)
        lay.alpha_composite(top)
        return lay
    return cached(("ring", r), make)


def cam_track(key):
    """A trilha da Zoe suavizada (média móvel de 3 pontos), numa grade fina."""
    def make():
        tr = np.array(CAMS[key]["trilha"], float)
        ts = np.linspace(tr[0, 0], tr[-1, 0], 200)
        k = np.ones(3) / 3
        xs = np.interp(ts, tr[:, 0], np.convolve(np.pad(tr[:, 1], 1, mode="edge"), k, "valid"))
        ys = np.interp(ts, tr[:, 0], np.convolve(np.pad(tr[:, 2], 1, mode="edge"), k, "valid"))
        return ts, xs, ys
    return cached(("track", key), make)


def her(key, s):
    ts, xs, ys = cam_track(key)
    return float(np.interp(s, ts, xs)), float(np.interp(s, ts, ys))


def f_cam(o, t, t0, t1):
    """Câmera de segurança em cartão: velocidade (cam_time), janela (janela_A) e, onde ela é pequena demais, o
    círculo lilás acompanhando (anel_ativo). Entra e sai num corte seco, como no Ep. 2."""
    key = o["cam"]
    c = CAMS[key]
    s = cam_time(c, t - t0)
    if c.get("reverso"):                       # o trecho de trás para a frente (o DVR estava rebobinando)
        s = c["ss"] + c["se"] - s
    base, mask, (bx, by) = cam_base(key)
    fr = base.copy()
    fr.paste(cam_card(key, s), (bx, by), mask)
    if anel_ativo(key):
        tr = c["trilha"]
        a = ease((s - tr[0][0]) / 0.12) * (1 - ease((s - tr[-1][0] + 0.05) / 0.2))
        if a > 0:
            hx, hy = her(key, min(max(s, tr[0][0]), tr[-1][0]))
            u, v, _ = janela_A(key, s) @ np.array([hx, hy, 1.0])
            X, Y = bx + u, by + v
            ring = ring_img(c["anel"])
            lay = Image.new("RGBA", (W, H))
            lay.alpha_composite(fade_alpha(ring, a), (round(X - ring.width / 2), round(Y - ring.height / 2)))
            clip = Image.new("L", (W, H), 0)
            clip.paste(mask, (bx, by))
            lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel("A")), np.asarray(clip))))
            fr = fr.convert("RGBA")
            fr.alpha_composite(lay)
            fr = fr.convert("RGB")
    if o.get("fade"):
        fr = darken(fr, ease((t - t0) / o["fade"]))
    return fr


# ================================================================ planos: prints em cartão
# chave → (arquivo, recorte, caixas a borrar (px do original), largura na tela, centro, rotação)
CARDS = {
    # Street Views com a câmera circulada à mão (qua 23/09, 13h33 e 13h42): sem a barra do celular, o selo
    # do Google, o botão de ampliar, as setas de navegação e o "Voltar para o trajeto"
    "sv98": (D6 / "IMG-20260923-WA0098.jpg", (0, 215, 1080, 995), [], 840, (520, 790), 0.8),
    "sv106": (D6 / "IMG-20260923-WA0106.jpg", (0, 170, 591, 895), [], 540, (530, 760), -1.0),
    # o satélite com o Instituto e as áreas de mato circuladas (foto da tela do notebook): sem a barra de
    # tarefas do Windows, a barra de abas do topo, o botão "Camadas" e os marcadores da borda direita
    "sat": (D6 / "img maps menino deus", (55, 48, 1525, 858), [], 1000, (540, 800), -0.8),
}
CARD_Z = (1.0, 1.04)  # zoom lento e contínuo em cada print
XF = 0.3              # crossfade entre um print e o próximo


def blur_boxes(im, boxes):
    for b in boxes:
        reg = im.crop(b)
        for _ in range(3):
            reg = reg.filter(ImageFilter.BoxBlur(20))
        im.paste(reg, b[:2])
    return im


def place(layer, cx, cy, s, rot=0.0):
    """Camada RGBA na tela: escala s, rotação rot (graus) e centro (cx, cy) → RGBA WxH."""
    lw, lh = layer.size
    th = math.radians(rot)
    c, sn = math.cos(th) / s, math.sin(th) / s
    return layer.transform((W, H), Image.AFFINE,
                           (c, sn, lw / 2 - c * cx - sn * cy, -sn, c, lh / 2 + sn * cx - c * cy),
                           resample=Image.BICUBIC)


def card_layer(key):
    def make():
        from PIL import ImageOps
        path, crop, boxes, dw, _, _ = CARDS[key]
        im = blur_boxes(ImageOps.exif_transpose(Image.open(path)).convert("RGB"), boxes)
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
    _, _, _, _, (cx, cy), rot = CARDS[key]
    fr = solid(INK).convert("RGBA")
    fr.alpha_composite(place(card_layer(key), cx, cy, z, rot))
    return fr.convert("RGB")


def f_cartao(o, t, t0, t1):
    """Um print por vez, com um zoom lento e contínuo (CARD_Z). `xf` = (cartão, início, fim) do plano anterior,
    que sai num crossfade de XF s continuando o próprio zoom."""
    fr = card_frame(o["card"], lerp(*CARD_Z, (t - t0) / (t1 - t0)))
    if "xf" in o and t - t0 < XF:
        key, p0, p1 = o["xf"]
        fr = Image.blend(card_frame(key, lerp(*CARD_Z, (t - p0) / (p1 - p0))), fr, ease((t - t0) / XF))
    return fr


def f_ink(o, t, t0, t1):
    return solid(INK)


# ================================================================ planos: o fecho (a primeira noite em casa)
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
        self.p.stdout.read()
        self.p.stdout.close()
        self.p.wait()


# IMG_8337 (24/09, 23h56): a primeira noite em casa. A Zoe deitada no bichinho de pelúcia, coberta pela manta rosa,
# de frente, com o rosto em pé, olhando para a câmera: de 29,05 s (logo depois que o celular se aproxima) até 31,85 s
# (os olhos abertos até ~30,3 s; depois ela vai fechando os olhos, com sono). O Reel 01 usou de 22,0 a 24,8 s.
# O celular está na mão: a tremida rápida sai por estabilização (semelhança SIFT até o quadro de 30,0 s, suavizada
# em 0,3 s; só a diferença é corrigida, o movimento lento fica) e o zoom esconde as bordas.
HOJE = SET / "IMG_8337.MOV"
HOJE_SS = 29.05
HOJE_REF = 30.00
HOJE_SUAVE = 9          # quadros (sigma da gaussiana do caminho suavizado)
# o rosto está no alto do quadro original (os olhos em y ≈ 210): a imagem desce HOJE_DESCE px e o topo fica sob um
# degradê ink (opaco até HOJE_TOPO, some em HOJE_TOPO_FIM); abaixo de HOJE_TOPO a imagem é sempre válida
HOJE_TOPO, HOJE_TOPO_FIM = 225, 400
HOJE_OLHOS = 210        # altura dos olhos no quadro de referência (px de 1080x1920), para conferir


def hoje_estab():
    """(matrizes 2x3 por quadro, zoom): a correção de cada quadro do fecho (em 1080x1920) e o menor zoom que
    esconde as bordas em todos os quadros. Cache em WORK."""
    def make():
        import cv2   # noqa: E402
        n = int(round(FECHO * FPS)) + 2
        sig = f"{HOJE.name}|{HOJE_SS}|{n}|{HOJE_REF}|{HOJE_SUAVE}|{HOJE_TOPO}"
        cache = WORK / "estab-fecho.npz"
        if cache.exists():
            z = np.load(cache, allow_pickle=False)
            if str(z["sig"]) == sig:
                return z["A"], float(z["zoom"])
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{HOJE_SS:.3f}", "-i", str(HOJE), "-vf",
                              f"fps={FPS},scale=540:960,format=gray", "-frames:v", str(n), "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        g = np.frombuffer(raw, np.uint8).reshape(-1, 960, 540)
        ref = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{HOJE_REF:.3f}", "-i", str(HOJE), "-vf",
                              "scale=540:960,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        ref = np.frombuffer(ref, np.uint8).reshape(960, 540)
        sift = cv2.SIFT_create(3000)
        fl = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
        mask = np.zeros((960, 540), np.uint8)
        mask[:560] = 255                                   # o rosto (a manta e a pelúcia embaixo se mexem)
        kr, dr = sift.detectAndCompute(ref, mask)
        par = []
        for f in g:
            k, d = sift.detectAndCompute(f, mask)
            m = [a for a, b in fl.knnMatch(d, dr, k=2) if a.distance < 0.7 * b.distance]
            A_ = np.float32([k[x.queryIdx].pt for x in m])
            B_ = np.float32([kr[x.trainIdx].pt for x in m])
            M, _ = cv2.estimateAffinePartial2D(A_, B_, method=cv2.RANSAC, ransacReprojThreshold=2.0)
            sc, rot = math.hypot(M[0, 0], M[1, 0]), math.atan2(M[1, 0], M[0, 0])
            par.append((M[0, 2] * 2, M[1, 2] * 2, math.log(sc), rot))   # translação em px de 1080x1920
        par = np.array(par)
        k = np.exp(-0.5 * (np.arange(-3 * HOJE_SUAVE, 3 * HOJE_SUAVE + 1) / HOJE_SUAVE) ** 2)
        k /= k.sum()
        suave = np.stack([np.convolve(np.pad(par[:, j], len(k) // 2, mode="edge"), k, "valid") for j in range(4)], 1)

        def mat(tx, ty, ls, r):
            sc = math.exp(ls)
            return np.array([[sc * math.cos(r), -sc * math.sin(r), tx], [sc * math.sin(r), sc * math.cos(r), ty],
                             [0, 0, 1.0]])
        corr = [np.linalg.inv(mat(*b)) @ mat(*a) for a, b in zip(par, suave)]     # quadro → caminho suavizado
        cantos = np.array([[0, HOJE_TOPO, 1], [W, HOJE_TOPO, 1], [W, H, 1], [0, H, 1]], float).T

        def Zm(zoom, desce):
            """zoom centrado na horizontal; a imagem desce `desce` px."""
            return np.array([[zoom, 0, W / 2 - zoom * W / 2], [0, zoom, desce], [0, 0, 1.0]])

        def valido(Z):
            for C in corr:
                q = np.linalg.inv(Z @ C) @ cantos
                if q[0].min() < 2 or q[1].min() < 2 or q[0].max() > W - 2 or q[1].max() > H - 2:
                    return False
            return True
        # o menor zoom que deixa a imagem descer o máximo possível (até 260 px)
        melhor = None
        for zoom in np.arange(1.04, 1.40, 0.01):
            for desce in range(260, -1, -10):
                if valido(Zm(zoom, desce)):
                    break
            else:
                continue
            if melhor is None or desce > melhor[1] + 15:
                melhor = (zoom, desce)
            if desce >= 200:
                break
        zoom, desce = melhor
        A = np.array([(Zm(zoom, desce) @ C)[:2] for C in corr])
        print(f"  estabilização do fecho: zoom {zoom:.2f}, a imagem desce {desce} px (os olhos em y ≈ "
              f"{desce + zoom * HOJE_OLHOS:.0f}); correção máxima {np.abs(par[:, :2] - suave[:, :2]).max():.0f} px")
        np.savez(cache, A=A, zoom=np.array(zoom), sig=np.array(sig))
        return A, float(zoom)
    return cached("hoje_estab", make)


def f_hoje(o, t, t0, t1):
    """Fecho: a Zoe na primeira noite em casa, estabilizada (hoje_estab). Entra saindo do preto."""
    import cv2   # noqa: E402
    if "_rd" not in o:
        o["_rd"] = Reader(HOJE, HOJE_SS + o.get("_off", 0), t1 - t0, W, H, f"scale={W}:{H}:flags=lanczos")
    fr = o["_rd"].read()
    A, _ = hoje_estab()
    i = min(max(int(round((t - t0) * FPS)), 0), len(A) - 1)
    fr = Image.fromarray(cv2.warpAffine(np.asarray(fr), A[i], (W, H), flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE))
    fr = grad_top(fr, 1.0, HOJE_TOPO_FIM, opaco=HOJE_TOPO)
    return darken(fr, ease((t - t0) / o.get("fade", 0.4)))


def grad_top(fr, a0=0.85, y1=700, opaco=0):
    """Degradê ink no topo (a0 de y=0 até `opaco`, caindo até 0 em y1), para dar leitura ao título."""
    def make():
        y = np.arange(H, dtype=float)
        u = np.clip((y - opaco) / (y1 - opaco), 0, 1)
        a = a0 * (1 + np.cos(np.pi * u)) / 2
        lay = np.zeros((H, W, 4), np.uint8)
        lay[..., :3] = INK
        lay[..., 3] = (255 * a).astype(np.uint8)[:, None]
        return Image.fromarray(lay)
    out = fr.convert("RGBA")
    out.alpha_composite(cached(("gradtop", a0, y1, opaco), make))
    return out.convert("RGB")


def f_gancho(o, t, t0, t1):
    return grad_top(f_mapa(dict(o, topo=False), t, t0, t1))


# ================================================================ a montagem (SHOTS)
SEGUE = 1.25                                  # zoom da vista que acompanha a ponta (px por metro)
INTEIRA = ("fixa", 0.0, -53.0, 0.378)         # a rota inteira, entre o título e as legendas (y ≈ 450 a 1090)
TRAVESSIA = ("fixa", -205.0, 150.0, 1.25)     # a travessia da Av. Brasil (P6: "inclusive a avenida principal")
CIDADE = ("fixa", 0.0, 420.0, 0.13)           # a cidade inteira (P7: "muito longe de alcançar ela")
FIM_TEIXEIRA = ("fixa", -150.0, 660.0, 0.90)  # o fim da Teixeira Soares, onde entra o "?" (P8)
VISTA_B = ("fixa", -539.0, 615.0, 0.23)       # a rota e o Instituto Menino Deus (P8), sem linha entre os dois
# a ponta da linha (metros desde a esquina da fuga) depois de cada câmera; de cada uma só se sabe a rua
PONTA = {"c2a": 900, "p3": 1050, "c3": 1150, "c5": 1280, "c7": 1424, "p4": 1853, "c8": 2100}


def passagem(key, s):
    """Instante (na linha do tempo do Reel) em que o arquivo da câmera `key` chega em s."""
    return T[key] + cam_tau(CAMS[key], s)


# o momento mais claro de cada passagem (s do arquivo): o tempo forte da trilha. A da camera1 cai sob a voz
# (P2) e sai mais baixa (o acento fica fora do duck)
PASSAGENS = {"c1": (8.20, 0.45), "c2a": (14.30, 1.0), "c3": (19.85, 1.0), "c4": (26.20, 1.0), "c5": (10.45, 1.0),
             "c6": (3.40, 1.0), "c7": (2.75, 1.0), "c8": (7.45, 1.0)}


def hits():
    """[(instante na linha do tempo, ganho)] dos tempos fortes, em ordem."""
    return sorted((round(passagem(k, s), 3), g) for k, (s, g) in PASSAGENS.items())


def shots():
    """(início, função, opções): cada plano vai até o início do próximo. Os tempos vêm das palavras."""
    L = mj()["acc"][-1]
    d_ep2 = mj()["cruzamentos"]["FIM_EP2"]
    gancho_d0, gancho_t = 110.0, 2.70

    def d_gancho(t):
        u = min(1.0, max(0.0, t / gancho_t))
        return gancho_d0 + (L - gancho_d0) * (1 - (1 - u) ** 1.6)

    m3, ma, mb, m4, m5, m6 = T["m3"], T["ma"], T["mb"], T["m4"], T["m5"], T["m6"]
    t_dobrou, t_chicuta = cue("dobrou") - 0.10, cue("Chicuta,", end=True) - 0.05
    t_av, t_q, t_m, t_s = cue("Avenida Brasil"), cue("Quinze"), cue("Morom"), cue("seguiu")
    t_ts = cue("Teixeira Soares.", end=True)
    t_i, t_reto, t_rua = cue("Independência"), cue("reto,"), cue("rua.", end=True)
    t_inc = cue("inclusive")
    t_seis = cue("seis dias")
    t_longe = cue("A gente estava muito")
    t_lado, t_tinham, t_inst = cue("lado"), cue("Tinham"), cue("Instituto")
    sv2 = cue("a gente foi seguindo") - 0.05
    acesas = {"lavapes": -9.0, "chicuta": -9.0, "brasil": -9.0, "novembro": -9.0, "morom": -9.0, "teixeira": -9.0,
              "independencia": -9.0}       # nomes já acesos (sem o brilho de quando acendem)
    return [
        # gancho (P1) — a rota inteira se desenhando, já em movimento no 1º quadro; 2 KM e 7 MIN no ASS
        (0.0, f_gancho, {"d": d_gancho, "vista": [(0.0, ("fixa", 0.0, -75.0, 0.40)), (P1[0], INTEIRA)]}),
        # cartela DIA 6 · QUA 23/09
        (T["dia6"], f_ink, {}),
        # P2 — "câmera por câmera": os dois Street Views com a câmera circulada à mão, um por vez
        (P0[1], f_cartao, {"card": "sv98"}),
        (sv2, f_cartao, {"card": "sv106", "xf": ("sv98", P0[1], sv2)}),
        # "...sexta-feira de manhã, logo depois que ela fugiu." — a camera1: ela corre lá no alto, atrás do relógio
        (T["c1"], f_cam, {"cam": "c1"}),
        (T["c1b"], f_cam, {"cam": "c1b"}),
        # a CAM 2 da Lava Pés (sem voz): a travessia mais nítida
        (T["c2a"], f_cam, {"cam": "c2a"}),
        # P3 — o mapa parte de onde o Ep. 2 parou; sobe a Lava Pés e dobra na Coronel Chicuta
        (m3, f_mapa, {"d": [(m3, d_ep2), (m3 + 0.15, d_ep2), (m3 + 1.05, PONTA["c2a"]), (t_dobrou, PONTA["c2a"]),
                            (t_chicuta, PONTA["p3"])],
                      "vista": [(m3, ("fixa", 120.0, -600.0, 1.0)), (m3 + 1.15, ("segue", SEGUE))],
                      "hora": [(m3 + 1.05, "08H44")],
                      "rotulos": {"lavapes": cue("Lava"), "chicuta": cue("Coronel")}}),
        # a Coronel Chicuta: câmera, mapa, câmera, mapa
        (T["c3"], f_cam, {"cam": "c3"}),
        (ma, f_mapa, {"d": [(ma, PONTA["p3"]), (ma + 0.08, PONTA["p3"]), (ma + 0.62, PONTA["c3"])],
                      "vista": [(ma, ("segue", SEGUE))], "hora": [(ma + 0.06, "08H45")],
                      "rotulos": {"lavapes": acesas["lavapes"], "chicuta": acesas["chicuta"]}}),
        (T["c4"], f_cam, {"cam": "c4"}),
        (T["c5"], f_cam, {"cam": "c5"}),
        (mb, f_mapa, {"d": [(mb, PONTA["c3"]), (mb + 0.08, PONTA["c3"]), (mb + 0.62, PONTA["c5"])],
                      "vista": [(mb, ("segue", SEGUE))], "hora": [(mb + 0.06, "08H46")],
                      "rotulos": {"chicuta": acesas["chicuta"]}}),
        (T["c6"], f_cam, {"cam": "c6"}),
        (T["c7"], f_cam, {"cam": "c7"}),
        # P4 — atravessa a Avenida Brasil, desce a 15 até a Morom e segue até a Teixeira Soares
        (m4, f_mapa, {"d": [(m4, PONTA["c5"]), (m4 + 0.40, PONTA["c7"]), (t_av + 0.95, 1595), (t_m, 1730),
                            (t_s, 1730), (t_ts - 0.10, PONTA["p4"])],
                      "vista": [(m4, ("segue", SEGUE)), (t_av + 0.2, ("segue", 1.45)), (t_q, ("segue", 1.45)),
                                (t_m, ("segue", SEGUE))],
                      "hora": [(m4, "08H46")],
                      "rotulos": {"chicuta": acesas["chicuta"], "brasil": t_av, "novembro": t_q, "morom": t_m,
                                  "teixeira": cue("Teixeira")}}),
        # a Teixeira Soares (08:50)
        (T["c8"], f_cam, {"cam": "c8"}),
        # P5 — "Dali, ela desceu em direção à Independência e foi reto, até o final da rua."
        (m5, f_mapa, {"d": [(m5, PONTA["p4"]), (t_i + 0.05, 1984), (t_i + 0.55, PONTA["c8"]), (t_reto, PONTA["c8"]),
                            (t_rua - 0.10, L)],
                      "vista": [(m5, ("segue", SEGUE)), (t_reto, ("segue", SEGUE)), (t_rua + 0.3, ("segue", 1.10))],
                      "hora": [(m5 + 0.06, "08H50")], "hora_lado": 1,
                      "rotulos": {"teixeira": acesas["teixeira"], "independencia": t_i}}),
        # P6 — "E a gente ficava abismado vendo aquilo. Como é que nenhum carro pegou ela?": as outras vistas
        (T["c2b"], f_cam, {"cam": "c2b"}),
        (T["c2d"], f_cam, {"cam": "c2d"}),
        # "Foram várias ruas movimentadas, inclusive a avenida principal." → P7 → "muito longe de alcançar ela"
        (m6, f_mapa, {"d": [(m6, L)],
                      "vista": [(m6, INTEIRA), (t_inc - 0.10, INTEIRA), (t_inc + 0.70, TRAVESSIA),
                                (P0[6] - 0.05, TRAVESSIA), (t_seis + 0.10, INTEIRA), (t_longe - 0.05, INTEIRA),
                                (t_longe + 2.10, CIDADE)],
                      "rotulos": {"brasil": cue("avenida principal")},
                      # o nome da avenida some antes do mapa começar a abrir (não encosta na linha ao diminuir)
                      "rot_op": [(t_inc - 0.1, 0.0), (t_inc + 0.4, 1.0), (P0[6] - 0.45, 1.0), (P0[6] - 0.07, 0.0)]}),
        # cartela QUI 24/09 (sem número de dia)
        (T["qui"], f_ink, {}),
        # P8 — o "?" no fim da Teixeira Soares; a ligação; o mapa abre e o Instituto acende (sem linha entre os dois)
        (P0[7], f_mapa, {"d": [(P0[7], L)],
                         "vista": [(P0[7], FIM_TEIXEIRA), (t_tinham - 0.15, FIM_TEIXEIRA), (t_tinham + 1.00, VISTA_B)],
                         "q": (t_lado - 0.05, t_tinham + 0.05), "md": t_inst}),
        # P9 — "E aí, todo o nosso foco foi pra lá.": o satélite com as áreas de mato circuladas
        (P0[8] - 0.05, f_cartao, {"card": "sat"}),
        # spoiler: a câmera do Instituto (qui 24/09)
        (T["c9"], f_cam, {"cam": "c9"}),
        # fecho: a primeira noite em casa
        (T["fecho"], f_hoje, {"fade": 0.4}),
    ]


# ================================================================ texto (ASS)
LIBASS_EM = 0.558      # no libass, o "em" da Poppins é ~0,558 x Fontsize (medido: a maiúscula tem ~0,41)
CAP_Y, CAP_MAXW = 1180, 800        # legendas: centro em x=540, sem entrar nos 130 px da direita
YEL, WHT = r"{\c&H00D7FF&}", r"{\c&HFFFFFF&}"
# contador: 6 segmentos no topo, abaixo da interface do Instagram (y ≈ 230)
SEG_X0, SEG_X1, SEG_Y, SEG_H, SEG_GAP = 130, 950, 252, 10, 14
SEG_W = (SEG_X1 - SEG_X0 - 5 * SEG_GAP) / 6
NUM_Y, NUM_FS = 1395, 230          # os números grandes (2 KM, 7 MIN, 6 DIAS, 10 MIN): abaixo das legendas


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
    return w["w"].rstrip(".,:…?").upper()


# palavras que não devem fechar um bloco: artigos e preposições (peso maior) e outras curtas
SOLTAS = {w: 1.2 for w in ("a", "o", "e", "de", "da", "do", "dos", "na", "no", "pra", "para", "com", "um", "uma",
                           "uns", "as", "os", "se", "em", "por", "pela", "pelas", "às", "à")}
SOLTAS.update({w: 0.4 for w in ("que", "eu", "ia", "já", "não", "só", "mas", "quando", "ela", "era", "até", "foi",
                                "toda", "todo", "nosso")})


def cap_chunks(words):
    """Blocos de até 3 palavras que caibam na largura. Quebra na pontuação e nas pausas da fala e, dentro de
    cada frase, escolhe a divisão com menos blocos, evitando bloco que termina em palavra solta e bloco de uma
    palavra curta."""
    phrases, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if w["w"][-1] in ".,:…?" or (nxt and nxt["s"] - w["e"] > 0.25):
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
        best = [(0.0, [])] + [(math.inf, None)] * n
        for i in range(1, n + 1):
            for k in (1, 2, 3):
                if k <= i and best[i - k][1] is not None:
                    c = cost(ph[i - k:i], i == n)
                    if c is not None and best[i - k][0] + c < best[i][0]:
                        best[i] = (best[i - k][0] + c, best[i - k][1] + [ph[i - k:i]])
        out += best[n][1]
    return out


def CHIPS():
    """As etiquetas de horário dos cartões das câmeras: (entra, sai, texto, x, y). No canto de cima à esquerda
    do cartão; na camera7 à direita (o relógio dela fica à esquerda); na camera1, embaixo (o relógio em close
    fica no alto)."""
    out = []
    for key in ("c1", "c2a", "c3", "c4", "c5", "c6", "c7", "c8", "c2b", "c2d", "c9"):
        vw, vh, vx, vy = vista(key)
        x0, y0 = vx - vw / 2, vy - vh / 2
        t0 = T[key]
        t1 = t0 + cam_dur(key) + (cam_dur("c1b") if key == "c1" else 0.0)     # a camera1 tem duas partes
        x, y = x0 + 260, y0 + 28
        if key == "c7":
            x = x0 + vw - 260
        if key == "c1":
            y = y0 + vh - 30
        if key == "c9":
            x = x0 + 200
        out.append((t0 + (0.12 if key != "c1" else 0.0), t1, CAMS[key]["chip"], x, y))
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
Style: Num,Poppins ExtraBold,{NUM_FS},&H00E9F1F6,&H00E9F1F6,&H001F1317,&H64000000,-1,0,0,0,100,100,0,0,1,0,6,5,40,40,0
Style: Chip,Poppins ExtraBold,46,&H001F1317,&H001F1317,&H00F3A7B9,&H00000000,-1,0,0,0,100,100,1,0,3,14,0,5,40,40,0
Style: Fecho,Poppins ExtraBold,84,&H00E9F1F6,&H00E9F1F6,&H001F1317,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,4,40,40,0
Style: FechoSub,Poppins,54,&H00F3A7B9,&H00F3A7B9,&H001F1317,&H00000000,-1,0,0,0,100,100,1,0,1,0,0,4,40,40,0
Style: Handle,Poppins,46,&H26E9F1F6,&H26E9F1F6,&H661F1317,&H661F1317,-1,0,0,0,100,100,1,0,3,12,0,5,40,40,0
Style: Draw,Poppins,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []

    def add(s, e, style, txt, layer=1):
        ev.append(f"Dialogue: {layer},{ass_time(s)},{ass_time(e)},{style},,0,0,0,,{txt}")

    # --- legendas: toda a fala; nenhum bloco entra numa cartela nem no spoiler (corta no início deles)
    cartelas = [T["dia6"], T["qui"], T["c9"]]
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

    # --- contador de dias: 6 segmentos; os 5 primeiros já cheios; o 6º enche na cartela DIA 6. Em "seis dias
    # de busca" o contador inteiro acende (brilho), e na cartela da quinta ele só pulsa
    def seg(i):
        return SEG_X0 + i * (SEG_W + SEG_GAP)
    for i in range(6):
        add(0, DUR, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(CREAM)}\1a&HBF&\fad(250,0)\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 0)
    for i in range(5):
        add(0, DUR, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(LILAC)}\fad(250,0)\p1}}"
            + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
    tf = T["dia6"] + 0.15
    x = seg(5)
    clip0 = rf"\clip({x:.0f},{SEG_Y - 20},{x:.0f},{SEG_Y + SEG_H + 20})"
    clip1 = rf"\clip({x:.0f},{SEG_Y - 20},{x + SEG_W:.0f},{SEG_Y + SEG_H + 20})"
    add(tf, DUR, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}{clip0}\t(0,450,{clip1})\p1}}"
        + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
    add(tf, tf + 1.2, "Draw", rf"{{\pos({x:.1f},{SEG_Y})\1c{ass_c(LILAC)}\1a&H60&\blur8{clip0}"
        rf"\t(0,450,{clip1})\fad(0,500)\p1}}" + rrect(SEG_W, SEG_H, SEG_H / 2), 1)
    for tp, dur in ((cue("seis dias") + 0.05, 1.6), (T["qui"] + 0.10, 0.9)):     # o contador inteiro pulsa
        for i in range(6):
            add(tp, tp + dur, "Draw", rf"{{\pos({seg(i):.1f},{SEG_Y})\1c{ass_c(LILAC)}\1a&H40&\blur9"
                rf"\fad(150,{int(dur * 600)})\p1}}" + rrect(SEG_W, SEG_H, SEG_H / 2), 2)

    # --- gancho no topo (até o fim da cartela DIA 6, como nos Ep. 1 e 2)
    pop_ = r"\fad(0,150)\fscx102\fscy102\t(0,160,\fscx100\fscy100)"
    add(0, P0[1], "Hook", rf"{{\pos(540,{327 + 0.0605 * 170:.0f}){pop_}}}OS 6 DIAS DA ZOE", 4)
    add(0, P0[1], "HookSub", rf"{{\pos(540,{403 + 0.0605 * 93:.0f}){pop_}}}PARTE 3", 4)

    # --- os números grandes, abaixo das legendas: 2 KM e 7 MIN no gancho; 6 DIAS e depois 10 MIN no P7, no
    # mesmo lugar e do mesmo tamanho. O número em cream e a unidade em lilás
    LIL = rf"{{\1c{ass_c(LILAC)}}}"
    yb = NUM_Y + 0.0605 * NUM_FS

    def numero(t0, t1, num, uni, x):
        add(t0, t1, "Num", rf"{{\pos({x:.0f},{yb:.0f})\fad(90,120)\fscx112\fscy112\t(0,140,\fscx100\fscy100)}}"
            + num + " " + LIL + uni, 5)
    w2, w7, gap = tw("2 KM", NUM_FS), tw("7 MIN", NUM_FS), 70
    xa = 520 - (w2 + gap + w7) / 2
    numero(cue("dois quilômetros") - 0.05, T["dia6"], "2", "KM", xa + w2 / 2)
    numero(cue("sete minutos") - 0.05, T["dia6"], "7", "MIN", xa + w2 + gap + w7 / 2)
    numero(cue("seis dias") - 0.05, cue("dez minutos") - 0.12, "6", "DIAS", 520)
    numero(cue("dez minutos") - 0.05, cue("A gente estava muito") - 0.35, "10", "MIN", 520)

    # --- cartelas: DIA 6 · QUA 23/09 e a da quinta, sem número de dia (QUI 24/09)
    t0, t1 = T["dia6"], P0[1]
    add(t0 + 0.04, t1, "Dia", r"{\move(540,905,540,880,0,220)\fad(120,90)}DIA 6", 2)
    add(t0 + 0.12, t1, "Data", r"{\move(540,1060,540,1040,0,220)\fad(120,90)}QUA 23/09", 2)
    t0, t1 = T["qui"], P0[7]
    add(t0 + 0.04, t1, "Dia", r"{\move(540,985,540,960,0,220)\fad(120,90)\fs220}QUI " + LIL + "24/09", 2)

    # --- etiquetas de horário nas câmeras
    for t_in, t_out, txt, x, y in CHIPS():
        add(t_in, t_out, "Chip", rf"{{\pos({x:.0f},{y:.0f})\frz3\fad(80,120)\fscx112\fscy112"
            rf"\t(0,120,\fscx100\fscy100)}}" + txt, 4)

    # --- fecho: O REENCONTRO →, numa caixa ink embaixo (sobre a manta e a pelúcia: os olhos e o focinho ficam
    # livres), e o @ discreto embaixo da caixa, tudo acima de y = 1500 (zona segura). Sem o "no 1º vídeo do perfil"
    # (pedido do Guilherme, 06/10): a caixa ficou com uma linha só, centrada onde estava a de duas
    ft, fs = "O REENCONTRO", 84
    txt_w = tw(ft, fs, spacing=1)
    aw, ah, gap, padx = 66, 48, 26, 46
    bw = txt_w + gap + aw + 2 * padx
    bh = 120
    by = 1278                       # abaixo do queixo dela (o centro fica em y 1338, como antes)
    bx = 540 - bw / 2
    yl1 = by + bh / 2
    t_in = T["fecho"] + 0.30
    add(t_in, DUR, "Draw", rf"{{\pos({bx:.1f},{by:.1f})\1c{ass_c(INK)}\1a&H1A&\fad(250,0)\p1}}" + rrect(bw, bh, 22), 5)
    add(t_in, DUR, "Fecho", rf"{{\an4\pos({bx + padx:.1f},{yl1 + 2:.1f})\fad(250,0)}}" + ft, 6)
    add(t_in, DUR, "Draw", rf"{{\pos({bx + padx + txt_w + gap:.1f},{yl1 - ah / 2:.1f})\1c{ass_c(PINK)}"
        rf"\fad(250,0)\p1}}" + arrow(aw, ah, 13), 6)
    add(t_in + 0.25, DUR, "Handle", rf"{{\pos(540,{by + bh + 42:.0f})\fad(300,0)}}" + HANDLE, 6)

    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ================================================================ áudio
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
    return {
        "t0": 0.10,
        "hits": hits(),                                    # as passagens da Zoe
        "baixa": P0[5] - 0.15,                             # P6: baixa
        "pad": cue("busca,", end=True) + 0.05,             # depois de "seis dias de busca": só o pad
        "corte": cue("A gente estava muito") - 0.30,       # zera antes de "A gente estava muito longe"
        "qui": T["qui"],
        "spoiler": T["c9"],
        "fecho": T["fecho"],
        "end": DUR,
        "chimes": [cue("seis dias") + 0.05, T["qui"] + 0.10],
        "gancho": P0[1],                                    # até o P2, o groove suave
        "respiro": (local_final(0, TRECHOS[1][-1][1]) - 0.05, P0[1]),  # do fim da vogal de "minutos" (antes do "s") ao P2: só o pad
    }


MUSIC_DB = -8.0         # trilha em relação à voz, antes do duck (a voz tira ~6 dB dela)
AMB_DB = 12.0           # ambiente do fecho (o som original da IMG_8337 é baixinho: -57 dB de média, sem fala)
SEM_VOZ_DB = -19.5      # média (volumedetect) da trilha nos trechos sem voz, no mix final
ACENTO_DB = 4.0         # as marcas das passagens em relação à trilha (o arquivo já sai 0,3x mais baixo: trilha_05.ACENTO)
RAMPA = 0.30            # o ganho sobe ao sair a voz e desce ao entrar a voz nesse tempo
LIMITE = {"mix": 0.80, "mix-sem-musica": 0.84}   # teto do limitador (com trilha: ≤ -1,5 dBFS de true peak)


def sem_voz():
    """Os trechos sem voz em que a trilha sobe: a CAM 2 da Lava Pés, as câmeras da Chicuta, a camera8 e o
    spoiler. (início da subida, fim) na linha do tempo."""
    return [(P1[1] - 0.15, P0[2]), (P1[2] - 0.15, P0[3]), (P1[3] - 0.15, P0[4]), (P1[8] - 0.15, T["fecho"] + 0.6)]


def janelas():
    """Onde medir a trilha sem voz (sem as rampas): uma janela por trecho de sem_voz()."""
    nomes = ("A", "B", "C", "D")
    return {n: (round(a + 0.15 + RAMPA + 0.05, 2), round(b - RAMPA - 0.05, 2)) for n, (a, b) in zip(nomes, sem_voz())}


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
        if abs(li + 14) < 0.05:
            break
        g += -14 - li
    normalize.ganho = g
    return li, lp


def build_audio():
    """voz.wav → mixagem com trilha e sem trilha, as duas em -14 LUFS. Na com trilha, a trilha sobe só nos
    trechos sem voz (sem_voz), até a média de SEM_VOZ_DB; sob a voz o duck fica como no Ep. 2."""
    import trilha_05   # noqa: E402  trilha original (numpy + scipy)
    voz, pre, pre_nat = WORK / "voz.wav", WORK / "mix-pre.wav", WORK / "mix-sem-musica-pre.wav"
    ins, fc, extra = [], [], []
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
        if k in ENXERTO:                  # o "s" que a gravação não pegou (ver ENXERTO)
            ef, e0, e1, eg, ex, eo = ENXERTO[k]
            extra.append(VOZ / f"{ef}.ogg")   # as entradas extras vão depois de todas as partes (a parte k é a entrada k)
            j = len(PARTS) + len(extra) - 1
            fc.append(f"{src},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"
                      f"afade=t=in:d={fi}[q{k}]")
            fc.append(f"[{j}:a]atrim=start={e0}:end={e1},asetpts=PTS-STARTPTS,aresample=48000,"
                      f"aformat=sample_fmts=fltp:channel_layouts=mono,volume={eg}dB[e{k}]")
            de = d + _ext(k)
            fc.append(f"[q{k}][e{k}]acrossfade=d={ex}:c1=tri:c2=tri,afade=t=out:st={de - eo:.3f}:d={eo}[p{k}]")
            continue
        fc.append(f"{src},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"
                  f"afade=t=in:d={fi},afade=t=out:st={d - fo:.3f}:d={fo}[p{k}]")
    for e in extra:
        ins += ["-i", e]
    gaps = [P0[0]] + [P0[k] - P1[k - 1] for k in range(1, len(PARTS))]
    for k, g in enumerate(gaps):
        fc.append(f"aevalsrc=0:s=48000:d={g:.4f},aformat=sample_fmts=fltp:channel_layouts=mono[g{k}]")
    seq = "".join(f"[g{k}][p{k}]" for k in range(len(PARTS)))
    fc.append(f"{seq}concat=n={2 * len(PARTS)}:v=0:a=1,highpass=f=80,afftdn=nf=-25,"
              f"acompressor=threshold=0.1:ratio=2.5:attack=10:release=150,apad=whole_dur={DUR}[v]")
    ff([*ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", DUR, "-c:a", "pcm_s16le", voz])

    trilha_05.render(MUSIC, music_marks(), acc_out=MUSIC_ACC)
    vi, _ = loudness(voz)
    mi, _ = loudness(MUSIC)
    mg = vi + MUSIC_DB - mi
    ms = int(T["fecho"] * 1000)
    fdur = DUR - T["fecho"]
    amb = (f"[2:a]aresample=48000,aformat=channel_layouts=stereo,highpass=f=120,lowpass=f=9000,"
           f"volume={AMB_DB}dB,afade=t=in:d=0.6,afade=t=out:st={fdur - 1.0:.2f}:d=0.95,adelay={ms}|{ms},"
           f"apad=whole_dur={DUR}[amb]")
    hoje = ["-ss", HOJE_SS, "-t", fdur, "-i", HOJE]
    trechos = sem_voz()
    win = janelas()
    mix, mix_nat = WORK / "mix.wav", WORK / "mix-sem-musica.wav"

    def com_trilha(g):
        """A voz empurra a trilha para baixo (sidechain); depois do duck, o ganho de cada trecho sem voz entra e
        sai em RAMPA s. As marcas das passagens vêm à parte (ACENTO_DB em relação à trilha), com o mesmo duck da
        voz e o mesmo ganho de cada trecho."""
        up = "1" + "".join(
            f"+{10 ** (g[n] / 20) - 1:.4f}*clip((t-{a:.3f})/{RAMPA},0,1)*clip(({b:.3f}-t)/{RAMPA},0,1)"
            for n, (a, b) in zip(win, trechos))
        fc = (f"[0:a]pan=stereo|c0=c0|c1=c0,asplit=3[v][key][key2];"
              f"[1:a]aresample=48000,volume={mg:.2f}dB[m];"
              f"[m][key]sidechaincompress=threshold=0.02:ratio=2.5:attack=25:release=400:makeup=1,"
              f"volume='{up}':eval=frame[md];{amb};"
              f"[3:a]aresample=48000,volume={mg + ACENTO_DB:.2f}dB[a0];"
              f"[a0][key2]sidechaincompress=threshold=0.02:ratio=2.5:attack=25:release=400:makeup=1,"
              f"volume='{up}':eval=frame[acc];"
              f"[v][md][amb][acc]amix=inputs=4:normalize=0:duration=first[out]")
        ff(["-i", voz, "-i", MUSIC, *hoje, "-i", MUSIC_ACC, "-filter_complex", fc, "-map", "[out]", "-t", DUR,
            "-c:a", "pcm_s16le", pre])
        li, lp = normalize(pre, mix, LIMITE["mix"])
        com_trilha.fc = fc
        names = list(win)
        return li, lp, dict(zip(names, mean_db(mix, [win[n] for n in names])))

    g = {n: 6.0 for n in win}
    for it in range(6):                   # acerta cada ganho até a média de cada trecho sem voz bater
        li, lp, med = com_trilha(g)
        print("  trilha sem voz, passada", it + 1, " | ".join(
            f"{n} {win[n][0]:.1f}–{win[n][1]:.1f} s: {g[n]:+.1f} dB → {med[n]:.1f} dB" for n in win))
        if all(abs(med[n] - SEM_VOZ_DB) < 0.25 for n in win):
            break
        for n in win:
            g[n] += SEM_VOZ_DB - med[n]
    print(f"{mix.name}: {li:.1f} LUFS, pico {lp:.1f} dBFS (voz {vi:.1f} LUFS, trilha {mg:+.1f} dB, sem voz "
          + ", ".join(f"{n} {g[n]:+.1f}" for n in win) + " dB)")
    # para a revisão: a trilha como ela entra na mixagem (com o duck, os ganhos e o ganho final), sem a voz, e a voz
    # sozinha, no mesmo ganho: videos/ep3/trilha-isolada.wav, acento-isolado.wav e voz-isolada.wav
    gf = normalize.ganho
    base = com_trilha.fc.split("[v][md][amb][acc]amix")[0]
    for nome, fim, sobra in (("trilha-isolada", "[md][acc]amix=inputs=2:normalize=0:duration=first", "[v][amb]"),
                             ("acento-isolado", "[acc]anull", "[v][md][amb]"), ("voz-isolada", "[v]anull", "[md][amb][acc]")):
        sink = "".join(f";{x}]anullsink" for x in sobra[:-1].split("]"))
        fcx = f"{base}{fim},volume={gf:.2f}dB[out]{sink}"
        ff(["-i", voz, "-i", MUSIC, *hoje, "-i", MUSIC_ACC, "-filter_complex", fcx, "-map", "[out]", "-t", DUR,
            "-c:a", "pcm_s16le", WORK / f"{nome}.wav"])
    # sem trilha: voz + ambiente do fecho
    fc = f"[0:a]pan=stereo|c0=c0|c1=c0[v];{amb.replace('[2:a]', '[1:a]')};[v][amb]amix=inputs=2:normalize=0:duration=first[out]"
    ff(["-i", voz, *hoje, "-filter_complex", fc, "-map", "[out]", "-t", DUR, "-c:a", "pcm_s16le", pre_nat])
    li, lp = normalize(pre_nat, mix_nat, LIMITE["mix-sem-musica"])
    print(f"{mix_nat.name}: {li:.1f} LUFS, pico {lp:.1f} dBFS")
    return mix, mix_nat


# ================================================================ vídeo
def fpath(p):
    # caminho para dentro do filtergraph: no Windows, "C:\..." quebra o parser do ffmpeg
    return Path(p).resolve().as_posix().replace(":", r"\:")


def plano_em(sh, t):
    starts = [s[0] for s in sh]
    i = max(k for k, s in enumerate(starts) if s <= t + 1e-6)
    t0, fn, o = sh[i]
    t1 = sh[i + 1][0] if i + 1 < len(sh) else DUR
    return i, t0, t1, fn, o


def render(mix, out, t_from=0.0, t_to=None):
    """Compõe os quadros plano a plano e manda para o ffmpeg. Os quadros das câmeras de um plano são soltos da
    memória quando ele acaba (a máquina tem pouca RAM livre)."""
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
        i, t0, t1, fn, o = plano_em(sh, t)
        if cur is not None and cur is not o:
            if "_rd" in cur:
                cur.pop("_rd").close()
            if "cam" in cur and not any(s[2].get("cam") == cur["cam"] for s in sh[i:]):
                release(cur["cam"])
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


def quadros(ts):
    """Só os quadros pedidos (com o texto do ASS queimado), em PNG: videos/ep3/quadros/q-<t>.png."""
    outdir = WORK / "quadros"
    outdir.mkdir(parents=True, exist_ok=True)
    sh = shots()
    for t in ts:
        n = int(round(t * FPS))
        t = n / FPS
        i, t0, t1, fn, o = plano_em(sh, t)
        o = dict(o)
        o.pop("_rd", None)
        o["_off"] = t - t0
        fr = fn(o, t, t0, t1)
        if "_rd" in o:
            o.pop("_rd").close()
        raw = outdir / "raw.png"
        fr.save(raw)
        ff(["-i", raw, "-vf", f"setpts=PTS+{t}/TB,subtitles='{fpath(ASS)}':fontsdir='{fpath(FONTS)}'",
            "-frames:v", "1", outdir / f"q-{t:06.2f}.png"])
        raw.unlink()
        print(outdir / f"q-{t:06.2f}.png")


def prep():
    WORK.mkdir(parents=True, exist_ok=True)
    if not (MAPS / "ep3-camadas.json").exists() or not all((MAPS / f"ep3-{n}.png").exists() for n in ("perto", "meio", "cidade")):
        import mapa   # noqa: E402  (Chrome headless)
        mapa.ep3_camadas(MAPS)
        _cache.clear()


ZOE_PLANO = {"c1": "camera1", "c1b": "camera1", "c2a": "camera2-cam2", "c2d": "camera2-cam1", "c2b": "camera2-lixeira",
             "c3": "camera3", "c4": "camera4", "c5": "camera5", "c6": "camera6", "c7": "camera7", "c8": "camera8",
             "c9": "camera9"}


def confere():
    """Antes de renderizar: cada janela dentro da imagem da câmera em todos os quadros do plano, e cada plano
    cobrindo a passagem confirmada (ZOE) da sua câmera."""
    for key in CAMS:
        f = confere_janelas(key)
        a, b = ZOE[ZOE_PLANO[key]]
        fora = CAMS[key]["se"] < a or CAMS[key]["ss"] > b
        print(f"  janela {key}: folga mínima {f:5.1f} px | plano {CAMS[key]['ss']:.2f}–{CAMS[key]['se']:.2f} s"
              f" (Zoe {a:.2f}–{b:.2f} s)" + ("" if f >= 0 else "  ← FORA DA IMAGEM: ajuste CAMS")
              + ("  ← O PLANO NÃO MOSTRA A PASSAGEM" if fora else ""))
        release(key)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")       # o log vai para arquivo no Windows (cp1252)
    except AttributeError:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == "palavras":
        return palavras()
    prep()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    build_ass(ASS)
    if len(sys.argv) > 1 and sys.argv[1] == "quadros":
        return quadros([float(x) for x in sys.argv[2:]])
    nomes = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]
    print("linha do tempo:", " | ".join(f"{n} {a:.2f}-{b:.2f}" for n, a, b in zip(nomes, P0, P1)))
    print("blocos:", " | ".join(f"{k} {v:.2f}" for k, v in sorted(T.items(), key=lambda kv: kv[1])))
    print("tempos fortes:", ", ".join(f"{h:.2f}" for h, _ in hits()))
    confere()
    mix, mix_nat = build_audio()
    if len(sys.argv) > 1 and sys.argv[1] == "audio":       # só refaz as mixagens e troca o áudio dos MP4
        for src, mx in ((OUT, mix), (OUT_NAT, mix_nat)):
            tmp = WORK / "remux.mp4"
            ff(["-i", OUT, "-i", mx, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-t", f"{DUR:.3f}", tmp])
            tmp.replace(src)
            print(src)
        return
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
