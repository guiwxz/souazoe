#!/bin/sh
# Renderiza a capa do Reel (1080x1920) em ../saida/video/<pasta>/capa.png (padrão: video3)
# + capa-grid.jpg, o recorte 3:4 que aparece no grid do perfil.
# Uso: ./render.sh [video2]
cd "$(dirname "$0")"
OUT="../saida/video/${1:-video3}"
mkdir -p "$OUT"
export OUT
google-chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=3000 --window-size=1080,2200 --screenshot=/tmp/zoe_capa.png "file://$PWD/index.html" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out=os.environ['OUT']
im=Image.open('/tmp/zoe_capa.png').convert('RGB').crop((0,0,1080,1920))
im.save(f'{out}/capa.png')
im.crop((0,240,1080,1680)).resize((540,720)).save(f'{out}/capa-grid.jpg',quality=88)
PY
echo "$OUT/capa.png"
