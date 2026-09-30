"""Mapas da série "Os 6 dias da Zoe": ruas reais de Passo Fundo (OpenStreetMap) na identidade da Zoe.

Gera quadros 1080x1920 (SVG → Chrome headless → PNG). A malha de ruas é baixada uma vez
da Overpass API e fica em videos/osm-passo-fundo.json (não versionado). Ruas © OpenStreetMap.

Uso: python editor/mapa.py ep1 [pasta_saida]          (padrão: videos/mapas/)
     python editor/mapa.py ep1-camadas [pasta_saida]  (camadas para as animações do build_03.py)
     python editor/mapa.py ep2 [pasta_saida]          (Ep. 2: o trajeto uma rua adiante, antes e depois)
     python editor/mapa.py ep2-camadas [pasta_saida]  (camadas para as animações do build_04.py)
"""
import json
import math
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "videos" / "osm-passo-fundo.json"
FONTS = ROOT / "editor" / "fonts"
W, H = 1080, 1920

# identidade: ink, cream, lilac, pink, muted
INK, CREAM, LILAC, PINK, MUTED = "#17131F", "#F6F1E9", "#B9A7F3", "#EC4899", "#6E667A"

BBOX = (-28.305, -52.465, -28.195, -52.345)   # sul, oeste, norte, leste: a área urbana inteira
ROADS = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|"
         "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link")
# (largura em metros, cor): a largura acompanha o zoom, com um mínimo em pixels
STYLE = {
    "residential": (9, "#2A2433"), "living_street": (9, "#2A2433"), "unclassified": (9, "#2A2433"),
    "tertiary": (12, "#352D42"), "tertiary_link": (10, "#352D42"),
    "secondary": (15, "#41384F"), "secondary_link": (12, "#41384F"),
    "primary": (18, "#4C4260"), "primary_link": (14, "#4C4260"),
    "trunk": (20, "#574B6D"), "trunk_link": (14, "#574B6D"),
    "motorway": (22, "#574B6D"), "motorway_link": (14, "#574B6D"),
    "stream": (4, "#1E2436"), "river": (30, "#1F2840"),
}

# a fuga (cruzamentos exatos no OSM): subiu a Tiradentes e, na Lava Pés, virou para a esquerda
ESQ_BRITO = (-28.2533441, -52.4049122)     # Tiradentes × Eduardo de Brito: onde ela escapou da guia
ESQ_LAVAPES = (-28.2542755, -52.4040163)   # Tiradentes × Lava Pés
FIM = (-28.2559816, -52.4065435)           # Lava Pés × Fagundes dos Reis (duas quadras): até onde se sabe
# a rota segue pelos nós da Rua Lava Pés até o FIM (Silva Jardim, Benjamin Constant, Fagundes dos Reis)
FIM_EP2 = (-28.2566359, -52.4078446)       # Lava Pés × Capitão Eleutério: uma rua a mais (câmeras da terça, 22/09)

ANCORA = (W / 2, 540)                      # onde o MEIO cai na tela, igual nas três vistas (trajeto no alto)
LARGURA = {"a": 700, "b": 2600, "c": 9500}   # metros de largura de cada vista do Ep. 1


def load():
    if not CACHE.exists():
        s, w, n, e = BBOX
        q = (f'[out:json][timeout:170];(way["highway"~"^({ROADS})$"]({s},{w},{n},{e});'
             f'way["waterway"~"^(river|stream)$"]({s},{w},{n},{e}););out tags geom;')
        req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                     data=urllib.parse.urlencode({"data": q}).encode(),
                                     headers={"User-Agent": "zoe-causas-animais/1.0"})
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_bytes(urllib.request.urlopen(req, timeout=200).read())
    return json.loads(CACHE.read_text(encoding="utf-8"))["elements"]


class View:
    """Projeção local: `center` (lat, lon) cai em `anchor` na tela, com `width_m` metros de largura."""

    def __init__(self, center, width_m, anchor=ANCORA, size=(W, H)):
        self.lat0, self.lon0 = center
        self.s = W / width_m                                   # pixels por metro (a largura é a da tela)
        self.kx = 111320 * math.cos(math.radians(self.lat0))   # metros por grau de longitude
        self.ky = 110574                                       # metros por grau de latitude
        self.ax, self.ay = anchor
        self.cw, self.ch = size                                # tamanho do quadro (maior nas vistas "grandes")

    def xy(self, lat, lon):
        return (self.ax + (lon - self.lon0) * self.kx * self.s,
                self.ay + (self.lat0 - lat) * self.ky * self.s)

    def visible(self, geom, pad=200):
        return any(-pad < x < self.cw + pad and -pad < y < self.ch + pad
                   for x, y in (self.xy(g["lat"], g["lon"]) for g in geom))


