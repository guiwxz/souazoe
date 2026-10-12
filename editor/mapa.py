"""Mapas da série "Os 6 dias da Zoe": ruas reais de Passo Fundo (OpenStreetMap) na identidade da Zoe.

Gera quadros 1080x1920 (SVG → Chrome headless → PNG). A malha de ruas é baixada uma vez
da Overpass API e fica em videos/osm-passo-fundo.json (não versionado). Ruas © OpenStreetMap.

Uso: python editor/mapa.py ep1 [pasta_saida]          (padrão: videos/mapas/)
     python editor/mapa.py ep1-camadas [pasta_saida]  (camadas para as animações do build_03.py)
     python editor/mapa.py ep2 [pasta_saida]          (Ep. 2: o trajeto uma rua adiante, antes e depois)
     python editor/mapa.py ep2-camadas [pasta_saida]  (camadas para as animações do build_04.py)
     python editor/mapa.py ep3 [pasta_saida]          (Ep. 3: prévia do trajeto inteiro e a vista com o Instituto Menino Deus)
     python editor/mapa.py ep3-camadas [pasta_saida]  (camadas para o build_05.py: bases em três níveis + JSON)
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
# Ep. 3 (câmeras de quarta e quinta, 23 e 24/09): o caminho inteiro da sexta, 08h43 a 08h50 (Guilherme, 05/10)
ESQ_CHICUTA = (-28.2584624, -52.4113319)   # Lava Pés × Coronel Chicuta: o fim da Lava Pés
CHICUTA_BRASIL = (-28.261891, -52.4092292)  # Coronel Chicuta × Av. Brasil, já do outro lado (pista sul)
NOVEMBRO_BRASIL = (-28.2626654, -52.4107416)  # 15 de Novembro × Av. Brasil (pista sul)
NOVEMBRO_MOROM = (-28.2637397, -52.4100944)
MOROM_TEIXEIRA = (-28.2642411, -52.411221)
TEIXEIRA_INDEP = (-28.2652719, -52.4105646)
FIM_EP3 = (-28.2681864, -52.4088005)       # Teixeira Soares × Dr. Benedito Acauã: o fim da Teixeira Soares
MENINO_DEUS = (-28.2753919, -52.4223373)   # Instituto Menino Deus (Nominatim): onde ela foi vista na quinta
NOVEMBRO_NORTE = (-28.2624004, -52.4108701)  # 15 de Novembro × Av. Brasil, pista norte (o rótulo da 15 vai daí para o norte)
# cada trecho: (rua, de, até); o caminho segue só pelos nós daquela rua
PERNAS_EP3 = [
    ("Rua Tiradentes", ESQ_BRITO, ESQ_LAVAPES),
    ("Rua Lava Pés", ESQ_LAVAPES, ESQ_CHICUTA),
    ("Rua Coronel Chicuta", ESQ_CHICUTA, CHICUTA_BRASIL),
    ("Avenida Brasil Centro", CHICUTA_BRASIL, NOVEMBRO_BRASIL),
    ("Rua 15 de Novembro", NOVEMBRO_BRASIL, NOVEMBRO_MOROM),
    ("Rua Morom", NOVEMBRO_MOROM, MOROM_TEIXEIRA),
    ("Rua Teixeira Soares", MOROM_TEIXEIRA, FIM_EP3),
]

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


def metros(a, b):
    return math.hypot((b[0] - a[0]) * 110574, (b[1] - a[1]) * 111320 * math.cos(math.radians(a[0])))


def rota_ruas(els, pernas=PERNAS_EP3):
    """O trajeto por uma sequência de ruas: em cada perna, o caminho mais curto (Dijkstra) só pelos
    nós da rua indicada. Devolve os pontos e o comprimento acumulado (m) no fim de cada perna."""
    pts, marcos = [], []
    for nome, de, ate in pernas:
        adj = {}
        for e in els:
            if e["tags"].get("name") == nome:
                g = [_k((p["lat"], p["lon"])) for p in e["geometry"]]
                for a, b in zip(g, g[1:]):
                    adj.setdefault(a, set()).add(b)
                    adj.setdefault(b, set()).add(a)
        src, dst = _k(de), _k(ate)
        if src not in adj or dst not in adj:
            raise ValueError(f"{de} ou {ate} não é um nó da {nome}")
        dist, prev, fila = {src: 0.0}, {src: None}, [(0.0, src)]
        while fila:
            fila.sort()
            c, u = fila.pop(0)
            if u == dst:
                break
            for w in adj[u]:
                nc = c + metros(u, w)
                if nc < dist.get(w, 1e18):
                    dist[w], prev[w] = nc, u
                    fila.append((nc, w))
        trecho, u = [], dst
        while u is not None:
            trecho.append(u)
            u = prev[u]
        trecho.reverse()
        pts += trecho if not pts else trecho[1:]
        marcos.append((nome, sum(metros(a, b) for a, b in zip(pts, pts[1:]))))
    return pts, marcos


def rotulo_rota(v, pts, frac, texto, lado=1, dist=34, size=24):
    """Rótulo paralelo à rota, a `frac` do comprimento (na tela), deslocado `dist` px para um lado."""
    xy = [v.xy(*p) for p in pts]
    seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:])]
    alvo, acc = frac * sum(seg), 0.0
    for (a, b), s in zip(zip(xy, xy[1:]), seg):
        if acc + s >= alvo:
            t = (alvo - acc) / s
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            nx, ny = -(b[1] - a[1]) / s, (b[0] - a[0]) / s
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if ang > 90:
                ang -= 180
            elif ang < -90:
                ang += 180
            x, y = x + nx * dist * lado, y + ny * dist * lado
            return (f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate({ang:.1f} {x:.1f} {y:.1f})" '
                    f'font-family="PB" font-size="{size}" letter-spacing="3" fill="{CREAM}" fill-opacity=".8" '
                    f'stroke="{INK}" stroke-width="7" paint-order="stroke" text-anchor="middle" '
                    f'dominant-baseline="central">{texto}</text>')
        acc += s
    return ""


def ep3_labels(els, v, pts_por_rua):
    out = []
    for nome, texto, frac, lado in [("Rua Lava Pés", "R. LAVA PÉS", .5, 1),
                                    ("Rua Coronel Chicuta", "R. CEL. CHICUTA", .45, 1),
                                    ("Rua Teixeira Soares", "R. TEIXEIRA SOARES", .55, -1)]:
        out.append(rotulo_rota(v, pts_por_rua[nome], frac, texto, lado))
    # a avenida e a Morom são curtas na rota: o rótulo vai no quarteirão seguinte, a nordeste, fora dela
    out.append(svg_label(v, "AV. BRASIL", *street_along(els, "Avenida Brasil Centro", CHICUTA_BRASIL, 150, 1), size=28))
    morom_ne = rota_ruas(els, [("Rua Morom", NOVEMBRO_MOROM, (-28.2630186, -52.4085979))])[0]  # até a Chicuta
    out.append(rotulo_rota(v, morom_ne, .68, "R. MOROM", dist=0, size=22))
    return "".join(out)


def ep3(outdir):
    """Ep. 3: prévia do trajeto inteiro (A) e a vista aberta com o Instituto Menino Deus (B)."""
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r, marcos = rota_ruas(els)
    por_rua = {p[0]: rota_ruas(els, [p])[0] for p in PERNAS_EP3}
    for nome, acc in marcos:
        print(f"  {nome:24s} até {acc:5.0f} m")
    total = marcos[-1][1]

    va = View(meio(r), 1500, anchor=(W / 2, 860))
    render(svg_map(els, va, ep3_labels(els, va, por_rua) + route(va, r, 12)), outdir / "ep3-a-trajeto.png")

    lats, lons = [p[0] for p in r + [MENINO_DEUS]], [p[1] for p in r + [MENINO_DEUS]]
    vb = View(((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2), 2900, anchor=(W / 2, 860))
    mx, my = vb.xy(*MENINO_DEUS)
    imd = (f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="44" fill="{LILAC}" opacity=".3" filter="url(#glow)"/>'
           f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="15" fill="{LILAC}"/>'
           f'<text x="{mx:.1f}" y="{my + 62:.1f}" font-family="PB" font-size="26" letter-spacing="3" '
           f'fill="{LILAC}" stroke="{INK}" stroke-width="7" paint-order="stroke" text-anchor="middle">'
           f'INSTITUTO MENINO DEUS</text>')
    render(svg_map(els, vb, route(vb, r, 9) + imd), outdir / "ep3-b-menino-deus.png")
    print(f"ok: {outdir} (trajeto: {total:.0f} m; do fim ao Instituto, em linha reta: "
          f"{metros(FIM_EP3, MENINO_DEUS):.0f} m)")


# Ep. 3: as camadas para o build_05. O mapa anda (acompanha a ponta da linha, abre até a cidade e até o
# Instituto), então as bases saem em três níveis de detalhe, todos na mesma projeção em metros a partir do
# meio da rota (x para leste, y para o sul): o build escolhe o nível de cada quadro e recorta. A rota, os
# nomes das ruas, o horário na ponta, o "?" e o Instituto são desenhados no build, a partir do JSON.
NIVEIS_EP3 = [
    # (nome, pixels por metro, margem em metros: oeste, leste, norte, sul) em volta da caixa de referência
    ("perto", 1.6, (700, 700, 700, 1000)),         # a rota (a vista que acompanha a ponta)
    ("meio", 0.6, (2000, 2000, 2600, 3000)),       # a rota e o Instituto (a rota inteira e a vista B)
    ("cidade", 0.15, None),                        # a área urbana inteira (BBOX + 3 km)
]
# nomes das ruas (o build acende cada um quando a Isabela fala): (texto, rua, como achar o ponto, lado)
# "rota": a tantos metros do início da rota, ao lado dela (lado ±1); "rua": a `dist` metros do cruzamento `de`, sobre
# a rua, no sentido que se afasta da rota (ep3_pela_rua).
ROTULOS_EP3 = [
    ("lavapes", "R. LAVA PÉS", {"rota": 800}, -1),
    # a Chicuta: no trecho ao norte da Lava Pés (ela dobrou para o sul), acima da ponta e fora das legendas
    ("chicuta", "R. CEL. CHICUTA", {"rua": "Rua Coronel Chicuta", "de": ESQ_CHICUTA, "dist": 165}, 0),
    # a avenida, a 15 de Novembro e a Morom ficam nos trechos que ela NÃO percorreu (longe da linha, uns dos outros
    # e da etiqueta do horário na ponta): a avenida a leste da Chicuta, a 15 ao norte da avenida, a Morom a oeste
    # da Teixeira
    ("brasil", "AV. BRASIL", {"rua": "Avenida Brasil Centro", "de": CHICUTA_BRASIL, "dist": 260}, 0),
    ("novembro", "R. 15 DE NOVEMBRO", {"rua": "Rua 15 de Novembro", "de": NOVEMBRO_NORTE, "dist": 150}, 0),
    ("morom", "R. MOROM", {"rua": "Rua Morom", "de": MOROM_TEIXEIRA, "dist": 100}, 0),
    # a Teixeira: no trecho ao norte da Morom (ela desceu para o sul), longe da esquina, fora das legendas
    ("teixeira", "R. TEIXEIRA SOARES", {"rua": "Rua Teixeira Soares", "de": MOROM_TEIXEIRA, "dist": 185}, 0),
    ("independencia", "R. INDEPENDÊNCIA", {"rua": "Rua Independência", "de": TEIXEIRA_INDEP, "dist": 175}, 0),
]


def ep3_pela_rua(els, nome, de, dist, pm, ref):
    """Ponto (m) e direção a `dist` metros do cruzamento `de`, andando pela rua `nome` (passando de um trecho do OSM
    para o seguinte, sempre pelo vizinho mais reto), no sentido cujo ponto fica mais longe da rota `pm`."""
    adj = {}
    for e in els:
        if e["tags"].get("name") == nome:
            g = [_k((q["lat"], q["lon"])) for q in e["geometry"]]
            for a, b in zip(g, g[1:]):
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    src = _k(de)
    if src not in adj:
        raise ValueError(f"{de} não é um nó da {nome}")
    cands = []
    for primeiro in adj[src]:
        cam, ant, u, andado = [src, primeiro], src, primeiro, metros(src, primeiro)
        while andado < dist:
            prox = [w for w in adj.get(u, ()) if w not in cam]
            if not prox:
                break
            ux, uy = u[1] - ant[1], u[0] - ant[0]

            def curva(w):
                wx, wy = w[1] - u[1], w[0] - u[0]
                return -(ux * wx + uy * wy) / (math.hypot(ux, uy) * math.hypot(wx, wy) + 1e-12)
            ant, u = u, min(prox, key=curva)
            cam.append(u)
            andado += metros(ant, u)
        if andado < dist:
            continue
        a, b = ep3_metros(cam[-2], ref), ep3_metros(cam[-1], ref)
        sg = math.hypot(b[0] - a[0], b[1] - a[1])
        f = 1 - (andado - dist) / sg
        q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        longe = min(math.hypot(q[0] - c[0], q[1] - c[1]) for c in pm)
        cands.append((longe, q, (b[0] - a[0], b[1] - a[1])))
    if not cands:
        raise ValueError(f"a {nome} não tem {dist} m a partir de {de}")
    _, q, dxy = max(cands, key=lambda c: c[0])
    return q, dxy


def ep3_metros(p, ref):
    """(lat, lon) → metros (leste, sul) a partir de `ref`, na mesma conta da View."""
    kx = 111320 * math.cos(math.radians(ref[0]))
    return ((p[1] - ref[1]) * kx, (ref[0] - p[0]) * 110574)


def ep3_camadas(outdir):
    """Camadas do Ep. 3: as três bases (sem rótulos, sem crédito) e ep3-camadas.json com a rota em metros, os
    marcos de cada rua, os cruzamentos, os pontos dos nomes das ruas e o Instituto Menino Deus."""
    els = load()
    outdir.mkdir(parents=True, exist_ok=True)
    r, marcos = rota_ruas(els)
    ref = meio(r)
    pm = [ep3_metros(p, ref) for p in r]
    md = ep3_metros(MENINO_DEUS, ref)
    xs, ys = [p[0] for p in pm], [p[1] for p in pm]
    caixa = (min(xs), max(xs), min(ys), max(ys))
    caixa_md = (min(caixa[0], md[0]), max(caixa[1], md[0]), min(caixa[2], md[1]), max(caixa[3], md[1]))
    s_, w_, n_, e_ = BBOX
    cid = (ep3_metros((n_, w_), ref), ep3_metros((s_, e_), ref))
    niveis = []
    for nome, s, mg in NIVEIS_EP3:
        if mg is None:
            x0, x1, y0, y1 = cid[0][0] - 3000, cid[1][0] + 3000, cid[0][1] - 3000, cid[1][1] + 3000
        else:
            cx = caixa if nome == "perto" else caixa_md
            x0, x1, y0, y1 = cx[0] - mg[0], cx[1] + mg[1], cx[2] - mg[2], cx[3] + mg[3]
        size = (int(math.ceil((x1 - x0) * s)), int(math.ceil((y1 - y0) * s)))
        anchor = (-x0 * s, -y0 * s)
        v = View(ref, W / s, anchor, size)
        f = outdir / f"ep3-{nome}.png"
        render(svg_map(els, v, credit=False), f, size=size)
        niveis.append({"nome": nome, "arquivo": f.name, "s": s, "anchor": list(anchor), "size": list(size)})
        print(f"  {nome}: {size[0]}x{size[1]} px ({s} px/m)")

    acc = [0.0]
    for a, b in zip(r, r[1:]):
        acc.append(acc[-1] + metros(a, b))

    def na_rota(d):
        """Ponto (m) e direção da rota a d metros do início."""
        for i in range(len(acc) - 1):
            if acc[i + 1] >= d:
                u = (d - acc[i]) / (acc[i + 1] - acc[i])
                (x1, y1), (x2, y2) = pm[i], pm[i + 1]
                return (x1 + (x2 - x1) * u, y1 + (y2 - y1) * u), (x2 - x1, y2 - y1)
        return pm[-1], (pm[-1][0] - pm[-2][0], pm[-1][1] - pm[-2][1])

    rotulos = []
    for chave, texto, onde, lado in ROTULOS_EP3:
        if "rota" in onde:
            (x, y), (dx, dy) = na_rota(onde["rota"])
        else:                     # pela rua, a `dist` metros do cruzamento, no sentido que se afasta da rota
            (x, y), (dx, dy) = ep3_pela_rua(els, onde["rua"], onde["de"], onde["dist"], pm, ref)
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90:
            ang -= 180
        elif ang < -90:
            ang += 180
        rotulos.append({"chave": chave, "texto": texto, "x": x, "y": y, "ang": ang, "lado": lado})

    cruz = {}
    for nome in ("ESQ_LAVAPES", "FIM", "FIM_EP2", "ESQ_CHICUTA", "CHICUTA_BRASIL", "NOVEMBRO_BRASIL",
                 "NOVEMBRO_MOROM", "MOROM_TEIXEIRA", "TEIXEIRA_INDEP", "FIM_EP3"):
        k = _k(globals()[nome])
        cruz[nome] = next(acc[i] for i, q in enumerate(r) if _k(q) == k)
    info = {"ref": list(ref), "niveis": niveis, "rota": [list(p) for p in pm], "acc": acc,
            "marcos": [[n, a] for n, a in marcos], "cruzamentos": cruz, "rotulos": rotulos,
            "menino_deus": list(md), "cidade": [list(cid[0]), list(cid[1])]}
    (outdir / "ep3-camadas.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    print("ok:", outdir, f"(rota {acc[-1]:.0f} m)")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "ep1"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "videos" / "mapas"
    {"ep1": ep1, "ep1-camadas": ep1_camadas, "ep2": ep2, "ep2-camadas": ep2_camadas,
     "ep3": ep3, "ep3-camadas": ep3_camadas}[what](out)
