"""Découpe et prépare les planches de sprites fournies pour le jeu.

Usage (depuis la racine du projet) :
    .venv/bin/python tools/extract_sprites.py

Entrées :
    assets/finn/image.png     planche de Finn (fond « damier » peint, pas de transparence)
    assets/monstre/image.png  planche du zombie bonbon (cases de 32x32, transparente)
Sorties :
    assets/sprites/finn_<variante>.png   + assets/sprites/finn.json
    assets/sprites/zombie_<variante>.png + assets/sprites/zombie.json

Variantes de Finn (progression par la mort) :
    normal, muscle1, muscle2 (plus fort), old1, old2 (vieillissement)
"""
import colorsys
import json
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sprites"
OUTLINE = (27, 20, 38, 255)

# --------------------------------------------------------------------------
# Finn
# --------------------------------------------------------------------------
FINN_SCALE = 0.46
CELL_W, CELL_H = 96, 64
ANCHOR_X = 48      # centre du chapeau dans la case
FOOT_Y = 62        # ligne des pieds (depuis le haut de la case)

# Boîtes (x1, y1, x2, y2) des sprites dans assets/finn/image.png
FINN_BOXES = {
    "idle": [(28, 86, 90, 201), (132, 87, 195, 201), (235, 87, 296, 201), (334, 87, 397, 201)],
    "walk": [(28, 249, 99, 362), (134, 251, 203, 362), (232, 251, 300, 362),
             (334, 250, 402, 363), (434, 250, 495, 363), (523, 251, 603, 362)],
    "run": [(30, 415, 92, 532), (125, 412, 214, 524), (234, 409, 310, 526), (330, 410, 407, 525),
            (424, 411, 500, 515), (524, 407, 591, 525), (612, 407, 685, 524)],
    "jump": [(892, 94, 967, 211), (1005, 82, 1076, 195)],
    "fall": [(1104, 87, 1175, 205)],
    "land": [(1219, 103, 1286, 210)],
    "attack": [(772, 260, 863, 390), (891, 258, 1008, 389), (1032, 268, 1154, 389), (1165, 280, 1246, 390)],
    "air_attack": [(28, 634, 139, 738), (389, 597, 471, 729)],
    "hurt": [(772, 458, 862, 571), (907, 455, 979, 572)],
    "dead": [(774, 696, 971,751), (1007, 696, 1148, 752)],
}


def _is_checker(c, strict=False):
    r, g, b = c
    m = (r + g + b) / 3
    if strict:
        return max(r, g, b) - min(r, g, b) <= 26 and b - r >= 10 and 100 <= m <= 200
    return max(r, g, b) - min(r, g, b) <= 32 and b - r >= 3 and 80 <= m <= 222


def remove_checker(im):
    """Supprime le damier gris-bleu peint en remplissant depuis le fond."""
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
            if _is_checker(px[x, y], strict=True):
                q.append((x, y))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not _is_checker(px[x, y]):
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


def harden_alpha(im, threshold=110):
    im = im.copy()
    p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            p[x, y] = (r, g, b, 255) if a > threshold else (0, 0, 0, 0)
    return im


def opaque_bbox(im):
    return im.getchannel("A").getbbox()


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


def finn_frames():
    sheet = remove_checker(Image.open(ROOT / "assets" / "finn" / "image.png"))
    frames, anims = [], {}
    for name, boxes in FINN_BOXES.items():
        anims[name] = []
        for (x1, y1, x2, y2) in boxes:
            crop = sheet.crop((x1 - 2, y1 - 2, x2 + 3, y2 + 3))
            small = crop.resize((round(crop.width * FINN_SCALE), round(crop.height * FINN_SCALE)), Image.LANCZOS)
            small = harden_alpha(small)
            bb = opaque_bbox(small)
            ax = (bb[0] + bb[2]) / 2 if name == "dead" else hat_center_x(small)
            cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
            cell.alpha_composite(small, (round(ANCHOR_X - ax), FOOT_Y - bb[3]))
            anims[name].append(len(frames))
            frames.append(cell)
    # Pas d'animation d'échelle dans la planche : on réutilise le saut (bras levés) en miroir.
    anims["climb"] = [anims["jump"][1], len(frames)]
    frames.append(frames[anims["jump"][1]].transpose(Image.FLIP_LEFT_RIGHT))
    return frames, anims


