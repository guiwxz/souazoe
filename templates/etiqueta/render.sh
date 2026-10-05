#!/bin/sh
# Renderiza a etiqueta dos saquinhos de petisco (index.html, 9 x 5 cm) em:
#   saida/etiqueta-petisco.png         a etiqueta a 300 dpi (1063 x 591), sem sangria: prévia e envio
#   saida/etiqueta-petisco-grafica.pdf vetorial, 94 x 54 mm (2 mm de sangria em volta), para a gráfica
#   saida/etiqueta-petisco-a4.pdf      A4 com 10 etiquetas e marcas de corte, para imprimir em casa
#                                      (papel adesivo ou couchê; imprimir em "tamanho real", sem ajustar à página)
# Uso: ./render.sh
cd "$(dirname "$0")"
mkdir -p saida
# no Windows (Git Bash) o Chrome não está no PATH e o Python nativo não enxerga /tmp nem /c/...
CHROME=$(command -v google-chrome || command -v chrome || command -v chromium || echo "/c/Program Files/Google/Chrome/Application/chrome.exe")
# ambiente remoto: Chromium do Playwright
[ -x "$CHROME" ] || for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome; do [ -x "$c" ] && CHROME="$c"; done
win() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
TMP=$(mktemp -d)
SHOT="$(win "$TMP")/etiqueta.png"
DIR=$(win "$PWD")
case "$DIR" in /*) URL="file://$DIR/index.html" ;; *) URL="file:///$DIR/index.html" ;; esac
SANDBOX=; [ "$(id -u 2>/dev/null)" = 0 ] && SANDBOX=--no-sandbox  # Chrome como root (container) exige
CH() { "$CHROME" $SANDBOX --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=4000 "$@" 2>/dev/null; }

# PNG a 300 dpi: 1 px do CSS = 1/96 pol, então a escala é 300/96; 90 x 50 mm = 340,2 x 189 px do CSS
CH --force-device-scale-factor=3.125 --window-size=341,189 --screenshot="$SHOT" "$URL#png"
CH --no-pdf-header-footer --print-to-pdf="$DIR/saida/etiqueta-petisco-grafica.pdf" "$URL#grafica"
CH --no-pdf-header-footer --print-to-pdf="$DIR/saida/etiqueta-petisco-a4.pdf" "$URL#folha"

export SHOT
python3 - <<'PY'
import os
from PIL import Image
im = Image.open(os.environ['SHOT']).convert('RGB')
im = im.crop((0, 0, round(90 / 25.4 * 300), round(50 / 25.4 * 300)))
im.save('saida/etiqueta-petisco.png', dpi=(300, 300))
print('saida/etiqueta-petisco.png', im.size)
PY
ls saida/*.pdf
rm -rf "$TMP"
