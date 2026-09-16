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


def ciel(stops, h=256):
    """Dégradé vertical 4 x h : [(t, (r, g, b)), ...] avec t de 0 (haut) à 1 (bas)."""
    im = canvas(4, h)
    p = im.load()
    stops = sorted(stops)
    for y in range(h):
        t = y / (h - 1)
        c = stops[-1][1]
        if t <= stops[0][0]:
            c = stops[0][1]
        else:
            for k in range(len(stops) - 1):
                (t0, c0), (t1, c1) = stops[k], stops[k + 1]
                if t0 <= t <= t1:
                    f = (t - t0) / max(1e-6, t1 - t0)
                    c = tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
                    break
        for x in range(4):
            p[x, y] = c + (255,)
    return im


class Bande:
    """Toile d'un décor tuilé horizontalement.

    Elle est suréchantillonnée (formes lissées, comme un dessin animé) et large
    de trois copies : ce qui déborde à gauche/droite est replié sur l'image
    finale, donc le raccord est invisible quand le jeu la répète.
    """

    SS = 3

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * 3 * self.SS, h * self.SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def _b(self, x0, y0, x1, y1):
        s, w = self.SS, self.w
        return [(x0 + w) * s, y0 * s, (x1 + w) * s - 1, y1 * s - 1]

    def _p(self, pts):
        s, w = self.SS, self.w
        return [((x + w) * s, y * s) for x, y in pts]

    def rect(self, x0, y0, x1, y1, c):
        self.d.rectangle(self._b(x0, y0, x1, y1), fill=c)

    def ell(self, x0, y0, x1, y1, c):
        self.d.ellipse(self._b(x0, y0, x1, y1), fill=c)

    def poly(self, pts, c):
        self.d.polygon(self._p(pts), fill=c)

    def trait(self, pts, c, ep=1.0):
        self.d.line(self._p(pts), fill=c, width=max(1, int(ep * self.SS)), joint="curve")

    def colline(self, profil, y_bas, corps, bandes, liseré):
        """Remplit sous une crête : corps, bandes de plus en plus sombres, liseré clair."""
        xs = [-self.w + i * 0.5 for i in range(int(self.w * 3 / 0.5) + 1)]
        for dy, c in [(0.0, corps)] + list(bandes):
            self.poly([(-self.w, y_bas)] + [(x, profil(x) + dy) for x in xs]
                      + [(2 * self.w, y_bas)], c)
        self.trait([(x, profil(x) + 1.4) for x in xs], liseré, 2.6)

    def finir(self):
        s, w, h = self.SS, self.w, self.h
        plein = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        plein.alpha_composite(self.im.crop((0, 0, w * s, h * s)))
        plein.alpha_composite(self.im.crop((2 * w * s, 0, 3 * w * s, h * s)))
        plein.alpha_composite(self.im.crop((w * s, 0, 2 * w * s, h * s)))
        return plein.convert("RGBa").resize((w, h), Image.BOX).convert("RGBA")


