#!/bin/sh
# Renderiza os 8 cards (1080x1350) em ../saida/carrossel/<nome>/ (padrão: carrossel1)
# Uso: ./render.sh [carrossel2]
cd "$(dirname "$0")"
OUT="../saida/carrossel/${1:-carrossel1}"
mkdir -p "$OUT"
export OUT
google-chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,11200 --screenshot=/tmp/zoe_full.png "file://$PWD/index.html" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out=os.environ['OUT']
im=Image.open('/tmp/zoe_full.png').convert('RGB')
for i in range(8):
    im.crop((0,i*1350,1080,(i+1)*1350)).save(f'{out}/zoe-{i+1:02d}.png')
t=Image.new('RGB',(4*540,2*675))
for i in range(8):
    t.paste(Image.open(f'{out}/zoe-{i+1:02d}.png').resize((540,675)),((i%4)*540,(i//4)*675))
t.save(f'{out}/_preview.jpg',quality=88)
PY