def widen_body(cell, factor):
    """Élargit tout ce qui est sous la tête (torse, bras, jambes) : Finn se muscle."""
    hb = head_bottom(cell)
    body = cell.crop((0, hb + 1, CELL_W, CELL_H))
    wide = body.resize((round(CELL_W * factor), body.height), Image.NEAREST)
    out = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    out.alpha_composite(wide, (round(ANCHOR_X - ANCHOR_X * factor), hb + 1))
    out.alpha_composite(cell.crop((0, 0, CELL_W, hb + 1)), (0, 0))
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
    for y in range(CELL_H):
        for x in range(CELL_W):
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
    # barbe : sous le visage (dernières lignes de peau à l'intérieur du chapeau, pas les mains)
    skin = [(x, y) for y in range(hb + 1) for x in range(CELL_W)
            if in_head(x, y) and abs(x - hcx) <= HAT_HALF - 3 and src[x, y][3] and is_skin(*src[x, y][:3])]
    out = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    body = recol.crop((0, hb + 1, CELL_W, CELL_H))
    dx, dy = (1, 1) if stage == 1 else (2, 3)
    out.alpha_composite(body, (0, hb + 1))
    out.alpha_composite(recol.crop((0, 0, CELL_W, hb + 1)), (dx, dy))
    if skin:
        fb = max(y for _, y in skin)
        xs = [x for x, y in skin if y >= fb - 2]
        x0, x1 = min(xs) + dx, max(xs) + dx
        length = 4 if stage == 1 else 8
        op = out.load()
        for y in range(fb - 1 + dy, min(CELL_H - 1, fb + length + dy)):
            shrink = max(0, (y - (fb + dy)) // 2)
            for x in range(x0 + shrink, x1 - shrink + 1):
                op[x, y] = beard_col
        out = add_outline(out)
    return out


def build_finn():
    frames, anims = finn_frames()
    dead = set(anims["dead"])
    variants = {
        "normal": frames,
        "muscle1": [f if i in dead else widen_body(f, 1.18) for i, f in enumerate(frames)],
        "muscle2": [f if i in dead else widen_body(f, 1.36) for i, f in enumerate(frames)],
        "old1": [age_frame(f, 1, i in dead) for i, f in enumerate(frames)],
        "old2": [age_frame(f, 2, i in dead) for i, f in enumerate(frames)],
    }
    for name, fr in variants.items():
        strip = Image.new("RGBA", (CELL_W * len(fr), CELL_H), (0, 0, 0, 0))
        for i, f in enumerate(fr):
            strip.alpha_composite(f, (i * CELL_W, 0))
        strip.save(OUT / f"finn_{name}.png")
    meta = {"cell": [CELL_W, CELL_H], "anchor": [ANCHOR_X, FOOT_Y], "count": len(frames),
            "variants": list(variants), "anims": anims}
    (OUT / "finn.json").write_text(json.dumps(meta, indent=2))
    print(f"Finn : {len(frames)} frames x {len(variants)} variantes")


# --------------------------------------------------------------------------
# Zombie bonbon
# --------------------------------------------------------------------------
Z = 32
# (ligne, colonne) des cases dans assets/monstre/image.png
ZOMBIE_ANIMS = {
    "walk": [(0, c) for c in range(14)],
    "attack": [(4, 9), (4, 10), (4, 11), (4, 12), (4, 13)],
    "hop": [(3, 13), (3, 14), (3, 15)],
    "stun": [(7, 5), (7, 6), (7, 7)],
    "die": [(6, 8), (6, 9), (6, 10), (6, 11)],
    "burst": [(8, 12), (8, 13), (8, 14)],
}


def _shift_hue(im, hue, sat_mul=1.0, val_mul=1.0, eye_color=None):
    im = im.copy()
    p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if not a:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            is_eye = s > 0.45 and v > 0.7 and 0.15 < h < 0.3
            is_tongue = (h > 0.85 or h < 0.03) and s > 0.25
            if is_eye:
                if eye_color:
                    p[x, y] = eye_color + (a,)
                continue
            if is_tongue:
                continue
            nr, ng, nb = colorsys.hsv_to_rgb(hue, min(1, s * sat_mul + 0.12), min(1, v * val_mul))
            p[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
    return im


def _crown(frame, canvas_h):
    """Pose une couronne dorée sur la tête du zombie (pour le boss)."""
    top_pad = canvas_h - Z
    out = Image.new("RGBA", (Z, canvas_h), (0, 0, 0, 0))
    out.alpha_composite(frame, (0, top_pad))
    bb = opaque_bbox(out)
    top = bb[1]
    op = out.load()
    xs = [x for x in range(Z) if op[x, top + 2][3]]
    cx = (min(xs) + max(xs)) // 2 if xs else Z // 2
    cx = max(7, min(Z - 8, cx))
    crown = Image.new("RGBA", out.size, (0, 0, 0, 0))
    p = crown.load()
    gold, dark, gem = (255, 206, 60, 255), (214, 140, 24, 255), (255, 90, 170, 255)
    base_y = top + 1
    for x in range(cx - 5, cx + 6):
        for y in range(base_y - 2, base_y + 1):
            p[x, y] = gold if y < base_y else dark
    for x, h in ((cx - 5, 3), (cx - 4, 2), (cx, 4), (cx - 1, 2), (cx + 1, 2), (cx + 5, 3), (cx + 4, 2)):
        for y in range(base_y - 2 - h, base_y - 2):
            p[x, y] = gold
    p[cx, base_y - 1] = gem
    p[cx - 3, base_y - 1] = (120, 220, 255, 255)
    p[cx + 3, base_y - 1] = (120, 220, 255, 255)
    out.alpha_composite(add_outline(crown))
    return out


def build_zombies():
    sheet = Image.open(ROOT / "assets" / "monstre" / "image.png").convert("RGBA")
    order, anims = [], {}
    for name, cells in ZOMBIE_ANIMS.items():
        anims[name] = list(range(len(order), len(order) + len(cells)))
        order.extend(cells)
    base = [sheet.crop((c * Z, r * Z, c * Z + Z, r * Z + Z)) for r, c in order]
    variants = {
        "normal": (base, Z),
        "jumper": ([_shift_hue(f, 0.53, 1.3, 1.05) for f in base], Z),
        "champion": ([_shift_hue(f, 0.78, 1.5, 1.0, eye_color=(255, 70, 70)) for f in base], Z),
        "boss": ([_crown(_shift_hue(f, 0.93, 1.4, 1.12), Z + 8) for f in base], Z + 8),
    }
    for name, (fr, h) in variants.items():
        strip = Image.new("RGBA", (Z * len(fr), h), (0, 0, 0, 0))
        for i, f in enumerate(fr):
            strip.alpha_composite(f, (i * Z, h - f.height))
        strip.save(OUT / f"zombie_{name}.png")
    meta = {"count": len(order), "cells": {k: [Z, h] for k, (_, h) in variants.items()}, "anims": anims}
    (OUT / "zombie.json").write_text(json.dumps(meta, indent=2))
    print(f"Zombie : {len(order)} frames x {len(variants)} variantes")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_finn()
    build_zombies()