def _k(p):
    return (round(p[0], 7), round(p[1], 7))


def rota(els, fim=FIM):
    """O trajeto: ESQ_BRITO → ESQ_LAVAPES pela Tiradentes e daí pelos nós da Rua Lava Pés até `fim`
    (caminho mais curto no grafo da rua, sem cortar caminho). Trocar o fim basta para refazer a rota."""
    adj = {}
    for e in els:
        if e["tags"].get("name") == "Rua Lava Pés":
            pts = [_k((g["lat"], g["lon"])) for g in e["geometry"]]
            for a, b in zip(pts, pts[1:]):
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    src, dst = _k(ESQ_LAVAPES), _k(fim)
    if dst not in adj:
        raise ValueError(f"o fim {fim} não é um nó da Rua Lava Pés")
    prev, fila = {src: None}, [src]
    for u in fila:                                  # busca em largura
        for w in sorted(adj.get(u, ())):
            if w not in prev:
                prev[w] = u
                fila.append(w)
    path, u = [], dst
    while u is not None:
        path.append(u)
        u = prev[u]
    return [ESQ_BRITO] + path[::-1]


def meio(r):
    """Centro das três vistas: o meio do retângulo que contém a rota."""
    lats, lons = [p[0] for p in r], [p[1] for p in r]
    return ((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)


def street_along(els, name, corner, dist_m, step):
    """Ponto e ângulo a `dist_m` metros do cruzamento `corner`, andando pela rua `name`
    na ordem dos nós (step=+1) ou ao contrário (step=-1)."""
    ways = [e for e in els if e["tags"].get("name") == name]
    for wy in ways:
        pts = [(g["lat"], g["lon"]) for g in wy["geometry"]]
        for i, p in enumerate(pts):
            if abs(p[0] - corner[0]) < 1e-6 and abs(p[1] - corner[1]) < 1e-6:
                walked, j = 0.0, i
                while 0 <= j + step < len(pts):
                    a, b = pts[j], pts[j + step]
                    seg = math.hypot((b[0] - a[0]) * 110574, (b[1] - a[1]) * 111320 * 0.881)
                    if walked + seg >= dist_m:
                        t = (dist_m - walked) / seg
                        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), (a, b)
                    walked += seg
                    j += step
    raise ValueError(f"não achei {name} a partir de {corner}")


def svg_label(v, text, pt, seg, size=26):
    x, y = v.xy(*pt)
    (ax, ay), (bx, by) = v.xy(*seg[0]), v.xy(*seg[1])
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    if ang > 90:
        ang -= 180
    elif ang < -90:
        ang += 180
    return (f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate({ang:.1f} {x:.1f} {y:.1f})" '
            f'font-family="PB" font-size="{size}" letter-spacing="3" fill="{CREAM}" fill-opacity=".75" '
            f'stroke="{INK}" stroke-width="7" paint-order="stroke" text-anchor="middle" '
            f'dominant-baseline="central">{text}</text>')


GLOW = ('<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="10"/></filter></defs>')
CREDIT = (f'<text x="{W - 24}" y="{H - 24}" font-family="PB" font-size="16" fill="{MUTED}" '
          f'fill-opacity=".7" text-anchor="end">© OpenStreetMap</text>')


def svg_map(els, v, extra="", credit=True):
    order =["stream", "river", "residential", "living_street", "unclassified", "tertiary_link",
             "tertiary", "secondary_link", "secondary", "primary_link", "primary", "trunk_link",
             "trunk", "motorway_link", "motorway"]
    by = {k: [] for k in order}
    for e in els:
        k = e["tags"].get("highway") or e["tags"].get("waterway")
        if k in by and v.visible(e["geometry"]):
            by[k].append(" ".join(f"{x:.1f},{y:.1f}" for x, y in
                                  (v.xy(g["lat"], g["lon"]) for g in e["geometry"])))
    body = []
    for k in order:
        wm, col = STYLE[k]
        sw = max(wm * v.s, 1.1 if k != "stream" else 0.8)
        body.append(f'<g fill="none" stroke="{col}" stroke-width="{sw:.2f}" stroke-linecap="round" '
                    f'stroke-linejoin="round">' +
                    "".join(f'<polyline points="{p}"/>' for p in by[k]) + "</g>")
    w, h = v.cw, v.ch
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'{GLOW}<rect width="{w}" height="{h}" fill="{INK}"/>{"".join(body)}{extra}'
            f'{CREDIT if credit else ""}</svg>')


