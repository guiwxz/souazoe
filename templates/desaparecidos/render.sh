#!/bin/sh
# Renderiza o alerta em saida/<nome>-feed.png (1080x1350) e saida/<nome>-story.png (1080x1920)
# e, se a página tiver um terceiro card (quadrado, para carrossel), em saida/<nome>-quadrado.png (1080x1080)
# Uso: ./render.sh [garibaldi-masha]
# Se existir <nome>.html (caso com layout próprio, ex.: bob.html), renderiza ele; senão, o index.html
cd "$(dirname "$0")"
NOME="${1:-garibaldi-masha}"
mkdir -p saida
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || command -v chromium || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
# ambiente remoto: Chromium do Playwright
[ -x "$CHROME" ] || for c in /opt/pw-browsers/chromium-*/chrome-linux*/chrome; do [ -x "$c" ] && CHROME="$c"; done
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/alerta.png"
DIR=$(win "$PWD")
PAGINA=index.html
[ -f "$NOME.html" ] && PAGINA="$NOME.html"
case "$DIR" in /*) URL="file://$DIR/$PAGINA" ;; *) URL="file:///$DIR/$PAGINA" ;; esac
export NOME SHOT
SANDBOX=; [ "$(id -u 2>/dev/null)" = 0 ] && SANDBOX=--no-sandbox  # Chrome como root (container) exige
"$CHROME" $SANDBOX --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,4400 --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
nome = os.environ['NOME']
im = Image.open(os.environ['SHOT']).convert('RGB')
im.crop((0, 0, 1080, 1350)).save(f'saida/{nome}-feed.png')
im.crop((0, 1350, 1080, 3270)).save(f'saida/{nome}-story.png')
saidas = [f'saida/{nome}-feed.png', f'saida/{nome}-story.png']
quadrado = im.crop((0, 3270, 1080, 4350))
if quadrado.getbbox():  # abaixo do Stories só tem o preto do body quando a página não tem o card quadrado
    quadrado.save(f'saida/{nome}-quadrado.png')
    saidas.append(f'saida/{nome}-quadrado.png')
print(*saidas)
PY
rm -rf "$TMP"