def build_backgrounds():
    # ----------------------------------------------------------------- ciels
    save(ciel([(0.0, (56, 134, 246)), (0.45, (108, 180, 252)), (0.78, (170, 220, 255)),
               (1.0, (218, 244, 255))]), "sky_day.png")
    save(ciel([(0.0, (38, 24, 84)), (0.35, (104, 56, 140)), (0.68, (214, 104, 136)),
               (0.88, (252, 162, 122)), (1.0, (255, 214, 158))]), "sky_dusk.png")

    # ------------------------------------- couche lointaine : Royaume Bonbon
    W, H = 480, 170
    b = Bande(W, H)

    def mont_loin(x):
        return 52 + wave(x, W, [(11, 2, 0.4), (6, 5, 2.2), (3, 9, 1.1)])

    def mont_pres(x):
        return 82 + wave(x, W, [(13, 1, 2.7), (7, 4, 0.6), (3, 8, 3.4)])

    b.colline(mont_loin, H, (198, 190, 248), [(10, (182, 170, 240))], (228, 224, 255))
    b.colline(mont_pres, H, (168, 152, 228), [(12, (152, 134, 216)), (30, (138, 118, 204))],
              (210, 200, 250))
    # plaine de sucre : une ondulation douce, surtout pas une bande droite
    b.colline(lambda x: 130 + wave(x, W, [(5, 3, 1.4), (2, 7, 0.2)]), H,
              (186, 166, 232), [(11, (172, 150, 226))], (214, 198, 250))

    ROSE, ROSE_C, ROSE_F = (246, 148, 202), (255, 202, 230), (212, 100, 166)
    SUCRE, VITRE, DORE = (255, 244, 250), (124, 66, 118), (255, 226, 118)

    def tour(x, base, haut, larg, canne=False, fleche=True):
        """Tour de sucre coiffée d'un dôme LARGE et BAS (pas une boule)."""
        y0 = base - haut
        b.rect(x - larg, y0, x + larg, base, ROSE)
        b.rect(x - larg, y0, x - larg * 0.3, base, ROSE_C)
        b.rect(x + larg * 0.42, y0, x + larg, base, ROSE_F)
        if canne:                                        # rayures sucre d'orge
            pas = larg * 2.1
            k = -2
            while y0 - 2 * larg + k * pas < base:
                ya = y0 - 2 * larg + k * pas
                quad = [(x - larg, ya), (x - larg, ya + pas * 0.42),
                        (x + larg, ya + 2 * larg + pas * 0.42), (x + larg, ya + 2 * larg)]
                b.poly([(px, min(max(py, y0), base)) for px, py in quad], SUCRE)
                k += 1
        dl, dh = larg * 1.45, larg * 1.1
        b.ell(x - dl, y0 - dh, x + dl, y0 + dh * 0.8, ROSE_F)
        b.rect(x - dl, y0 - dh * 0.1, x + dl, y0 + 1.2, ROSE_F)
        b.ell(x - dl * 0.76, y0 - dh * 0.86, x - dl * 0.06, y0 - dh * 0.04, ROSE)
        if fleche:
            b.trait([(x, y0 - dh), (x, y0 - dh - larg * 1.2)], SUCRE, 1.0)
            b.ell(x - 1.9, y0 - dh - larg * 1.2 - 3.8, x + 1.9, y0 - dh - larg * 1.2, DORE)
        wy = y0 + larg * 1.5
        while wy < base - 8:
            b.ell(x - larg * 0.3, wy, x + larg * 0.3, wy + 4.4, VITRE)
            wy += 11

    def chateau(cx, base, e=1.0):
        # rempart crénelé
        for k in range(-5, 6):
            b.rect(cx + k * 9 * e - 2.9 * e, base - 35 * e, cx + k * 9 * e + 2.9 * e,
                   base - 27 * e, ROSE)
        b.rect(cx - 48 * e, base - 30 * e, cx + 48 * e, base, ROSE)
        b.rect(cx - 48 * e, base - 30 * e, cx + 48 * e, base - 25 * e, ROSE_C)
        b.rect(cx - 48 * e, base - 7 * e, cx + 48 * e, base, ROSE_F)
        b.ell(cx - 7 * e, base - 22 * e, cx + 7 * e, base - 8 * e, VITRE)     # porche
        b.rect(cx - 7 * e, base - 15 * e, cx + 7 * e, base, VITRE)
        # tours d'angle et tours intermédiaires
        tour(cx - 40 * e, base, 44 * e, 6.5 * e, canne=True, fleche=False)
        tour(cx + 40 * e, base, 44 * e, 6.5 * e, canne=True, fleche=False)
        tour(cx - 21 * e, base, 62 * e, 8 * e)
        tour(cx + 21 * e, base, 62 * e, 8 * e)
        # donjon central : corps large, grand dôme surbaissé
        y0 = base - 84 * e
        b.rect(cx - 15 * e, y0, cx + 15 * e, base, ROSE)
        b.rect(cx - 15 * e, y0, cx - 6 * e, base, ROSE_C)
        b.rect(cx + 7 * e, y0, cx + 15 * e, base, ROSE_F)
        b.ell(cx - 23 * e, y0 - 19 * e, cx + 23 * e, y0 + 13 * e, ROSE_F)
        b.rect(cx - 23 * e, y0 - 1 * e, cx + 23 * e, y0 + 3 * e, ROSE_F)
        b.ell(cx - 18 * e, y0 - 15 * e, cx - 3 * e, y0 + 1 * e, ROSE)
        b.trait([(cx, y0 - 19 * e), (cx, y0 - 33 * e)], SUCRE, 1.3)
        b.ell(cx - 3.6 * e, y0 - 40 * e, cx + 3.6 * e, y0 - 32 * e, DORE)
        for wy in (y0 + 16 * e, y0 + 34 * e, y0 + 52 * e):
            for wx in (-8 * e, 0, 8 * e):
                b.ell(cx + wx - 2.4 * e, wy, cx + wx + 2.4 * e, wy + 6 * e, VITRE)

    def maison(cx, base, r, c):
        """Maison-bonbon : une goutte de gomme avec sa porte et son bonbon sur le toit."""
        c2 = tuple(min(255, v + 34) for v in c)
        porte = (176, 110, 164)
        b.ell(cx - r, base - r * 1.8, cx + r, base + r * 0.45, c)
        b.ell(cx - r * 0.76, base - r * 1.62, cx - r * 0.02, base - r * 0.5, c2)
        b.ell(cx - r * 0.24, base - r * 0.7, cx + r * 0.24, base - r * 0.32, porte)
        b.rect(cx - r * 0.24, base - r * 0.5, cx + r * 0.24, base, porte)
        b.ell(cx - r * 0.5, base - r * 1.16, cx - r * 0.16, base - r * 0.82, porte)
        b.ell(cx + r * 0.16, base - r * 1.16, cx + r * 0.5, base - r * 0.82, porte)
        b.ell(cx - r * 0.22, base - r * 2.06, cx + r * 0.22, base - r * 1.72, SUCRE)

    def sucette(cx, base, h, r, c):
        b.trait([(cx, base), (cx, base - h)], (238, 230, 250), 1.4)
        b.ell(cx - r, base - h - r * 1.5, cx + r, base - h + r * 0.5, c)
        b.ell(cx - r * 0.68, base - h - r * 1.34, cx - r * 0.04, base - h - r * 0.42,
              tuple(min(255, v + 36) for v in c))

    chateau(136, 149, 0.82)
    for cx, base, r, c in ((44, 146, 9, (250, 168, 210)), (66, 148, 7, (168, 232, 214)),
                           (296, 147, 8, (252, 214, 122)), (320, 149, 11, (238, 150, 198)),
                           (348, 147, 8, (196, 172, 248)), (392, 148, 9, (168, 232, 214)),
                           (418, 146, 7, (250, 196, 216)), (444, 149, 10, (252, 214, 122))):
        maison(cx, base, r, c)
    for cx, base, h, r, c in ((242, 148, 13, 5, (244, 130, 176)),
                              (266, 149, 18, 6, (154, 216, 240)),
                              (470, 147, 11, 4, (246, 196, 96))):
        sucette(cx, base, h, r, c)
    save(b.finir(), "bg_far.png")

    # ------------------------------- couche proche : collines et arbres ronds
    W, H = 480, 150
    b = Bande(W, H)

    def crete(x):
        return 54 + wave(x, W, [(12, 2, 1.1), (7, 5, 0.2), (3, 11, 2.2)])

    def bosse(x):
        return 92 + wave(x, W, [(10, 1, 3.0), (6, 4, 1.6), (3, 9, 0.4)])

    b.colline(crete, H, (102, 186, 98), [(15, (84, 166, 90)), (32, (70, 148, 82))],
              (156, 220, 122))

    TRONC = (126, 82, 54)
    VERTS = ((66, 150, 80), (112, 196, 112)), ((236, 132, 182), (255, 184, 216)), \
            ((244, 192, 84), (255, 228, 152))

    def arbre(cx, r, c, c2):
        sol = crete(cx) + 2
        b.rect(cx - 2.4, sol - r * 1.2, cx + 2.4, sol + 4, TRONC)
        b.ell(cx - r, sol - r * 2.4, cx + r, sol - r * 0.35, c)
        b.ell(cx - r * 0.72, sol - r * 2.2, cx + r * 0.02, sol - r * 1.2, c2)

    rng = random.Random(11)
    for i in range(9):
        cx = 24 + i * 52 + rng.randint(-8, 8)
        arbre(cx, rng.uniform(8.0, 11.5), *VERTS[i % 3])
    for i in range(14):                                   # buissons sur la crête
        cx = 12 + i * 34 + rng.randint(-7, 7)
        r = rng.uniform(4.0, 6.5)
        sol = crete(cx) + 2
        b.ell(cx - r, sol - r * 1.5, cx + r, sol + r * 0.3, (78, 160, 86))
        b.ell(cx - r * 0.7, sol - r * 1.35, cx + r * 0.05, sol - r * 0.4, (120, 198, 116))

    b.colline(bosse, H, (70, 148, 82), [(17, (56, 130, 74)), (36, (46, 114, 68))],
              (112, 190, 100))
    for i in range(16):                                   # petites fleurs
        cx = 8 + i * 30 + rng.randint(-8, 8)
        cy = bosse(cx) + rng.uniform(6, 34)
        c = rng.choice([(250, 200, 220), (252, 232, 150), (226, 200, 250)])
        b.ell(cx - 1.3, cy - 1.3, cx + 1.3, cy + 1.3, c)
    save(b.finir(), "bg_near.png")

    # ---------------------------------------------------------------- nuage
    ss = 4
    m = Image.new("L", (48 * ss, 22 * ss), 0)
    dm = ImageDraw.Draw(m)
    for (x0, y0, x1, y1) in ((1, 26, 21, 46), (10, 14, 34, 46), (22, 4, 42, 44),
                             (30, 16, 46, 46)):
        dm.ellipse([x0 * ss, y0 * ss, x1 * ss, y1 * ss], fill=255)
    dm.rounded_rectangle([3 * ss, 30 * ss, 45 * ss, 45 * ss], radius=6 * ss, fill=255)
    im = Image.new("RGBA", (48 * ss, 22 * ss), (0, 0, 0, 0))
    im.paste(gradient((255, 255, 255), (206, 226, 252), 22 * ss).resize((48 * ss, 22 * ss),
                                                                       Image.NEAREST), (0, 0), m)
    halo = canvas(48 * ss, 22 * ss)
    ImageDraw.Draw(halo).ellipse([9 * ss, 7 * ss, 31 * ss, 15 * ss], fill=(255, 255, 255, 170))
    im.alpha_composite(halo)
    im.putalpha(m)                       # recadre le halo sur la silhouette
    save(im.convert("RGBa").resize((48, 22), Image.BOX).convert("RGBA"), "cloud.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_jake()
    build_ui()
    build_backgrounds()
