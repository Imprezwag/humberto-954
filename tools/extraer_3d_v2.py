"""Extrae del DXF del plano la geometría para el recorrido 3D (muros, aberturas, escalera).
Versión 2: suma cochera cerrada, altillo sobre la cochera, techos y entretecho con el tanque.
Uso: python3 tools/extraer_3d_v2.py plano/Humberto954_plano.dxf recorrido-v2/casa.json"""
import sys, json, math, ezdxf
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely.validation import make_valid

DX = 13.0          # la planta alta está dibujada corrida 13 m a la derecha
doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
def floor_of(x): return 1 if x > 11 else 0
def loc(x, y):     # a coordenadas de planta baja
    return (x - DX, y) if x > 11 else (x, y)

walls = {0: [], 1: []}
for e in msp.query('LWPOLYLINE[layer=="MUROS"]'):
    pts = [loc(*p) for p in e.get_points('xy')]
    f = floor_of(list(e.get_points('xy'))[0][0])
    if e.closed and len(pts) >= 3:
        g = make_valid(Polygon(pts))
    else:   # baranda abierta de la terraza
        g = LineString(pts).buffer(0.05, cap_style=2)
    walls[f].append(g)
W = {f: unary_union(v) for f, v in walls.items()}

# carpinterías: letra más cercana
carp = [(loc(t.dxf.insert.x, t.dxf.insert.y), floor_of(t.dxf.insert.x), t.dxf.text.strip('?'))
        for t in msp.query('TEXT[layer=="TEXTOS-CARPINTERIA"]')]
ALTO = {'J': 1.30, 'K': 1.30, 'L': 1.10, 'M': 1.10, 'N': 0.80, 'O': 0.50, 'I': 1.90}
def letra(c, f, opts):
    best = min((math.dist(c, p), l) for p, ff, l in carp if ff == f and l in opts)
    return best[1]

windows = []
for e in msp.query('LWPOLYLINE[layer=="VENTANAS"]'):
    raw = list(e.get_points('xy'))
    if len(raw) != 4: continue
    f = floor_of(raw[0][0]); pts = [loc(x, y) for x, y, *_ in raw]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    r = (min(xs), min(ys), max(xs), max(ys))
    l = letra(((r[0]+r[2])/2, (r[1]+r[3])/2), f, ALTO)
    windows.append({"f": f, "r": [round(v, 3) for v in r], "l": l, "h": ALTO[l]})

doors = []
for a in msp.query('ARC[layer=="PUERTAS"]'):
    f = floor_of(a.dxf.center.x); cx, cy = loc(a.dxf.center.x, a.dxf.center.y); R = a.dxf.radius
    ends = [(cx + R*math.cos(math.radians(t)), cy + R*math.sin(math.radians(t))) for t in (a.dxf.start_angle, a.dxf.end_angle)]
    # la hoja abierta es la LINE que sale del centro; el otro extremo del arco es la hoja cerrada
    leaf = None
    for ln in msp.query('LINE[layer=="PUERTAS"]'):
        s = loc(ln.dxf.start.x, ln.dxf.start.y); en = loc(ln.dxf.end.x, ln.dxf.end.y)
        if floor_of(ln.dxf.start.x) == f and math.dist(s, (cx, cy)) < 1e-3: leaf = en
    closed = max(ends, key=lambda p: math.dist(p, leaf)) if leaf else ends[0]
    ox, oy = leaf[0]-cx, leaf[1]-cy; n = math.hypot(ox, oy); ox, oy = ox/n, oy/n
    # espesor del muro: hacia atrás de la hoja
    probe = LineString([(cx - ox*0.01, cy - oy*0.01), (cx - ox*0.45, cy - oy*0.45)])
    hit = probe.intersection(W[f].buffer(0.03))
    t = 0.15 if hit.is_empty else max(0.1, min(0.35, hit.length + 0.01))
    p0 = (cx, cy); p1 = closed
    lint = Polygon([p0, p1, (p1[0]-ox*t, p1[1]-oy*t), (p0[0]-ox*t, p0[1]-oy*t)])
    doors.append({"f": f, "hinge": [cx, cy], "closed": list(p1), "open": list(leaf), "w": R, "lint": [list(map(lambda v: round(v, 3), c)) for c in lint.exterior.coords[:-1]]})


