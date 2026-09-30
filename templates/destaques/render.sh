#!/bin/sh
# Renderiza cada capa (<section class="capa" id="..." data-nome="...">, 1080x1920) em saida/<id>.png
# e um _preview.png com a fileira de destaques como aparece no perfil (círculos pequenos + nomes).
# Uso: ./render.sh
cd "$(dirname "$0")"
mkdir -p saida
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || command -v chromium || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
[ -x "$CHROME" ] || for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome; do [ -x "$c" ] && CHROME="$c"; done
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
N=$(grep -c '^<section class="capa"' index.html)
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/capas.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/index.html" ;; *) URL="file:///$DIR/index.html" ;; esac
export SHOT
SANDBOX=; [ "$(id -u 2>/dev/null)" = 0 ] && SANDBOX=--no-sandbox
"$CHROME" $SANDBOX --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,$((N * 1920)) --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os, re
from PIL import Image, ImageDraw, ImageFont
capas = re.findall(r'^<section class="capa" id="([^"]+)" data-nome="([^"]+)"',
                   open('index.html', encoding='utf-8').read(), re.M)
im = Image.open(os.environ['SHOT']).convert('RGB')
# prévia: o círculo do meio no tamanho do perfil (~150 px em tela retina) e o nome embaixo
D, G = 150, 36
prev = Image.new('RGB', (G + (D + G) * len(capas), D + 110), (255, 255, 255))
draw = ImageDraw.Draw(prev)
fonte = ImageFont.truetype('../fonts/Poppins-Medium.ttf', 24)
anel = Image.new('L', (D, D), 0)
ImageDraw.Draw(anel).ellipse((0, 0, D - 1, D - 1), fill=255)
for i, (ident, nome) in enumerate(capas):
    capa = im.crop((0, i * 1920, 1080, (i + 1) * 1920))
    capa.save(f'saida/{ident}.png')
    x = G + (D + G) * i
    prev.paste(capa.crop((0, 420, 1080, 1500)).resize((D, D), Image.LANCZOS), (x, 30), anel)
    draw.ellipse((x - 5, 25, x + D + 4, 30 + D + 4), outline=(219, 219, 219), width=2)
    draw.text((x + D / 2, D + 50), nome, font=fonte, fill=(38, 38, 38), anchor='mt')
    print(f'saida/{ident}.png')
prev.save('saida/_preview.png')
PY
rm -rf "$TMP"
