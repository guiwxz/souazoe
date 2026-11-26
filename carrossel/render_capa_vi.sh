#!/bin/sh
# Renderiza a capa única do ZOE VI (zoe-vi-capa.html) em ../saida/carrossel/carrossel2/zoe-vi-capa-feed.png (1080x1350)
# e zoe-vi-capa-story.png (1080x1920, Stories/TikTok). Uso: sh carrossel/render_capa_vi.sh
cd "$(dirname "$0")"
OUT=../saida/carrossel/carrossel2
mkdir -p "$OUT"
CHROME=$(command -v google-chrome || command -v chrome || command -v chromium || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
[ -x "$CHROME" ] || for c in /opt/pw-browsers/chromium-*/chrome-linux*/chrome; do [ -x "$c" ] && CHROME="$c"; done
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/capa.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/zoe-vi-capa.html" ;; *) URL="file:///$DIR/zoe-vi-capa.html" ;; esac
export OUT SHOT
SANDBOX=; [ "$(id -u 2>/dev/null)" = 0 ] && SANDBOX=--no-sandbox
"$CHROME" $SANDBOX --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,3400 --screenshot="$SHOT" "$URL" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out = os.environ['OUT']
im = Image.open(os.environ['SHOT']).convert('RGB')
im.crop((0, 0, 1080, 1350)).save(f'{out}/zoe-vi-capa-feed.png')
im.crop((0, 1350, 1080, 3270)).save(f'{out}/zoe-vi-capa-story.png')
print(f'{out}/zoe-vi-capa-feed.png', f'{out}/zoe-vi-capa-story.png')
PY
rm -rf "$TMP"