# ---------- escalera (interpretación del dibujo de ambas plantas) ----------
from shapely.affinity import translate
PB_FLOOR, PA_FLOOR = 0.40, 3.55
def fan(pv, a0, a1, R=2.0):
    import numpy as np
    ang = [math.radians(a0 + (a1 - a0) * k / 8) for k in range(9)]
    return Polygon([pv] + [(pv[0] + R*math.cos(a), pv[1] + R*math.sin(a)) for a in ang])
treads = []
A = box(0.15, 6.95, 1.0, 7.9)
for a0, a1 in [(-90, -101.9), (-101.9, -120.1), (-120.1, -140.5), (-140.5, -160.6), (-160.6, -180)]:
    treads.append(("A", fan((1.0, 7.9), a0, a1).intersection(A)))
for y in [7.9, 8.15, 8.4, 8.65, 8.9]:
    treads.append(("B", box(0.15, y, 1.0, y + 0.25)))
C = box(0.15, 9.15, 1.0, 10.0)
for a0, a1 in [(180, 154.8), (154.8, 135), (135, 115.2), (115.2, 90)]:
    treads.append(("C", fan((1.0, 9.15), a1, a0).intersection(C)))
for x in [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]:
    treads.append(("D", box(x, 9.15, x + 0.25, 10.0)))
treads.append(("D", box(2.75, 9.15, 3.05, 10.0)))
N = len(treads) + 1
RISE = (PA_FLOOR - PB_FLOOR) / N
stairs = [{"s": seg, "h": round(PB_FLOOR + (k + 1) * RISE, 4), "g": g} for k, (seg, g) in enumerate(treads)]
stair_all = unary_union([t["g"] for t in stairs])
upper = [t for t in stairs if t["s"] in "CD"]
# acceso a la escalera desde el hall: se abre el muro x 1,00-1,20 en el primer tramo
W[0] = W[0].difference(box(0.99, 6.95, 1.21, 7.9))
terraza = box(4.25, 10.0, 6.6, 14.0)
def polys(g):
    g = g.buffer(0)
    gs = [g] if g.geom_type == 'Polygon' else list(getattr(g, 'geoms', []))
    out = []
    for p in gs:
        if p.geom_type != 'Polygon' or p.area < 1e-4: continue
        out.append({"o": [[round(x, 3), round(y, 3)] for x, y in p.exterior.coords[:-1]],
                    "h": [[[round(x, 3), round(y, 3)] for x, y in r.coords[:-1]] for r in p.interiors]})
    return out

# contornos de cada planta (para losas)
foot = {}
for f in (0, 1):
    hull = unary_union([W[f]] + [box(*w["r"]) for w in windows if w["f"] == f] + [Polygon(d["lint"]) for d in doors if d["f"] == f])
    hb = hull.buffer(0.05)
    big = max(hb.geoms, key=lambda p: p.area) if hb.geom_type != 'Polygon' else hb
    foot[f] = Polygon(big.exterior).buffer(-0.05, join_style=2)

# ---------- agregados v2 (relato de Santiago, no están en el plano) ----------
ATTIC = 6.30                                   # piso del entretecho (arriba de la losa de cielorraso)
LOSA_COCH_B, LOSA_COCH_T = 3.05, 3.25          # losa de la cochera: un escalón por debajo de la planta alta (dato de Santiago)
abertura = box(5.69, 4.40, 6.01, 5.05)          # puerta chica 0,65 x 1,70 a mitad de la pared (foto del dormitorio)
W[1] = W[1].difference(abertura)
placard = box(0.15, 6.2, 1.7, 6.8)              # placard del dormitorio chico (Rop.)
ladder = []
for i in range(8):          # escalera de mano apoyada contra la medianera (dato de Santiago)
    x1 = 1.0 - 0.05 * i
    ladder.append({"s": "L", "h": round(PA_FLOOR + (i + 1) * (ATTIC - PA_FLOOR) / 8, 4), "g": box(x1 - 0.05, 6.25, x1, 6.75)})
ladder.append({"s": "L", "h": ATTIC, "g": box(0.15, 6.2, 0.6, 6.8)})   # arriba, a nivel del entretecho
stairs += ladder
stairs.append({"s": "P", "h": 3.40, "g": box(6.0, 4.40, 6.35, 5.05)})   # el escalón para bajar al altillo
stair_all = unary_union([stair_all] + [t["g"] for t in ladder])

