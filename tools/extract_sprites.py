"""Découpe et prépare les planches de sprites fournies par l'équipe.

Usage (depuis la racine du projet) :
    .venv/bin/python tools/extract_sprites.py

Entrées (fond « damier » peint, sauf le roi déjà transparent) :
    assets/finn/finn-muscle-niveau-1.png       Finn, muscles niveau 1
    assets/finn/finn-muscle-niveau-2-à-4.png   Finn, muscles niveaux 2, 3 et 4 (3 panneaux)
    assets/monstre-niveau-1/zombie.png         monstre niveau 1 (zombie)
    assets/monstre-niveau-2/monstre.png        monstre niveau 2 (sorcier squelette, champion)
    assets/Boss-final/boss.png                 boss final (Roi des Glaces)
    assets/monstre-niveau-3/monstre.png        monstre niveau 3 (roi orange), damier gris clair
    assets/boos-final-2/boss-2.png             boss final n°2 (majordome menthe)
Sorties (assets/sprites/) :
    finn_muscle1..4.png, finn_old1.png, finn_old2.png + finn.json
    monster_zombie.png, monster_lich.png, monster_boss.png + monsters.json
    monster_king.png, monster_butler.png
    proj_fireball.png, proj_ice.png, proj_king_fire.png

Les planches sont découpées automatiquement (détection des sprites, rangés en
lignes) : les tables *_ANIMS disent quelle ligne / quelle position correspond à
quelle animation. Le vieux Finn (vieillissement) est dérivé du niveau 1.
"""
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sprites"
OUTLINE = (27, 20, 38, 255)


# --------------------------------------------------------------------------
# Détourage et détection
# --------------------------------------------------------------------------
def _is_checker(c, strict=False):
    r, g, b = c
    m = (r + g + b) / 3
    if strict:
        return max(r, g, b) - min(r, g, b) <= 26 and b - r >= 10 and 100 <= m <= 200
    return max(r, g, b) - min(r, g, b) <= 32 and b - r >= 3 and 80 <= m <= 222


def _is_light_checker(c, strict=False):
    """Damier gris clair (planche du majordome) : gris très peu saturé et lumineux."""
    r, g, b = c
    if strict:
        return max(r, g, b) - min(r, g, b) <= 10 and min(r, g, b) >= 170
    return max(r, g, b) - min(r, g, b) <= 18 and min(r, g, b) >= 150


def remove_checker(im, is_checker=_is_checker):
    """Supprime le damier peint en remplissant depuis le fond.

    is_checker décrit le damier : gris-bleu par défaut, gris clair pour la
    planche du majordome menthe (_is_light_checker).
    """
    im = im.convert("RGB")
    w, h = im.size
    px = im.load()
    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            if is_checker(px[x, y], strict=True):
                q.append((x, y))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not is_checker(px[x, y]):
            continue
        bg[i] = 1
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            if not bg[y * w + x]:
                op[x, y] = px[x, y] + (255,)
    return out


