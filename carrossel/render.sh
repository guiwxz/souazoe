#!/bin/sh
# Renderiza os cards (1080x1350) em ../saida/carrossel/<nome>/ (padrão: carrossel1)
# Uso: ./render.sh [carrossel2]
cd "$(dirname "$0")"
OUT="../saida/carrossel/${1:-carrossel1}"
mkdir -p "$OUT"
N=$(grep -c "<section class=\"card" index.html)
export OUT N
google-chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --window-size=1080,$((N*1350+400)) --screenshot=/tmp/zoe_full.png "file://$PWD/index.html" 2>/dev/null
python3 - <<'PY'
import os
from PIL import Image
out=os.environ['OUT']
im=Image.open('/tmp/zoe_full.png').convert('RGB')
n=int(os.environ['N'])
for i in range(n):
    im.crop((0,i*1350,1080,(i+1)*1350)).save(f'{out}/zoe-{i+1:02d}.png')
c=(n+1)//2
t=Image.new('RGB',(c*540,2*675))
for i in range(n):
    t.paste(Image.open(f'{out}/zoe-{i+1:02d}.png').resize((540,675)),((i%c)*540,(i//c)*675))
t.save(f'{out}/_preview.jpg',quality=88)
PY
