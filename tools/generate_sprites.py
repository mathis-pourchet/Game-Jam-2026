"""Génère les sprites « maison » du jeu (pixel art dessiné par code).

Usage (depuis la racine du projet) :
    .venv/bin/python tools/generate_sprites.py

Crée dans assets/sprites/ : Jake, icônes de stats, cœurs, crâne, sablier,
décors en parallaxe, ciel, nuages, grille du boss, panneau, projectiles, halo.
Chaque fichier peut être remplacé par un vrai dessin tant que le nom et la
taille restent les mêmes.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sprites"
OUTLINE = (27, 20, 38, 255)
random.seed(7)


def canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def outline(im, color=OUTLINE):
    src = im.load()
    out = im.copy()
    op = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] and src[nx, ny][:3] != color[:3]:
                    op[x, y] = color
                    break
    return out


def from_pattern(rows, palette):
    h, w = len(rows), max(len(r) for r in rows)
    im = canvas(w, h)
    p = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in palette:
                p[x, y] = palette[ch]
    return im


def save(im, name):
    im.save(OUT / name)
    print(f"  {name:22s} {im.width}x{im.height}")


# --------------------------------------------------------------------------
# Jake le chien
# --------------------------------------------------------------------------
JAKE = (242, 178, 48, 255)
JAKE_SH = (212, 138, 28, 255)
MUZZLE = (252, 212, 120, 255)


def jake_frame(squash=0, talk=False, wave=False):
    im = canvas(30, 26)
    d = ImageDraw.Draw(im)
    top = 2 + squash
    d.ellipse([3, 9 + squash, 24, 21], fill=JAKE)                 # corps
    d.ellipse([9, top, 26, 16], fill=JAKE)                        # tête
    d.rectangle([5, 17, 22, 19], fill=JAKE)
    d.ellipse([3, 14 + squash, 20, 21], fill=JAKE_SH)             # ombre du ventre
    d.ellipse([4, 13 + squash, 21, 19], fill=JAKE)
    d.polygon([(10, top + 3), (13, top + 1), (13, top + 8), (10, top + 7)], fill=JAKE_SH)   # oreille
    d.ellipse([16, top + 6, 26, top + 12], fill=MUZZLE)           # museau
    for ex in (15, 20):                                           # grands yeux
        d.ellipse([ex, top + 2, ex + 4, top + 6], fill=(255, 255, 255, 255))
        d.rectangle([ex + 2, top + 3, ex + 3, top + 5], fill=OUTLINE)
    d.ellipse([21, top + 6, 25, top + 8], fill=OUTLINE)           # truffe
    if talk:
        d.ellipse([19, top + 9, 24, top + 13], fill=(120, 30, 40, 255))
        d.rectangle([20, top + 12, 23, top + 12], fill=(240, 110, 130, 255))
    else:
        d.line([(19, top + 10), (24, top + 10)], fill=OUTLINE)
    for lx in (5, 10, 15, 19):                                     # pattes
        d.rectangle([lx, 20, lx + 2, 23], fill=JAKE)
    d.line([(1, 12 + squash), (3, 14 + squash)], fill=JAKE, width=2)   # queue
    if wave:
        d.line([(24, 14), (28, 7)], fill=JAKE, width=3)
    else:
        d.line([(22, 14), (25, 19)], fill=JAKE, width=2)
    return outline(im)


def build_jake():
    frames = [jake_frame(), jake_frame(1), jake_frame(talk=True), jake_frame(1, talk=True, wave=True)]
    strip = canvas(30 * len(frames), 26)
    for i, f in enumerate(frames):
        strip.alpha_composite(f, (i * 30, 0))
    save(strip, "jake.png")


# --------------------------------------------------------------------------
# Icônes & interface
# --------------------------------------------------------------------------
HEART = [
    ".XX...XX.",
    "XWXX.XXXX",
    "XWXXXXXXX",
    "XXXXXXXXX",
    ".XXXXXXX.",
    "..XXXXX..",
    "...XXX...",
    "....X....",
]
SKULL = [
    "..XXXXX..",
    ".XXXXXXX.",
    "XXXXXXXXX",
    "XX..X..XX",
    "XX..X..XX",
    "XXXX.XXXX",
    ".XXXXXXX.",
    "..X.X.X..",
]
HOURGLASS = [
    "WWWWWWW",
    ".XSSSX.",
    ".XSSSX.",
    "..XSX..",
    "...S...",
    "..X.X..",
    ".X.S.X.",
    ".XSSSX.",
    "WWWWWWW",
]


def build_ui():
    red, white = (240, 60, 90, 255), (255, 230, 240, 255)
    save(outline(from_pattern(HEART, {"X": red, "W": white})), "heart_full.png")
    save(outline(from_pattern(HEART, {"X": (70, 45, 80, 255), "W": (70, 45, 80, 255)})), "heart_empty.png")
    save(outline(from_pattern(SKULL, {"X": (245, 240, 230, 255)})), "skull.png")
    save(outline(from_pattern(HOURGLASS, {"W": (190, 130, 70, 255), "X": (200, 230, 255, 255),
                                           "S": (255, 214, 60, 255)})), "hourglass.png")

    # icônes de stats 16x16
    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    d.polygon([(8, 1), (14, 7), (10, 7), (10, 13), (6, 13), (6, 7), (2, 7)], fill=(110, 230, 120, 255))
    d.line([(7, 3), (7, 11)], fill=(200, 255, 200, 255))
    save(outline(im), "icon_jump.png")

    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    d.polygon([(10, 0), (3, 9), (8, 9), (5, 15), (13, 6), (8, 6), (11, 0)], fill=(255, 214, 60, 255))
    save(outline(im), "icon_speed.png")

    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    d.line([(4, 11), (13, 2)], fill=(235, 240, 255, 255), width=3)
    d.line([(5, 10), (12, 3)], fill=(255, 255, 255, 255), width=1)
    d.line([(2, 9), (6, 13)], fill=(255, 190, 40, 255), width=2)
    d.line([(1, 14), (3, 12)], fill=(150, 90, 40, 255), width=2)
    save(outline(im), "icon_force.png")

    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    d.polygon([(2, 2), (8, 0), (14, 2), (13, 9), (8, 15), (3, 9)], fill=(90, 150, 240, 255))
    heart = from_pattern(HEART[:-1], {"X": (255, 120, 190, 255), "W": (255, 230, 240, 255)})
    im.alpha_composite(heart, (4, 4))
    save(outline(im), "icon_resistance.png")

    # grille de l'arène (tuile 16x16, dessinée x2)
    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    for x in (1, 5, 9, 13):
        d.rectangle([x, 0, x + 2, 15], fill=(74, 70, 96, 255))
        d.line([(x, 0), (x, 15)], fill=(150, 146, 180, 255))
    d.rectangle([0, 6, 15, 8], fill=(96, 84, 110, 255))
    for x in (2, 6, 10, 14):
        d.point((x, 7), fill=(220, 200, 120, 255))
    save(im, "gate.png")

    # panneau en bois
    im = canvas(16, 16)
    d = ImageDraw.Draw(im)
    d.rectangle([7, 9, 8, 15], fill=(120, 80, 40, 255))
    d.rectangle([1, 2, 14, 10], fill=(200, 140, 72, 255))
    d.line([(2, 9), (13, 9)], fill=(160, 104, 50, 255))
    d.rectangle([7, 3, 8, 6], fill=OUTLINE)
    d.point((7, 8), fill=OUTLINE)
    d.point((8, 8), fill=OUTLINE)
    save(outline(im), "sign.png")

    # onde de choc
    im = canvas(20, 12)
    d = ImageDraw.Draw(im)
    d.ellipse([0, 2, 19, 20], outline=(235, 248, 255, 255), width=3)
    d.ellipse([3, 5, 16, 20], outline=(140, 205, 255, 255), width=2)
    im = im.crop((0, 0, 20, 12))
    save(im, "shockwave.png")

    # étincelle et halo doux (non pixelisé)
    save(from_pattern([".W.", "WWW", ".W."], {"W": (255, 255, 255, 255)}), "spark.png")
    g = canvas(64, 64)
    gp = g.load()
    for y in range(64):
        for x in range(64):
            r = math.hypot(x - 31.5, y - 31.5) / 32
            if r < 1:
                gp[x, y] = (255, 255, 255, int(255 * (1 - r) ** 2))
    save(g, "glow.png")


# --------------------------------------------------------------------------
# Décors
# --------------------------------------------------------------------------
def gradient(top, bottom, h=256):
    im = canvas(4, h)
    p = im.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(4):
            p[x, y] = c
    return im


def wave(x, w, parts):
    return sum(a * math.sin(2 * math.pi * k * x / w + ph) for a, k, ph in parts)


def build_backgrounds():
    save(gradient((78, 156, 250), (196, 234, 255)), "sky_day.png")
    save(gradient((52, 28, 92), (236, 124, 128)), "sky_dusk.png")

    # couche lointaine : montagnes lavande + château de la Princesse Chewing-gum
    W, H = 480, 170
    im = canvas(W, H)
    p = im.load()
    far = [(14, 2, 0.3), (8, 5, 1.7), (4, 11, 0.9)]
    for x in range(W):
        top = int(80 + wave(x, W, far))
        for y in range(top, H):
            shade = (176, 160, 232, 255) if (y - top) > 6 else (206, 192, 246, 255)
            p[x, y] = shade
    d = ImageDraw.Draw(im)
    pink, pink2 = (240, 150, 205, 255), (220, 116, 180, 255)
    for cx, s in ((120, 1.0), (340, 0.7)):
        base = 132
        d.rectangle([cx - 30 * s, base - 30 * s, cx + 30 * s, H], fill=pink)
        for tx, th in ((-26, 58), (0, 80), (26, 58), (-12, 66), (12, 66)):
            x0 = cx + tx * s
            d.rectangle([x0 - 5 * s, base - th * s, x0 + 5 * s, H], fill=pink if tx else pink2)
            d.ellipse([x0 - 7 * s, base - th * s - 10 * s, x0 + 7 * s, base - th * s + 4 * s], fill=pink2)
            d.polygon([(x0, base - th * s - 22 * s), (x0 - 3 * s, base - th * s - 8 * s),
                       (x0 + 3 * s, base - th * s - 8 * s)], fill=(255, 220, 240, 255))
    save(im, "bg_far.png")

    # couche proche : collines vertes et arbres ronds
    W, H = 480, 150
    im = canvas(W, H)
    p = im.load()
    near = [(12, 3, 1.1), (7, 7, 0.2), (3, 13, 2.2)]
    tops = []
    for x in range(W):
        top = int(62 + wave(x, W, near))
        tops.append(top)
        for y in range(top, H):
            band = ((y - top) // 14) % 2
            p[x, y] = (118, 206, 104, 255) if band == 0 else (104, 190, 94, 255)
            if y - top < 3:
                p[x, y] = (160, 232, 130, 255)
    d = ImageDraw.Draw(im)
    for tx in range(20, W - 20, 64):
        tx += random.randint(-10, 10)
        ty = tops[tx]
        r = random.randint(12, 18)
        d.rectangle([tx - 2, ty - r - 4, tx + 2, ty + 2], fill=(150, 96, 60, 255))
        col = random.choice([(90, 180, 90, 255), (250, 150, 190, 255), (255, 200, 90, 255)])
        d.ellipse([tx - r, ty - 2 * r - 6, tx + r, ty - 6], fill=col)
        d.ellipse([tx - r + 4, ty - 2 * r - 3, tx - 2, ty - r - 8], fill=(255, 255, 255, 70))
    save(im, "bg_near.png")

    # nuage
    im = canvas(48, 22)
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in ((2, 8, 20, 21), (12, 2, 32, 21), (26, 6, 46, 21)):
        d.ellipse([x0, y0, x1, y1], fill=(255, 255, 255, 255))
    d.rectangle([6, 16, 42, 21], fill=(222, 236, 255, 255))
    save(im, "cloud.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_jake()
    build_ui()
    build_backgrounds()
