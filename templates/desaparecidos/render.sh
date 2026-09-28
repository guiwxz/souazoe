#!/bin/sh
# Renderiza o alerta em saida/<nome>-feed.png (1080x1350) e saida/<nome>-story.png (1080x1920)
# Uso: ./render.sh [garibaldi-masha]
cd "$(dirname "$0")"
NOME="${1:-garibaldi-masha}"
mkdir -p saida
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/alerta.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/index.html" ;; *) URL="file:///$DIR/index.html" ;; esac
export NOME SHOT
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,3270 --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
nome = os.environ['NOME']
im = Image.open(os.environ['SHOT']).convert('RGB')
im.crop((0, 0, 1080, 1350)).save(f'saida/{nome}-feed.png')
im.crop((0, 1350, 1080, 3270)).save(f'saida/{nome}-story.png')
print(f'saida/{nome}-feed.png', f'saida/{nome}-story.png')
PY
rm -rf "$TMP"