# ---------- piezas con altura ----------
pieces = []   # {o,h,b,t,k}
PG = []
def add(g, b, t, k, f):
    for p in polys(g):
        p.update(b=round(b, 3), t=round(t, 3), k=k, f=f); pieces.append(p)
        PG.append((Polygon(p['o'], p['h']), b, t, k, f))
def add_split(g, b, t, f, regions, k='muro'):
    for reg, kk in regions:
        add(g.intersection(reg), b, t, kk, f); g = g.difference(reg)
    add(g, b, t, k, f)
WIN = {f: unary_union([box(*w["r"]) for w in windows if w["f"] == f]) for f in (0, 1)}
# planta baja
w0 = W[0].difference(WIN[0])
jardin = box(-1, -1, 5.75, 1.5)
used = jardin
add(w0.intersection(jardin), 0, 1.0, "ladrillo", 0)
for t in upper:
    add(w0.intersection(t["g"]).difference(used), 0, t["h"] - 0.2, "muro", 0); used = used.union(t["g"])
med = box(8.6, -1, 9, 13)
add(w0.intersection(med).intersection(box(8, -1, 10, 6.75)), 0, LOSA_COCH_B, "muro", 0)
add(w0.intersection(med).difference(box(8, -1, 10, 6.75)), 0, 2.6, "muro", 0)
poste = box(2.45, 1.55, 2.75, 1.8)     # columna del porch: llega al techito de tejas
add(w0.intersection(poste), 0, 2.98, "muro", 0)
add_split(w0.difference(used).difference(med).difference(poste), 0, PA_FLOOR, 0, [(box(5.65, 1.4, 6.05, 2.55), "ladrillo")])
# cochera cerrada: pilares y dinteles de los portones B (frente) y B' (pasante)
for y0 in (0.0, 6.6):
    kk = "muro" if y0 else "ladrillo"
    add(box(6.0, y0, 6.2, y0 + 0.15), 0.15 if y0 else 0, LOSA_COCH_B, kk, 0)
    add(box(8.46, y0, 8.66, y0 + 0.15), 0.15 if y0 else 0, LOSA_COCH_B, kk, 0)
    add(box(6.2, y0, 8.46, y0 + 0.15), 2.10, LOSA_COCH_B, kk, 0)
# altillo: muretes bajos de frente y fondo (el resto lo cierra el techo)
add(box(5.7, 4.40, 6.0, 5.05), PA_FLOOR + 1.70, 6.15, "muro", 1)      # dintel de la puerta chica
# frente de la cochera: borde de la losa en ladrillo
add(box(6.0, 0.0, 8.81, 0.15), LOSA_COCH_B, LOSA_COCH_T, "ladrillo", 0)
# tanque en el entretecho, arriba del baño de planta alta, apoyado sobre sus muros (dato de Santiago)
add(box(3.76, 7.43, 3.96, 8.97), ATTIC, 6.55, "muro", 2); add(box(5.72, 7.43, 5.92, 8.97), ATTIC, 6.55, "muro", 2)
add(box(3.76, 7.43, 5.92, 8.97), 6.55, 7.13, "tanque", 2)
# hogar del living, junto a la medianera (videos): base de piedra y campana de madera
add(box(0.15, 4.05, 0.80, 4.85), 0, PB_FLOOR + 0.45, "piedra", 0)
add(box(0.15, 4.15, 0.70, 4.75), PB_FLOOR + 1.45, 3.30, "machimbre", 0)
# planta alta
w1 = W[1].difference(WIN[1])
baranda = unary_union([g for g in walls[1] if g.geom_type == 'Polygon' and g.area < 0.6 and g.bounds[1] > 9.9 and g.bounds[2] > 6.3])
add(w1.intersection(baranda), 3.40, 4.40, "baranda", 1)
hueco = box(0.99, 6.94, 1.21, 9.16)    # baranda de mampostería con tapa de madera sobre el hueco de la escalera
add(w1.intersection(hueco), PA_FLOOR, PA_FLOOR + 0.92, "muro", 1)
add(w1.intersection(hueco), PA_FLOOR + 0.92, PA_FLOOR + 0.97, "madera", 1)
add_split(w1.difference(baranda).difference(hueco), PA_FLOOR, 6.15, 1, [(box(-1, 2.4, 7, 2.82), "tablas")])
# ventanas: antepecho, dintel y vidrio
for w in windows:
    fl = PB_FLOOR if w["f"] == 0 else PA_FLOOR; top = PA_FLOOR if w["f"] == 0 else 6.15
    g = box(*w["r"]); sill = fl + 2.10 - w["h"]
    kk = "tablas" if w["f"] == 1 and w["r"][3] < 2.9 else "muro"
    add(g, 0 if w["f"] == 0 else fl, sill, kk, w["f"]); add(g, fl + 2.10, top, kk, w["f"])
    add(g, sill, fl + 2.10, "vidrio", w["f"])
