"""Gera o QR code do perfil (img/qr-instagram.svg) usado na etiqueta.

Aponta para o Instagram (o perfil da comunidade local); o @ é o mesmo no TikTok e vai escrito embaixo.
Sem borda (a margem clara fica por conta da caixa creme no index.html) e em ink, para a impressão.

Precisa do segno num venv temporário: pip install segno
"""
from pathlib import Path

import segno

URL = "https://www.instagram.com/souazoe.pf/"
OUT = Path(__file__).resolve().parent / "img" / "qr-instagram.svg"

OUT.parent.mkdir(parents=True, exist_ok=True)
qr = segno.make(URL, error="m", micro=False)
qr.save(OUT, kind="svg", border=0, dark="#17131F", light=None, xmldecl=False, svgns=True, nl=False)
# o segno grava width/height fixos; com viewBox o SVG escala no tamanho que o CSS der
n = qr.symbol_size(border=0)[0]
svg = OUT.read_text().replace(f'width="{n}" height="{n}"', f'viewBox="0 0 {n} {n}" shape-rendering="crispEdges"')
OUT.write_text(svg)
print(OUT, f"versão {qr.version}, {qr.symbol_size(border=0)[0]} módulos")
