#!/bin/sh
# Renderiza cada Story (<section class="card">, 1080x1920) de <nome>.html em saida/<nome>-1.png, -2.png...
# na ordem da página (a ordem em que vão ao ar).
# Uso: ./render.sh [tapete-de-lambida]
cd "$(dirname "$0")"
NOME="${1:-tapete-de-lambida}"
PAGINA="$NOME.html"
[ -f "$PAGINA" ] || { echo "não existe $PAGINA" >&2; exit 1; }
mkdir -p saida
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || command -v chromium || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
# ambiente remoto: Chromium do Playwright
[ -x "$CHROME" ] || for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome; do [ -x "$c" ] && CHROME="$c"; done
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
N=$(grep -c '<section class="card"' "$PAGINA")
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/dica.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/$PAGINA" ;; *) URL="file:///$DIR/$PAGINA" ;; esac
export NOME SHOT N
SANDBOX=; [ "$(id -u 2>/dev/null)" = 0 ] && SANDBOX=--no-sandbox  # Chrome como root (container) exige
"$CHROME" $SANDBOX --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,$((N * 1920)) --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
nome, n = os.environ['NOME'], int(os.environ['N'])
im = Image.open(os.environ['SHOT']).convert('RGB')
for i in range(n):
    im.crop((0, i * 1920, 1080, (i + 1) * 1920)).save(f'saida/{nome}-{i + 1}.png')
    print(f'saida/{nome}-{i + 1}.png')
PY
rm -rf "$TMP"