def svg_layer(body, w=W, h=H):
    """Camada transparente (sem ruas nem fundo), para compor por cima do mapa."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'{GLOW}{body}</svg>')


def route(v, pts, width=14):
    """A rota rosa (com brilho) pelos pontos `pts`, com o início em cream e o fim em rosa."""
    xy = [v.xy(*p) for p in pts]
    line = (f'points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in xy)}" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round"')
    (x1, y1), (x2, y2) = xy[0], xy[-1]
    return (f'<polyline {line} stroke="{PINK}" stroke-width="{width * 2.2:.0f}" opacity=".55" filter="url(#glow)"/>'
            f'<polyline {line} stroke="{PINK}" stroke-width="{width}"/>'
            f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="{width * 1.05:.0f}" fill="{CREAM}" stroke="{PINK}" stroke-width="6"/>'
            f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="{width * 0.75:.0f}" fill="{PINK}"/>')


def dot(v, p, r=16):
    return dot_xy(*v.xy(*p), r)


def dot_xy(x, y, r=16):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 3.2:.0f}" fill="{PINK}" opacity=".35" filter="url(#glow)"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 2.2:.0f}" fill="none" stroke="{PINK}" stroke-width="3" opacity=".6"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{PINK}"/>')


def render(svg, out, size=(W, H), scale=1, transparent=False):
    """SVG → PNG no Chrome headless (mesmo esquema do carrossel/render.sh).
    `size` é a janela em pixels CSS; `scale` multiplica a resolução; `transparent` tira o fundo."""
    face = "".join(f"@font-face{{font-family:{n};src:url('{(FONTS / f).as_uri()}')}}"
                   for n, f in (("PB", "Poppins-Bold.ttf"), ("PX", "Poppins-ExtraBold.ttf")))
    html = out.with_suffix(".html")
    bg = "transparent" if transparent else INK
    html.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{face}'
                    f'html,body{{margin:0;background:{bg}}}</style></head><body>{svg}</body></html>',
                    encoding="utf-8")
    chrome = (shutil.which("google-chrome") or shutil.which("chrome")
              or r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    extra = ["--default-background-color=00000000"] if transparent else []
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={scale}", "--virtual-time-budget=3000", *extra,
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={out.resolve()}",
                    html.resolve().as_uri()],
                   check=True, capture_output=True)
    html.unlink()


def ep1_labels(els, v):
    # cada rótulo fica num trecho da rua fora da rota: nada encosta na linha
    return "".join(svg_label(v, t, *street_along(els, n, c, d, s)) for t, n, c, d, s in [
        ("R. TIRADENTES", "Rua Tiradentes", ESQ_LAVAPES, 118, -1),        # depois da Lava Pés (sudeste)
        ("R. EDUARDO DE BRITO", "Rua Eduardo de Brito", ESQ_BRITO, 140, -1),  # a sudoeste da esquina
        ("R. LAVA PÉS", "Rua Lava Pés", ESQ_LAVAPES, 102, -1),             # o outro lado (nordeste)
    ])


def ep1_question(v, r):
    """O "?" logo depois do FIM, no prolongamento do último trecho da rota."""
    (ax, ay), (fx, fy) = v.xy(*r[-2]), v.xy(*r[-1])
    d = math.hypot(fx - ax, fy - ay)
    cx, cy = fx + (fx - ax) / d * 95, fy + (fy - ay) / d * 95
    return (f'<text x="{cx:.0f}" y="{cy + 68:.0f}" font-family="PX" font-size="190" '
            f'fill="{LILAC}" text-anchor="middle">?</text>')


def ep1(outdir):
    """Ep. 1: o trajeto até a Fagundes dos Reis (A), o bairro (B) e a cidade inteira (C)."""
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r = rota(els)
    c = meio(r)

    v = View(c, LARGURA["a"])
    render(svg_map(els, v, ep1_labels(els, v) + route(v, r) + ep1_question(v, r)),
           outdir / "ep1-a-trajeto.png")

    v = View(c, LARGURA["b"])
    render(svg_map(els, v, dot(v, FIM, 12)), outdir / "ep1-b-bairro.png")

    v = View(c, LARGURA["c"])
    render(svg_map(els, v, dot(v, FIM, 10)), outdir / "ep1-c-cidade.png")
    print("ok:", outdir)


def ep1_camadas(outdir):
    """Camadas do Ep. 1 para as animações do build_03.py: a linha que cresce e os zooms A→B e B→C.

    As vistas "grande" cobrem 3x a tela na mesma escala (o zoom-out pode ir até 1/3 sem sair da
    imagem) e as "3x" são a tela com o triplo da resolução (o zoom-in chega a 3x sem perder
    nitidez). Rota, "?", ponto e crédito saem em camadas transparentes, e as bases saem sem eles.
    """
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r = rota(els)
    c = meio(r)
    big, anchor_big = (3 * W, 3 * H), (3 * ANCORA[0], 3 * ANCORA[1])

    va = View(c, LARGURA["a"])
    vag = View(c, LARGURA["a"], anchor_big, big)
    render(svg_map(els, vag, ep1_labels(els, vag), credit=False), outdir / "ep1-a-grande.png", size=big)
    render(svg_layer(route(va, r)), outdir / "ep1-a-rota.png", transparent=True)
    render(svg_layer(ep1_question(va, r)), outdir / "ep1-a-interrogacao.png", transparent=True)
    for k in "bc":
        render(svg_map(els, View(c, LARGURA[k]), credit=False), outdir / f"ep1-{k}-3x.png", scale=3)
    render(svg_map(els, View(c, LARGURA["b"], anchor_big, big), credit=False),
           outdir / "ep1-b-grande.png", size=big)
    render(svg_layer(dot_xy(120, 120, 12), 240, 240), outdir / "ep1-ponto.png", (240, 240), transparent=True)
    render(svg_layer(CREDIT), outdir / "ep1-credito.png", transparent=True)

    # a rota na tela (vista A, 1x) e o deslocamento do FIM em metros a partir do MEIO, para o build
    # acompanhar o ponto em qualquer escala: x = âncora_x + dx*s, y = âncora_y + dy*s
    fx, fy = va.xy(*FIM)
    info = {
        "anchor": [va.ax, va.ay], "grande_anchor": list(anchor_big), "grande_size": list(big),
        "scale": {k: W / m for k, m in LARGURA.items()},
        "rota": [list(va.xy(*p)) for p in r], "rota_latlon": [list(p) for p in r],
        "fim_m": [(fx - va.ax) / va.s, (fy - va.ay) / va.s],
    }
    (outdir / "ep1-camadas.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print("ok:", outdir)


def ep2_labels(els, v):
    return ep1_labels(els, v) + svg_label(
        v, "R. CAP. ELEUTÉRIO", *street_along(els, "Rua Capitão Eleutério", FIM_EP2, 105, -1))


def ep2(outdir):
    """Ep. 2: o trajeto do Ep. 1 (até a Fagundes dos Reis, com o "?") e o mesmo trajeto uma rua
    adiante, até a Capitão Eleutério, com o "?" no novo fim."""
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r1, r2 = rota(els), rota(els, FIM_EP2)
    v = View(meio(r2), LARGURA["a"])
    render(svg_map(els, v, ep2_labels(els, v) + route(v, r1) + ep1_question(v, r1)),
           outdir / "ep2-a-antes.png")
    render(svg_map(els, v, ep2_labels(els, v) + route(v, r2) + ep1_question(v, r2)),
           outdir / "ep2-a-trajeto.png")
    print("ok:", outdir)


def ep2_camadas(outdir):
    """Camadas do Ep. 2 para o build: base com rótulos (vista "grande", como no Ep. 1), a rota inteira
    até FIM_EP2 (o build revela de `frac_fim_ep1` até 1) e os dois "?" (no FIM do Ep. 1 e no novo)."""
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r1, r2 = rota(els), rota(els, FIM_EP2)
    c = meio(r2)
    big, anchor_big = (3 * W, 3 * H), (3 * ANCORA[0], 3 * ANCORA[1])
    va, vag = View(c, LARGURA["a"]), View(c, LARGURA["a"], anchor_big, big)
    render(svg_map(els, vag, ep2_labels(els, vag), credit=False), outdir / "ep2-a-grande.png", size=big)
    render(svg_layer(route(va, r2)), outdir / "ep2-a-rota.png", transparent=True)
    render(svg_layer(ep1_question(va, r1)), outdir / "ep2-a-interrogacao-1.png", transparent=True)
    render(svg_layer(ep1_question(va, r2)), outdir / "ep2-a-interrogacao-2.png", transparent=True)
    render(svg_layer(CREDIT), outdir / "ep2-credito.png", transparent=True)

    xy = [va.xy(*p) for p in r2]
    acc = [0.0]
    for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
        acc.append(acc[-1] + math.hypot(x2 - x1, y2 - y1))
    info = {
        "anchor": [va.ax, va.ay], "grande_anchor": list(anchor_big), "grande_size": list(big),
        "rota": [list(p) for p in xy], "rota_latlon": [list(p) for p in r2],
        "frac_fim_ep1": acc[len(r1) - 1] / acc[-1],     # r1 é o começo de r2: fração da linha já vista no Ep. 1
    }
    (outdir / "ep2-camadas.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print("ok:", outdir)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "ep1"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "videos" / "mapas"
    {"ep1": ep1, "ep1-camadas": ep1_camadas, "ep2": ep2, "ep2-camadas": ep2_camadas}[what](out)
