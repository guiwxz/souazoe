#!/bin/sh
# Renderiza os 8 cards (1080x1350) em ../saida/carrossel/<nome>/ (padrão: carrossel1)
# Uso: ./render.sh [carrossel2]
cd "$(dirname "$0")"
OUT="../saida/carrossel/${1:-carrossel1}"
mkdir -p "$OUT"
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/zoe_full.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/index.html" ;; *) URL="file:///$DIR/index.html" ;; esac
export OUT SHOT
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,11200 --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out=os.environ['OUT']
im=Image.open(os.environ['SHOT']).convert('RGB')
for i in range(8):
    im.crop((0,i*1350,1080,(i+1)*1350)).save(f'{out}/zoe-{i+1:02d}.png')
t=Image.new('RGB',(4*540,2*675))
for i in range(8):
    t.paste(Image.open(f'{out}/zoe-{i+1:02d}.png').resize((540,675)),((i%4)*540,(i//4)*675))
t.save(f'{out}/_preview.jpg',quality=88)
PY
rm -rf "$TMP"