# dinteles de puertas (no en el cerco ni en los portones de la cochera)
for d in doors:
    if d["f"] == 0 and (d["hinge"][1] < 1.5 or d["hinge"][0] > 6.1): continue
    if d["f"] == 1 and Polygon(d["lint"]).intersects(placard.buffer(0.1)): continue   # placard de la escalera: puerta hasta el cielorraso
    fl = PB_FLOOR if d["f"] == 0 else PA_FLOOR; top = PA_FLOOR if d["f"] == 0 else 6.15
    add(Polygon(d["lint"]), fl + 2.10, top, "muro", d["f"])

# ---------- locales (para pisos y para saber dónde estás) ----------
TIPO = {"Dormitorio": "parquet", "Terraza": "calcareo", "Lavadero": "granitico", "Cochera": "granitico_verde", "Baño": "baldosa_blanca"}
TIPO1 = {"Baño": "granito_negro"}
rooms = []
labels = []
for t in msp.query('TEXT[layer=="TEXTOS-LOCALES"]'):
    s = t.dxf.text
    if s.isupper() and len(s) > 3 and t.dxf.insert.y > 0 and "LINEA" not in s and "PLANTA" not in s and "PATIO" not in s and not s.startswith("N.P"):
        labels.append((floor_of(t.dxf.insert.x), s.title(), loc(t.dxf.insert.x, t.dxf.insert.y)))
for f in (0, 1):
    cut = unary_union([W[f], WIN[f]] + [Polygon(d["lint"]).buffer(0.01) for d in doors if d["f"] == f])
    free = foot[f].difference(cut)
    if f == 1: free = free.difference(stair_all)
    comps = list(free.geoms) if free.geom_type != 'Polygon' else [free]
    for c in comps:
        if c.area < 0.3: continue
        parts = [c]
        if f == 0 and c.bounds[1] < 1.0:   # jardín y porch son un mismo espacio abierto
            parts = [c.intersection(box(-1, -1, 9, 1.5)), c.difference(box(-1, -1, 9, 1.5))]
        for c2 in parts:
            names = [n for ff, n, p in labels if ff == f and c2.buffer(0.3).contains(Point(p[0], p[1] - 0.2))]
            name = " / ".join(dict.fromkeys(names)) or ("Jardín" if c2.bounds[3] <= 1.51 else ("Placard" if c2.area < 2 else "Paso"))
            for p in polys(c2):
                key = names[0] if names else name
                rooms.append({"f": f, "n": name, "piso": (TIPO1.get(key) if f == 1 else None) or TIPO.get(key, "granitico"), **p})
# vanos de puertas: piso del local vecino (si no, el vano queda como hueco)
for d in doors:
    if d["f"] == 0 and (d["hinge"][1] < 1.5 or d["hinge"][0] > 6.1): continue
    g = Polygon(d["lint"]).buffer(0.012, join_style=2)
    near = [r for r in rooms if r["f"] == d["f"] and Polygon(r["o"], r["h"]).intersects(g.buffer(0.05))]
    if not near: continue
    r0 = max(near, key=lambda r: Polygon(r["o"], r["h"]).area)
    rooms.append({"f": d["f"], "n": r0["n"], "piso": r0["piso"], "vano": True, **polys(g)[0]})
