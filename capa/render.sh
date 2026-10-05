#!/bin/sh
# Renderiza a capa do Reel (1080x1920) em ../saida/video/<pasta>/<nome>.png (padrão: video1/capa-01-v2, a do Reel 01 v2)
# + <nome>-grid.jpg, uma prévia do recorte 3:4 que aparece no grid do perfil (não precisa versionar).
# Uso: ./render.sh [video5] [capa-05]
cd "$(dirname "$0")"
OUT="../saida/video/${1:-video1}"
NAME="${2:-capa-01-v2}"
mkdir -p "$OUT"
export OUT NAME
google-chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=3000 --window-size=1080,2200 --screenshot=/tmp/zoe_capa.png "file://$PWD/index.html" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out, name = os.environ['OUT'], os.environ['NAME']
im=Image.open('/tmp/zoe_capa.png').convert('RGB').crop((0,0,1080,1920))
im.save(f'{out}/{name}.png')
im.crop((0,240,1080,1680)).resize((540,720)).save(f'{out}/{name}-grid.jpg',quality=88)
PY
echo "$OUT/$NAME.png"