def components(cut, min_area=300, k=2):
    """Boîtes (x1, y1, x2, y2, aire) des sprites, détectées à demi-résolution."""
    w0, h0 = cut.size
    small = cut.getchannel("A").resize((w0 // k, h0 // k), Image.NEAREST)
    w, h = small.size
    m = small.load()
    seen = bytearray(w * h)
    boxes = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0 * w + x0] or not m[x0, y0]:
                continue
            q = deque([(x0, y0)])
            seen[y0 * w + x0] = 1
            x1 = x2 = x0
            y1 = y2 = y0
            n = 0
            while q:
                x, y = q.popleft()
                n += 1
                x1, x2, y1, y2 = min(x1, x), max(x2, x), min(y1, y), max(y2, y)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and m[nx, ny]:
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            if n * k * k >= min_area:
                boxes.append((x1 * k, y1 * k, x2 * k + k, y2 * k + k, n * k * k))
    return boxes


def group_rows(boxes):
    """Range les boîtes en lignes (de haut en bas), chaque ligne triée de gauche à droite."""
    boxes = sorted(boxes, key=lambda b: (b[1] + b[3]) / 2)
    heights = sorted(b[3] - b[1] for b in boxes if b[4] >= 2000) or [50]
    med = heights[len(heights) // 2]
    rows = []
    for b in boxes:
        cy = (b[1] + b[3]) / 2
        if rows and abs(cy - rows[-1][0]) < med * 0.5:
            rows[-1][1].append(b)
            rows[-1][0] = sum((c[1] + c[3]) / 2 for c in rows[-1][1]) / len(rows[-1][1])
        else:
            rows.append([cy, [b]])
    return [sorted(r[1], key=lambda b: b[0]) for r in rows]


def harden_alpha(im, threshold=110):
    im = im.copy()
    p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            p[x, y] = (r, g, b, 255) if a > threshold else (0, 0, 0, 0)
    return im


def scaled_crop(cut, box, scale, max_w=None):
    x1, y1, x2, y2 = box[:4]
    if max_w:
        x2 = min(x2, x1 + max_w)
    crop = cut.crop((x1 - 2, y1 - 2, x2 + 2, y2 + 2))
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    return harden_alpha(crop.resize(size, Image.LANCZOS))


def opaque_bbox(im):
    return im.getchannel("A").getbbox()


def body_center_x(im):
    """Centre horizontal du corps (moyenne des pixels opaques de la partie basse)."""
    p = im.load()
    bb = opaque_bbox(im)
    top = bb[1] + (bb[3] - bb[1]) * 0.4
    xs = [x for y in range(int(top), bb[3]) for x in range(bb[0], bb[2]) if p[x, y][3]]
    return sum(xs) / len(xs) if xs else (bb[0] + bb[2]) / 2


def pack(images, anchors, min_w=0, min_h=0, pad=2):
    """Place chaque image dans une case commune : ancre au centre, pieds en bas."""
    boxes = [opaque_bbox(im) for im in images]
    half = max(max(ax - bb[0], bb[2] - ax) for bb, ax in zip(boxes, anchors))
    cell_w = max(min_w, 2 * math.ceil(half) + 2 * pad)
    cell_h = max(min_h, max(bb[3] - bb[1] for bb in boxes) + 2 * pad)
    cells = []
    for im, bb, ax in zip(images, boxes, anchors):
        cell = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
        cell.alpha_composite(im, (round(cell_w / 2 - ax), cell_h - pad - bb[3]))
        cells.append(cell)
    return cells, cell_w, cell_h


def save_strip(cells, name):
    w, h = cells[0].size
    strip = Image.new("RGBA", (w * len(cells), h), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        strip.alpha_composite(c, (i * w, 0))
    strip.save(OUT / name)


# --------------------------------------------------------------------------
# Finn
# --------------------------------------------------------------------------
FINN1_SHEET = ROOT / "assets" / "finn" / "finn-muscle-niveau-1.png"
FINN24_SHEET = ROOT / "assets" / "finn" / "finn-muscle-niveau-2-à-4.png"
FINN1_SCALE = 0.46
FINN24_SCALE = 0.435

# Boîtes (x1, y1, x2, y2) des sprites dans finn-muscle-niveau-1.png
FINN1_BOXES = {
    "idle": [(28, 86, 90, 201), (132, 87, 195, 201), (235, 87, 296, 201), (334, 87, 397, 201)],
    "walk": [(28, 249, 99, 362), (134, 251, 203, 362), (232, 251, 300, 362),
             (334, 250, 402, 363), (434, 250, 495, 363), (523, 251, 603, 362)],
    "run": [(30, 415, 92, 532), (125, 412, 214, 524), (234, 409, 310, 526), (330, 410, 407, 525),
            (424, 411, 500, 515), (524, 407, 591, 525), (612, 407, 685, 524)],
    "jump": [(892, 94, 967, 211), (1005, 82, 1076, 195)],
    "fall": [(1104, 87, 1175, 205)],
    "land": [(1219, 103, 1286, 210)],
    "attack": [(772, 260, 863, 390), (891, 258, 1008, 389), (1032, 268, 1154, 389), (1165, 280, 1246, 390)],
    "air_attack": [(389, 597, 471, 729), (28, 634, 139, 738)],
    "hurt": [(772, 458, 862, 571), (907, 455, 979, 572)],
    "dead": [(774, 696, 971, 751), (1007, 696, 1148, 752)],
}

# finn-muscle-niveau-2-à-4.png : anim -> (ligne, positions dans chaque panneau)
FINN24_ANIMS = {
    "idle": (0, [0, 1, 2, 3, 4]),
    "walk": (1, [0, 1, 2, 3, 4, 5]),
    "run": (2, [0, 1, 2, 3, 4]),
    "jump": (3, [0, 1]),
    "fall": (3, [3]),
    "land": (3, [4]),
    "climb": (3, [2, 3]),
    "attack": (4, [0, 1, 2, 3]),
    "air_attack": (4, [1, 3]),
    "hurt": (5, [0, 1]),
    "dead": (6, [0, 1]),
}


def is_hat(r, g, b):
    return min(r, g, b) > 215 and max(r, g, b) - min(r, g, b) < 30


def is_skin(r, g, b):
    return r > 185 and 130 < g < 232 and 90 < b < 210 and r - b > 35


HAT_HALF = 12


def hat_center_x(im):
    """Centre du chapeau : fenêtre de 24 px la plus dense en pixels blancs (ignore l'arc d'épée)."""
    p = im.load()
    bb = opaque_bbox(im)
    top, bottom = bb[1], bb[3]
    xs = [x for y in range(top, top + int((bottom - top) * 0.5)) for x in range(im.width)
          if p[x, y][3] and is_hat(*p[x, y][:3])]
    if not xs:
        return (bb[0] + bb[2]) / 2
    best = max(range(im.width), key=lambda s: sum(1 for x in xs if s <= x < s + 2 * HAT_HALF))
    inside = [x for x in xs if best <= x < best + 2 * HAT_HALF]
    return sum(inside) / len(inside)


def head_bottom(im, hcx=None):
    """Dernière ligne du chapeau blanc (près de son centre) dans la moitié haute du sprite."""
    p = im.load()
    bb = opaque_bbox(im)
    if not bb:
        return 0
    hcx = hat_center_x(im) if hcx is None else hcx
    top, bottom = bb[1], bb[3]
    last = top
    for y in range(top, top + int((bottom - top) * 0.55)):
        if any(p[x, y][3] and is_hat(*p[x, y][:3]) for x in range(im.width) if abs(x - hcx) <= HAT_HALF):
            last = y
    return last


def add_outline(im):
    """Ajoute un contour sombre d'1 px autour de la silhouette."""
    src = im.load()
    out = im.copy()
    op = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] and sum(src[nx, ny][:3]) > 150:
                    op[x, y] = OUTLINE
                    break
    return out


def _desaturate(c, amount, darken):
    r, g, b, a = c
    if not a:
        return c
    grey = 0.3 * r + 0.59 * g + 0.11 * b
    mix = lambda v: int((v + (grey - v) * amount) * darken)
    return (mix(r), mix(g), mix(b), a)


def age_frame(cell, stage, dead=False):
    """Vieillit Finn : couleurs délavées, chapeau jauni, barbe grise, dos voûté."""
    w, h = cell.size
    amount, darken = (0.45, 0.95) if stage == 1 else (0.7, 0.9)
    hat_col = (226, 222, 206, 255) if stage == 1 else (205, 204, 198, 255)
    beard_col = (196, 196, 204, 255) if stage == 1 else (242, 242, 246, 255)
    src = cell.load()
    hcx = None if dead else hat_center_x(cell)
    hb = 0 if dead else head_bottom(cell, hcx)

    def in_head(x, y):
        return dead or (y <= hb + 1 and abs(x - hcx) <= HAT_HALF)

    recol = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    rp = recol.load()
    for y in range(h):
        for x in range(w):
            c = src[x, y]
            if not c[3]:
                continue
            if is_hat(*c[:3]):
                rp[x, y] = hat_col if in_head(x, y) else c
            elif is_skin(*c[:3]):
                r, g, b, a = c
                rp[x, y] = ((r * 2 + 236) // 3, (g * 2 + 214) // 3, (b * 2 + 204) // 3, a)
            else:
                rp[x, y] = _desaturate(c, amount, darken)
    if dead:
        return recol
    skin = [(x, y) for y in range(hb + 1) for x in range(w)
            if in_head(x, y) and abs(x - hcx) <= HAT_HALF - 3 and src[x, y][3] and is_skin(*src[x, y][:3])]
    out = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    dx, dy = (1, 1) if stage == 1 else (2, 3)
    out.alpha_composite(recol.crop((0, hb + 1, w, h)), (0, hb + 1))
    out.alpha_composite(recol.crop((0, 0, w, hb + 1)), (dx, dy))
    if skin:
        fb = max(y for _, y in skin)
        xs = [x for x, y in skin if y >= fb - 2]
        x0, x1 = min(xs) + dx, max(xs) + dx
        length = 4 if stage == 1 else 8
        op = out.load()
        for y in range(fb - 1 + dy, min(h - 1, fb + length + dy)):
            shrink = max(0, (y - (fb + dy)) // 2)
            for x in range(x0 + shrink, x1 - shrink + 1):
                op[x, y] = beard_col
        out = add_outline(out)
    return out


def finn_level1():
    cut = remove_checker(Image.open(FINN1_SHEET))
    frames, anims = [], {}
    for name, boxes in FINN1_BOXES.items():
        anims[name] = []
        for box in boxes:
            anims[name].append(len(frames))
            frames.append(scaled_crop(cut, box, FINN1_SCALE))
    # pas d'animation d'échelle sur cette planche : le saut bras levés, en miroir
    anims["climb"] = [anims["jump"][1], len(frames)]
    frames.append(frames[anims["jump"][1]].transpose(Image.FLIP_LEFT_RIGHT))
    return frames, anims


def finn_levels_2_to_4():
    """Renvoie [(frames, anims)] pour les panneaux gauche, milieu et droite (niveaux 2, 3, 4)."""
    cut = remove_checker(Image.open(FINN24_SHEET))
    boxes = [b for b in components(cut) if b[3] - b[1] < 400]      # sans les traits de séparation
    rows = group_rows(boxes)
    edges = (cut.width / 3, cut.width * 2 / 3)
    panels = [dict() for _ in range(3)]
    for r, row in enumerate(rows):
        row = [b for b in row if b[4] >= 1500]                        # sans les petites marques rouges
        widths = sorted(b[2] - b[0] for b in row)
        med = widths[len(widths) // 2]
        row = [b for b in row if b[2] - b[0] <= med * 1.8]           # sans les sprites collés entre eux
        for b in row:
            cx = (b[0] + b[2]) / 2
            panel = 0 if cx < edges[0] else 1 if cx < edges[1] else 2
            panels[panel].setdefault(r, []).append(b)
    result = []
    for p, found in enumerate(panels):
        frames, anims = [], {}
        for name, (row, positions) in FINN24_ANIMS.items():
            available = found.get(row, [])
            anims[name] = []
            for pos in positions:
                if pos < len(available):
                    anims[name].append(len(frames))
                    frames.append(scaled_crop(cut, available[pos], FINN24_SCALE))
            if not anims[name]:
                raise ValueError(f"Finn niveau {p + 2} : animation {name} introuvable (ligne {row})")
        result.append((frames, anims))
    return result


def build_finn():
    variants = {"muscle1": finn_level1()}
    for level, data in enumerate(finn_levels_2_to_4(), start=2):
        variants[f"muscle{level}"] = data
    all_frames = [f for frames, _ in variants.values() for f in frames]
    dead_ids = {id(frames[i]) for frames, anims in variants.values() for i in anims["dead"]}
    anchors = [(opaque_bbox(f)[0] + opaque_bbox(f)[2]) / 2 if id(f) in dead_ids else hat_center_x(f)
               for f in all_frames]
    cells, cell_w, cell_h = pack(all_frames, anchors, min_w=96, min_h=64)
    meta = {"cell": [cell_w, cell_h], "anchor": [cell_w // 2, cell_h - 2], "variants": {}}
    start = 0
    for name, (frames, anims) in list(variants.items()):
        mine = cells[start:start + len(frames)]
        start += len(frames)
        variants[name] = (mine, anims)
    base_cells, base_anims = variants["muscle1"]
    dead = set(base_anims["dead"])
    variants["old1"] = ([age_frame(c, 1, i in dead) for i, c in enumerate(base_cells)], base_anims)
    variants["old2"] = ([age_frame(c, 2, i in dead) for i, c in enumerate(base_cells)], base_anims)
    for name, (frames, anims) in variants.items():
        save_strip(frames, f"finn_{name}.png")
        meta["variants"][name] = {"count": len(frames), "anims": anims}
    (OUT / "finn.json").write_text(json.dumps(meta, indent=2))
    print(f"Finn : case {cell_w}x{cell_h}, variantes " +
          ", ".join(f"{n} ({len(f)})" for n, (f, _) in variants.items()))


# --------------------------------------------------------------------------
# Monstres et boss
# --------------------------------------------------------------------------
# anim -> (ligne, positions) dans la liste des sprites détectés (aire >= 300 px)
MONSTERS = {
    "zombie": {
        "sheet": "assets/monstre-niveau-1/zombie.png", "scale": 0.367,
        "anims": {"idle": (0, [0, 1, 2, 3, 4]), "walk": (1, [0, 1, 2, 3, 4, 5]), "run": (2, [0, 1, 2, 3, 4, 5]),
                  "lunge": (3, [0, 1, 2, 3, 4]), "spit": (4, [0, 1, 3, 4, 5]), "hurt": (5, [0, 1, 2]),
                  "die": (5, [3, 4, 5])},
    },
    "lich": {
        "sheet": "assets/monstre-niveau-2/monstre.png", "scale": 0.447,
        "anims": {"idle": (0, [0, 1, 2, 3]), "attack": (0, [4, 5, 6, 7]), "walk": (1, [0, 1, 2, 3, 4, 5]),
                  "run": (2, [0, 1, 2, 3, 4, 5]), "cast": (3, [0, 3, 5]), "hurt": (4, [0, 1, 2]),
                  "die": (4, [3, 4, 5])},
        "projectile": ("proj_fireball.png", 3, 7, 0.447),
    },
    "boss": {
        "sheet": "assets/Boss-final/boss.png", "scale": 0.93,
        "anims": {"idle": (0, [0, 1, 2, 3, 4]), "taunt": (0, [5, 6, 7, 8]), "float": (1, [0, 1, 2, 3, 4, 5, 6, 7]),
                  "glide": (2, [0, 1, 2]), "charge": (2, [4]), "overhead": (2, [5, 7]), "shoot": (2, [8]),
                  "hurt": (3, [0, 1, 2, 3, 4, 5, 6, 7]), "die": (4, [0, 1, 2, 3, 4, 5])},
        "max_width": {"shoot": 215},
        "projectile": ("proj_ice.png", 2, 12, 0.55),
    },
    # Planche déjà transparente, mais chaque sprite est cerné d'un halo rouge/jaune
    # d'alpha 1 à 15 : sans alpha_min les voisins ne forment qu'une seule composante.
    "king": {
        "sheet": "assets/monstre-niveau-3/monstre.png", "scale": 0.72, "alpha_min": 200,
        "anims": {"idle": (0, [0, 1, 2, 3]), "walk": (1, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
                  "run": (2, [0, 1, 2, 3, 4, 5, 6]), "taunt": (3, [0, 1, 3]),
                  # coups d'estoc : les frames 1/4/5 (grand croissant lumineux) débordent
                  # trop à droite et doubleraient la largeur de case pour tout le roi
                  "attack": (4, [0, 2, 3, 6]), "cast": (5, [0, 4, 5, 6, 7]),
                  "hurt": (6, [0, 1, 2]), "die": (6, [3, 4, 5, 6, 7, 8, 9])},
        "projectile": ("proj_king_fire.png", 5, 9, 0.72),
    },
    # Damier gris clair (et non gris-bleu) ; min_area écarte l'ombre portée des sauts.
    "butler": {
        "sheet": "assets/boos-final-2/boss-2.png", "scale": 0.95,
        "checker": _is_light_checker, "min_area": 3000,
        "anims": {"idle": (0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]), "walk": (1, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
                  "run": (2, [0, 1, 2, 3, 4, 5, 6, 7, 8]), "jump": (3, [0, 1, 2, 3, 4]),
                  "hurt": (4, [0, 1, 2, 3]), "attack": (5, [0, 1, 2, 3, 4, 5]),
                  "die": (6, [2, 3, 4, 5, 6, 7, 8])},
    },
}


def build_monsters():
    meta = {"projectiles": {}}
    for name, spec in MONSTERS.items():
        src = Image.open(ROOT / spec["sheet"])
        if "alpha_min" in spec:
            # planche déjà transparente : on jette le halo lumineux qui soude les sprites
            cut = harden_alpha(src.convert("RGBA"), spec["alpha_min"] - 1)
        else:
            cut = remove_checker(src, spec.get("checker", _is_checker))
        rows = group_rows(components(cut, min_area=spec.get("min_area", 300)))
        frames, anims = [], {}
        for anim, (row, positions) in spec["anims"].items():
            anims[anim] = []
            for pos in positions:
                box = rows[row][pos]
                anims[anim].append(len(frames))
                frames.append(scaled_crop(cut, box, spec["scale"], spec.get("max_width", {}).get(anim)))
        cells, cell_w, cell_h = pack(frames, [body_center_x(f) for f in frames])
        save_strip(cells, f"monster_{name}.png")
        meta[name] = {"file": f"monster_{name}.png", "cell": [cell_w, cell_h], "count": len(cells), "foot": 2,
                      "anims": anims}
        if "projectile" in spec:
            file, row, pos, scale = spec["projectile"]
            proj = scaled_crop(cut, rows[row][pos], scale)
            proj.crop(opaque_bbox(proj)).save(OUT / file)
            meta["projectiles"][file[5:-4]] = file
        print(f"{name} : {len(cells)} frames, case {cell_w}x{cell_h}")
    (OUT / "monsters.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_finn()
    build_monsters()