rooms.append({"f": 0, "n": "Cochera", "piso": "granitico_verde", **polys(box(6.0, 0.15, 8.66, 6.6).difference(W[0]))[0]})
rooms.append({"f": 0, "n": "Pasante", "piso": "baldosa", **polys(box(6.0, 6.75, 8.66, 12.0).difference(W[0]))[0]})
rooms.append({"f": 1, "n": "Altillo sobre la cochera", "piso": "cemento", **polys(box(6.0, 0.15, 8.66, 6.6))[0]})
rooms.append({"f": 1, "n": "Dormitorio", "piso": "parquet", "vano": True, **polys(box(5.69, 4.40, 6.01, 5.05))[0]})
techo1 = foot[1].difference(terraza).difference(placard)
rooms.append({"f": 2, "n": "Entretecho", "piso": "cemento", **polys(techo1)[0]})
def zfor(r):
    f, n = r["f"], r["n"]
    if f == 2: return ATTIC
    if f == 1: return 3.40 if n == "Terraza" else LOSA_COCH_T if n.startswith("Altillo") else PA_FLOOR
    return {"Jardín": 0.03, "Porch": 0.30, "Cochera": 0.15, "Pasante": 0.15}.get(n, PB_FLOOR)
for r in rooms: r["z"] = zfor(r)

# ---------- revestimientos interiores: una lámina por cara de muro, con el color del local ----------
CIELO = lambda r: 2.75 if r["n"] == "Cochera" else 3.30 if r["f"] == 0 else 6.15
SIN = ("Jardín", "Porch", "Pasante", "Terraza", "Altillo sobre la cochera", "Entretecho")
skins = []
for i, r in enumerate(rooms):
    if r["n"] in SIN or r.get("vano"): continue
    poly = Polygon(r["o"], r["h"]); z0r, z1r = r["z"], CIELO(r)
    for ring in [r["o"]] + r["h"]:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            L = math.dist(a, b)
            if L < 0.02: continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2; nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
            if poly.contains(Point(mx + nx * 0.05, my + ny * 0.05)): nx, ny = -nx, -ny
            o = Point(mx + nx * 0.05, my + ny * 0.05)
            for g, pb, pt, k, pf in PG:
                if k == "vidrio" or not g.contains(o): continue
                z0, z1 = max(pb, z0r), min(pt, z1r)
                if z1 - z0 > 0.02:
                    e = 0.004
                    skins.append([i, round(a[0] - nx*e, 3), round(a[1] - ny*e, 3), round(b[0] - nx*e, 3), round(b[1] - ny*e, 3), round(z0, 3), round(z1, 3)])

slabs = []
def slab(g, b, t, k):
    for p in polys(g): p.update(b=b, t=t, k=k); slabs.append(p)
pb_house = foot[0].intersection(box(-1, 1.5, 7, 20))
slab(pb_house.difference(foot[1]).intersection(box(-1, 2.6, 9, 20)), 3.30, 3.45, "techo0")   # el porch tiene techo de tejas propio
slab(foot[1].difference(stair_all), 3.30, PA_FLOOR - 0.01, "losa")
slab(techo1, 6.15, ATTIC, "techo1")
slab(box(6.0, 0.0, 8.81, 6.75), LOSA_COCH_B, LOSA_COCH_T, "losa")

out = {"pieces": pieces, "rooms": rooms, "slabs": slabs, "doors": doors, "skins": skins,
       "stairs": [{**polys(t["g"])[0], "z": t["h"], "s": t["s"]} for t in stairs],
       "foot0": polys(foot[0]),
       "fondo": {"galpon": [0.15, 31.85, 5.5, 34.85, 3.0], "parrilla": [6.0, 33.6, 8.66, 34.85], "puerta_patio": [1.7, 14.0]},
       "roof": {"main": {"yr": 8.18, "hr": 8.85, "kF": 0.4225, "kB": 0.4225, "x0": -0.15, "x1": 6.3, "y0": 2.1, "y1": 14.25, "notch": [4.25, 10.0]},
                # altillo: piso plano (losa) y techo a dos aguas que arranca del piso; 2 m en la cumbrera, que cae sobre la puerta chica
                "coch": {"yr": 4.72, "hr": 5.32, "kF": 0.4386, "kB": 1.0197, "x0": 6.0, "x1": 8.81, "y0": -0.30, "y1": 7.0},
                "porch": {"x0": 0.15, "x1": 5.72, "yw": 2.5, "hw": 3.32, "ye": 1.25, "he": 2.85}}, "terraza": list(terraza.bounds), "lote": [0, 0, 8.66, 35.0]}
json.dump(out, open(sys.argv[2], "w"))
print(len(skins), "revestimientos", len(pieces), "piezas", len(slabs), "losas", len(stairs), "escalones, alzada", round(RISE, 3))
for r in rooms: print(r["f"], r["n"], r["piso"], round(Polygon(r["o"]).area, 2))
print(len(json.dumps(out))//1024, "KB")
