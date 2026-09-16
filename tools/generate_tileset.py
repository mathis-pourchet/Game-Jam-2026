"""Génère le tileset 32x32 du jeu : assets/tilesets/tileset_32x32.png.

Usage (depuis la racine du projet) :
    .venv/bin/python tools/generate_tileset.py

La grille est FIGÉE : chaque tuile est replacée exactement à sa position
d'origine d'après assets/tilesets/tileset32_map.json (id = row * 8 + col).

Objectif graphique : le rendu « Mario moderne » (New Super Mario Bros /
Super Mario Maker) — volumes lisibles, lumière venant du haut, dégradés
doux, contours foncés nets, petits reflets — avec la palette d'Adventure
Time (herbe vert vif, terre brun-rosé, pierre lavande, glace bleu pâle,
bonbons roses).

Technique :
  * chaque tuile est dessinée sur une toile suréchantillonnée x4 (128 px)
    puis réduite en moyenne de zone : on obtient des courbes lissées alors
    que le jeu affiche les tuiles à l'échelle 1 ;
  * la toile fait trois tuiles de large. Tout ce qui déborde à gauche ou à
    droite est replié sur la tuile finale, ce qui garantit des raccords
    horizontaux invisibles ;
  * les textures (moucheture de terre, grain de pierre) sont des sommes de
    sinus à fréquences entières, donc périodiques en x ET en y : une tuile
    posée à côté ou au-dessus d'elle-même ne montre aucune couture.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
TILESETS = ROOT / "assets" / "tilesets"

T = 32              # taille d'une tuile en pixels (jeu)
SS = 4              # suréchantillonnage
S = T * SS          # taille interne d'une tuile
W = S * 3           # toile de travail : trois tuiles de large

# Débordement « pleine largeur » : couvre toute la toile, donc aucune arête
# verticale parasite ne peut être repliée sur la tuile.
GX0, GX1 = -34.0, 66.0


# --------------------------------------------------------------------------
# Palette « Terre de Ooo »
# --------------------------------------------------------------------------
NOIR = (34, 24, 42)

HERBE_VIF = (164, 228, 96)
HERBE = (108, 198, 74)
HERBE_MOY = (74, 166, 62)
HERBE_SOMBRE = (46, 126, 54)
HERBE_TRAIT = (28, 78, 42)

TERRE_HAUT = (196, 138, 102)
TERRE = (168, 110, 80)
TERRE_BAS = (146, 92, 68)
TERRE_CAILLOU = (114, 68, 52)
TERRE_TRAIT = (74, 44, 38)
TERRE_ETINCELLE = (222, 172, 128)

PIERRE_HAUT = (190, 178, 230)
PIERRE = (152, 138, 202)
PIERRE_BAS = (112, 98, 162)
PIERRE_TRAIT = (54, 44, 88)
PIERRE_CLAIR = (226, 220, 250)

DALLE_HAUT = (200, 200, 238)
DALLE = (166, 168, 214)
DALLE_BAS = (130, 134, 186)
DALLE_TRAIT = (52, 52, 92)

BRIQUE_HAUT = (148, 148, 198)
BRIQUE = (122, 122, 176)
BRIQUE_BAS = (96, 96, 148)
MORTIER = (58, 58, 100)

GLACE_CLAIR = (236, 250, 255)
GLACE = (168, 220, 248)
GLACE_BAS = (118, 178, 226)
GLACE_TRAIT = (50, 98, 146)

GOMME_CLAIR = (255, 196, 224)
GOMME = (248, 140, 192)
GOMME_BAS = (214, 92, 154)
GOMME_TRAIT = (122, 44, 88)

CHOCO_CLAIR = (156, 100, 62)
CHOCO = (118, 70, 44)
CHOCO_BAS = (86, 48, 32)
CHOCO_TRAIT = (46, 26, 22)

BOIS_CLAIR = (216, 158, 98)
BOIS = (178, 118, 68)
BOIS_BAS = (134, 82, 48)
BOIS_TRAIT = (68, 40, 30)

OR_CLAIR = (255, 244, 176)
OR = (255, 206, 62)
OR_BAS = (224, 148, 34)
OR_TRAIT = (124, 70, 20)

ACIER_CLAIR = (242, 246, 255)
ACIER = (178, 186, 214)
ACIER_BAS = (108, 116, 154)
ACIER_TRAIT = (36, 38, 66)

SLIME_CLAIR = (196, 250, 140)
SLIME = (132, 214, 78)
SLIME_BAS = (86, 166, 56)
SLIME_TRAIT = (40, 92, 44)

GOO_CLAIR = (226, 160, 252)
GOO = (176, 96, 224)
GOO_BAS = (124, 58, 172)
GOO_TRAIT = (60, 26, 92)

BLANC = (255, 255, 255)
BLANC_BLEU = (226, 238, 255)


def melange(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def eclaircir(c, t):
    return melange(c, (255, 255, 255), t)


def assombrir(c, t):
    return melange(c, (0, 0, 0), t)


# --------------------------------------------------------------------------
# Dégradés et bruit périodique
# --------------------------------------------------------------------------
def rampe(stops):
    """Dégradé vertical (W, S) défini par une liste [(y_tuile, couleur), ...]."""
    stops = sorted(stops, key=lambda s: s[0])
    col = Image.new("RGB", (1, S))
    p = col.load()
    for j in range(S):
        y = (j + 0.5) / SS
        if y <= stops[0][0]:
            c = stops[0][1]
        elif y >= stops[-1][0]:
            c = stops[-1][1]
        else:
            c = stops[-1][1]
            for k in range(len(stops) - 1):
                y0, c0 = stops[k]
                y1, c1 = stops[k + 1]
                if y0 <= y <= y1:
                    c = melange(c0, c1, (y - y0) / max(1e-6, y1 - y0))
                    break
        p[0, j] = c
    return col.resize((W, S), Image.NEAREST)


_TABLES = {}


def _table(graine, n=8):
    if graine not in _TABLES:
        rng = random.Random(graine)
        _TABLES[graine] = [(rng.uniform(0.3, 1.0), rng.randint(2, 6), rng.randint(2, 6),
                            rng.uniform(0, 2 * math.pi)) for _ in range(n)]
    return _TABLES[graine]


_BRUITS = {}


def bruit(graine, res=32):
    """Image L (res, res) de bruit lisse, périodique en x et en y."""
    cle = (graine, res)
    if cle not in _BRUITS:
        table = _table(graine)
        im = Image.new("L", (res, res))
        p = im.load()
        for y in range(res):
            for x in range(res):
                v = sum(a * math.sin(2 * math.pi * (kx * x / res + ky * y / res) + ph)
                        for a, kx, ky, ph in table)
                p[x, y] = max(0, min(255, int(128 + 44 * v)))
        _BRUITS[cle] = im
    return _BRUITS[cle]


def _tripler(im):
    large = Image.new(im.mode, (W, im.height))
    for k in range(3):
        large.paste(im, (k * S, 0))
    return large


def reduire(im):
    """Réduction x4 en moyenne de zone, avec alpha prémultiplié (pas de halo)."""
    a = im.split()[3]
    canaux = [ImageChops.multiply(c, a) for c in im.split()[:3]]
    petit = Image.merge("RGBA", canaux + [a]).resize((T, T), Image.BOX)
    p = petit.load()
    for y in range(T):
        for x in range(T):
            r, g, b, al = p[x, y]
            if al:
                p[x, y] = (min(255, r * 255 // al), min(255, g * 255 // al),
                           min(255, b * 255 // al), al)
    return petit


# --------------------------------------------------------------------------
# Toile de travail
# --------------------------------------------------------------------------
class Tuile:
    """Toile d'une tuile : x4, large de trois tuiles (repliement horizontal).

    Toutes les coordonnées passées aux primitives sont en pixels de tuile
    (0..32), origine en haut à gauche.
    """

    def __init__(self):
        self.im = Image.new("RGBA", (W, S), (0, 0, 0, 0))

    # -- conversions --------------------------------------------------------
    @staticmethod
    def pt(x, y):
        return ((x + T) * SS, y * SS)

    @staticmethod
    def boite(x0, y0, x1, y1):
        return [(x0 + T) * SS, y0 * SS, (x1 + T) * SS - 1, y1 * SS - 1]

    # -- calques et masques -------------------------------------------------
    @staticmethod
    def masque(plein=False):
        return Image.new("L", (W, S), 255 if plein else 0)

    @staticmethod
    def calque():
        return Image.new("RGBA", (W, S), (0, 0, 0, 0))

    def poser(self, couche, masque=None, flou=0.0):
        if flou:
            couche = couche.filter(ImageFilter.GaussianBlur(flou * SS))
        if masque is not None:
            couche.putalpha(ImageChops.multiply(couche.split()[3], masque))
        self.im.alpha_composite(couche)

    # -- primitives ---------------------------------------------------------
    def _d(self, cible):
        return ImageDraw.Draw(self.im if cible is None else cible)

    def rect(self, x0, y0, x1, y1, c, cible=None):
        self._d(cible).rectangle(self.boite(x0, y0, x1, y1), fill=c)

    def ellipse(self, x0, y0, x1, y1, c, cible=None):
        self._d(cible).ellipse(self.boite(x0, y0, x1, y1), fill=c)

    def arrondi(self, x0, y0, x1, y1, r, c, cible=None):
        self._d(cible).rounded_rectangle(self.boite(x0, y0, x1, y1),
                                         radius=max(1, int(r * SS)), fill=c)

    def polygone(self, pts, c, cible=None):
        self._d(cible).polygon([self.pt(x, y) for x, y in pts], fill=c)

    def ligne(self, pts, c, ep=1.0, cible=None):
        self._d(cible).line([self.pt(x, y) for x, y in pts], fill=c,
                            width=max(1, int(ep * SS)), joint="curve")

    def arc(self, x0, y0, x1, y1, a0, a1, c, ep=1.0, cible=None):
        self._d(cible).arc(self.boite(x0, y0, x1, y1), a0, a1, fill=c,
                           width=max(1, int(ep * SS)))

    # -- remplissages -------------------------------------------------------
    def peindre(self, masque, stops):
        self.im.paste(rampe(stops), (0, 0), masque)

    def uni(self, masque, couleur):
        self.im.paste(Image.new("RGB", (W, S), couleur), (0, 0), masque)

    def grain(self, masque, graine, force=22, res=32,
              clair=(255, 250, 230), sombre=(28, 18, 38)):
        """Moucheture douce : éclaircit/assombrit sans créer de bruit sale."""
        n = _tripler(bruit(graine, res).resize((S, S), Image.BICUBIC))
        for couleur, canal in ((clair, n.point(lambda v: max(0, v - 134) * force // 121)),
                               (sombre, n.point(lambda v: max(0, 122 - v) * force // 122))):
            couche = Image.new("RGBA", (W, S), couleur + (0,))
            couche.putalpha(ImageChops.multiply(canal, masque))
            self.im.alpha_composite(couche)

    def relief(self, masque, dx, dy, rayon, couleur, alpha):
        """Ombre/lumière interne : la bande découverte par le masque décalé."""
        dec = ImageChops.offset(masque, int(round(dx * SS)), int(round(dy * SS)))
        bande = ImageChops.subtract(masque, dec)
        if rayon:
            bande = bande.filter(ImageFilter.GaussianBlur(rayon * SS))
        bande = ImageChops.multiply(bande, masque)
        couche = Image.new("RGBA", (W, S), couleur + (0,))
        couche.putalpha(bande.point(lambda v: v * alpha // 255))
        self.im.alpha_composite(couche)

    def brillance(self, masque, x0, y0, x1, y1, alpha=140, flou=1.0, couleur=BLANC):
        couche = self.calque()
        self.ellipse(x0, y0, x1, y1, couleur + (alpha,), cible=couche)
        self.poser(couche, masque, flou)

    def contour(self, couleur=NOIR, ep=1.0):
        a = self.im.split()[3]
        dil = a
        for _ in range(max(1, int(round(ep * SS)))):
            dil = dil.filter(ImageFilter.MaxFilter(3))
        fond = Image.new("RGBA", (W, S), couleur)
        fond.putalpha(dil)
        fond.alpha_composite(self.im)
        self.im = fond

    # -- sortie -------------------------------------------------------------
    def finir(self):
        plein = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        plein.alpha_composite(self.im.crop((0, 0, S, S)))
        plein.alpha_composite(self.im.crop((2 * S, 0, 3 * S, S)))
        plein.alpha_composite(self.im.crop((S, 0, 2 * S, S)))
        return reduire(plein)


# --------------------------------------------------------------------------
# Couronne d'herbe (partagée par grass_* et grassrock_*)
# --------------------------------------------------------------------------
def _profil(x):
    """Ligne de séparation herbe / sous-sol, périodique sur 32 px."""
    return 8.6 + 1.25 * math.sin(2 * math.pi * x / T + 0.7) + 0.55 * math.sin(4 * math.pi * x / T + 2.3)


_LAMES = ((3.5, 2.1, 3.4), (11.0, 1.7, 2.2), (18.0, 2.3, 4.0), (26.0, 1.8, 2.6))


def _profil_lames(x):
    y = _profil(x)
    for bx, bw, bd in _LAMES:
        for k in (-1, 0, 1):
            dx = x - (bx + k * T)
            if abs(dx) < bw:
                y = max(y, _profil(bx + k * T) + bd * (1 - (dx / bw) ** 2))
    return y


_XS = [GX0 + i * 0.25 for i in range(int((GX1 - GX0) / 0.25) + 1)]


def couronne_herbe(t, variante=0):
    """Dessine la couronne d'herbe et renvoie son masque."""
    m = t.masque()
    t.polygone([(GX0, -4)] + [(x, _profil_lames(x)) for x in _XS] + [(GX1, -4)], 255, m)

    t.peindre(m, [(0.0, HERBE_TRAIT), (0.95, HERBE_TRAIT), (1.05, HERBE_VIF),
                  (2.8, eclaircir(HERBE, 0.18)), (5.0, HERBE), (7.6, HERBE_MOY),
                  (10.4, HERBE_SOMBRE), (14.0, assombrir(HERBE_SOMBRE, 0.12))])

    couche = t.calque()
    # brins clairs qui montent du liseré
    brins = [(2.0, 5.8), (6.8, 4.6), (13.2, 5.2), (16.4, 4.2), (22.6, 5.6), (29.4, 4.8)]
    if variante:
        brins = [(x + 3.1, h * 0.9) for x, h in brins]
    for bx, bh in brins:
        t.ligne([(bx, 1.3), (bx + 0.5, bh)], eclaircir(HERBE_VIF, 0.35) + (170,), 0.6, cible=couche)
    # ombre douce sous le liseré de crête
    t.rect(GX0, 1.05, GX1, 2.0, eclaircir(HERBE_VIF, 0.55) + (120,), cible=couche)
    # ligne sombre à la base de l'herbe : assoit la couronne sur le sol
    t.ligne([(x, _profil_lames(x) - 0.55) for x in _XS],
            assombrir(HERBE_SOMBRE, 0.25) + (150,), 0.7, cible=couche)
    t.poser(couche, m)
    return m


# --------------------------------------------------------------------------
# Corps de sol
# --------------------------------------------------------------------------
def corps_terre(t, m, variante, sous_herbe):
    if sous_herbe:
        t.peindre(m, [(0, TERRE_HAUT), (8, TERRE_HAUT), (15, TERRE), (25, TERRE_BAS), (32, TERRE_BAS)])
    else:
        t.peindre(m, [(0, TERRE_BAS), (32, TERRE_BAS)])
    t.grain(m, 11 + variante, force=20, res=32)

    rng = random.Random(400 + variante)
    couche = t.calque()
    haut = 12.0 if sous_herbe else 3.0
    for _ in range(4):
        cx = rng.uniform(5.0, 27.0)
        cy = rng.uniform(haut, 28.0)
        r = rng.uniform(1.5, 2.6)
        t.ellipse(cx - r, cy - r * 0.8, cx + r, cy + r * 0.8, TERRE_CAILLOU + (235,), cible=couche)
        t.ellipse(cx - r * 0.75, cy - r * 0.72, cx + r * 0.35, cy + r * 0.1,
                  eclaircir(TERRE_CAILLOU, 0.42) + (235,), cible=couche)
    for _ in range(2):                       # petites étincelles de terre
        cx, cy = rng.uniform(5.0, 27.0), rng.uniform(haut, 29.0)
        t.ligne([(cx - 0.9, cy), (cx + 0.9, cy)], TERRE_ETINCELLE + (200,), 0.5, cible=couche)
        t.ligne([(cx, cy - 0.9), (cx, cy + 0.9)], TERRE_ETINCELLE + (200,), 0.5, cible=couche)
    t.poser(couche, m)


def corps_roche(t, m, variante, sous_herbe):
    if sous_herbe:
        t.peindre(m, [(0, PIERRE_HAUT), (9, PIERRE_HAUT), (18, PIERRE), (32, PIERRE_BAS)])
    else:
        t.peindre(m, [(0, melange(PIERRE, PIERRE_HAUT, 0.45)), (13, PIERRE), (32, PIERRE_BAS)])
    t.grain(m, 21 + variante, force=20, res=32)

    rng = random.Random(700 + variante)
    haut = 13.5 if sous_herbe else 3.0
    # gros galets encastrés : c'est eux qui donnent le volume « Mario »
    for _ in range(2):
        cx = rng.uniform(9.0, 23.0)
        cy = rng.uniform(haut + 4.0, 25.0)
        rx, ry = rng.uniform(4.8, 6.6), rng.uniform(2.6, 3.6)
        mg = t.masque()
        t.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, 255, mg)
        mg = ImageChops.multiply(mg, m)
        t.peindre(mg, [(cy - ry, eclaircir(PIERRE, 0.12)), (cy, PIERRE),
                       (cy + ry, assombrir(PIERRE, 0.10))])
        t.relief(mg, 0, 0.9, 0.22, PIERRE_CLAIR, 125)
        t.relief(mg, 0, -1.1, 0.32, PIERRE_TRAIT, 100)
    # une fissure franche, gravée
    couche = t.calque()
    x, y = rng.uniform(9.0, 23.0), haut + 1.0
    pts = [(x, y)]
    for _ in range(3):
        x += rng.uniform(-3.4, 3.4)
        y += rng.uniform(4.0, 6.5)
        pts.append((min(27.0, max(5.0, x)), min(30.0, y)))
    t.ligne(pts, PIERRE_TRAIT + (170,), 0.7, cible=couche)
    t.ligne([(px + 0.75, py + 0.45) for px, py in pts], PIERRE_CLAIR + (140,), 0.55, cible=couche)
    t.poser(couche, m, flou=0.1)


def corps_dalle(t, m, variante, sous_herbe):
    """Dallage du château : grandes pierres taillées, joints nets."""
    t.peindre(m, [(0, DALLE_HAUT), (6, DALLE_HAUT), (18, DALLE), (32, DALLE_BAS)])
    t.grain(m, 31 + variante, force=18, res=32)

    couche = t.calque()
    # joints : 3 rangées de 10.67 px, décalage alterné -> raccord parfait
    lignes = (10.67, 21.33)
    for y in lignes:
        t.ligne([(GX0, y), (GX1, y)], DALLE_TRAIT + (130,), 0.55, cible=couche)
        t.ligne([(GX0, y + 0.6), (GX1, y + 0.6)], eclaircir(DALLE_HAUT, 0.45) + (110,), 0.5, cible=couche)
    joints = ((0.0, (0, 10.67)), (16.0, (0, 10.67)), (8.0, (10.67, 21.33)),
              (24.0, (10.67, 21.33)), (0.0, (21.33, 32)), (16.0, (21.33, 32)))
    if variante == 1:
        joints = ((8.0, (0, 10.67)), (24.0, (0, 10.67)), (0.0, (10.67, 21.33)),
                  (16.0, (10.67, 21.33)), (8.0, (21.33, 32)), (24.0, (21.33, 32)))
    for jx, (ja, jb) in joints:
        for k in (-T, 0, T):          # le joint posé sur x = 0 doit aussi exister en x = 32
            t.ligne([(jx + k, ja), (jx + k, jb)], DALLE_TRAIT + (120,), 0.55, cible=couche)
            t.ligne([(jx + k + 0.6, ja), (jx + k + 0.6, jb)],
                    eclaircir(DALLE_HAUT, 0.4) + (90,), 0.5, cible=couche)
    rng = random.Random(900 + variante)
    for _ in range(3):
        cx, cy = rng.uniform(4.0, 28.0), rng.uniform(4.0, 29.0)
        t.ellipse(cx - 0.8, cy - 0.6, cx + 0.8, cy + 0.6, DALLE_BAS + (110,), cible=couche)
    t.poser(couche, m)


def corps_brique(t, m, variante, sous_herbe):
    """Mur de briques de pierre : 4 assises de 8 px, décalage alterné."""
    t.peindre(m, [(0, BRIQUE_HAUT), (14, BRIQUE), (32, BRIQUE_BAS)])
    couche = t.calque()
    for i in range(4):
        y0 = i * 8.0
        dec = 0.0 if i % 2 == 0 else 8.0
        for jx in (dec, dec + 16.0):
            for k in (-T, 0, T):
                t.rect(jx + k - 0.45, y0, jx + k + 0.45, y0 + 8.0, MORTIER + (210,), cible=couche)
        t.rect(GX0, y0 - 0.45, GX1, y0 + 0.45, MORTIER + (210,), cible=couche)
        # lumière en haut de chaque brique, ombre en bas
        t.rect(GX0, y0 + 0.5, GX1, y0 + 1.3, eclaircir(BRIQUE_HAUT, 0.42) + (120,), cible=couche)
        t.rect(GX0, y0 + 6.6, GX1, y0 + 7.6, assombrir(BRIQUE_BAS, 0.32) + (95,), cible=couche)
    t.poser(couche, m)
    t.grain(m, 41 + variante, force=16, res=32)


CORPS = {"terre": corps_terre, "roche": corps_roche, "dalle": corps_dalle, "brique": corps_brique}

TRAITS = {"terre": (HERBE_TRAIT, TERRE_TRAIT), "roche": (HERBE_TRAIT, PIERRE_TRAIT),
          "dalle": (HERBE_TRAIT, DALLE_TRAIT), "brique": (HERBE_TRAIT, MORTIER)}


def sol(bord=None, corps="terre", herbe=False, variante=0, bas=False, sommet=False):
    """Tuile de sol pleine.

    bord    : None | "gauche" | "droite" | "seul"
    corps   : clé de CORPS
    herbe   : ajoute la couronne d'herbe (et son arête supérieure)
    sommet  : arête supérieure sans herbe (dessus de maçonnerie)
    bas     : arête inférieure
    """
    t = Tuile()
    plein = t.masque()
    t.rect(GX0, 0, GX1, T, 255, plein)
    CORPS[corps](t, plein, variante, herbe)

    if sommet:
        couche = t.calque()
        trait = TRAITS[corps][1]
        clair = DALLE_HAUT if corps in ("dalle", "brique") else PIERRE_CLAIR
        t.rect(GX0, 0, GX1, 1.15, assombrir(trait, 0.15) + (255,), cible=couche)
        t.rect(GX0, 1.15, GX1, 2.4, eclaircir(clair, 0.3) + (195,), cible=couche)
        t.rect(GX0, 2.4, GX1, 4.0, eclaircir(clair, 0.05) + (85,), cible=couche)
        t.poser(couche, plein)

    if herbe:
        couronne_herbe(t, variante)

    if bas:
        couche = t.calque()
        t.rect(GX0, 28.4, GX1, 31.0, (20, 12, 26, 90), cible=couche)
        t.rect(GX0, 31.0, GX1, T, assombrir(TRAITS[corps][1], 0.05) + (255,), cible=couche)
        t.poser(couche, plein, flou=0.12)

    if bord:
        cotes = ("gauche", "droite") if bord == "seul" else (bord,)
        trait_h, trait_c = TRAITS[corps]
        for cote in cotes:
            couche = t.calque()
            if cote == "gauche":
                t.rect(1.0, 0, 3.4, T, (22, 14, 30, 135), cible=couche)
            else:
                t.rect(T - 3.4, 0, T - 1.0, T, (22, 14, 30, 155), cible=couche)
            t.poser(couche, plein, flou=0.55)

            m = t.masque()
            if cote == "gauche":
                t.rect(0, 0, 1.0, T, 255, m)
            else:
                t.rect(T - 1.0, 0, T, T, 255, m)
            m = ImageChops.multiply(m, plein)
            if herbe:
                t.peindre(m, [(0, trait_h), (10.0, trait_h), (11.5, trait_c), (32, trait_c)])
            else:
                t.peindre(m, [(0, trait_c), (32, trait_c)])
    return t.finir()


# --------------------------------------------------------------------------
# Plateformes traversables
# --------------------------------------------------------------------------
def plateforme(bord=None):
    """Planche de bois « pain d'épice », surface de collision au ras du haut."""
    t = Tuile()
    x0 = 0.6 if bord in ("gauche", "seul") else GX0
    x1 = T - 0.6 if bord in ("droite", "seul") else GX1
    m = t.masque()
    t.arrondi(x0, 0, x1, 13.0, 3.2, 255, m)

    t.peindre(m, [(0, BOIS_TRAIT), (1.0, BOIS_TRAIT), (1.1, eclaircir(BOIS_CLAIR, 0.3)),
                  (3.2, BOIS_CLAIR), (6.0, BOIS), (10.0, BOIS_BAS), (13.0, assombrir(BOIS_BAS, 0.25))])
    couche = t.calque()
    for y in (7.0, 9.6):
        t.ligne([(GX0, y), (GX1, y)], assombrir(BOIS_BAS, 0.18) + (110,), 0.5, cible=couche)
    for x in (4.0, 14.0, 24.0):
        t.ligne([(x, 3.4), (x + 0.4, 12.2)], assombrir(BOIS_BAS, 0.3) + (90,), 0.5, cible=couche)
    t.rect(GX0, 1.1, GX1, 2.4, eclaircir(BOIS_CLAIR, 0.5) + (140,), cible=couche)
    t.poser(couche, m)
    t.grain(m, 55, force=14, res=32)
    t.relief(m, 0, -2.6, 0.55, assombrir(BOIS_TRAIT, 0.15), 165)     # dessous de planche
    if bord in ("gauche", "seul"):
        t.relief(m, 2.6, 0, 0.5, BOIS_TRAIT, 90)
    if bord in ("droite", "seul"):
        t.relief(m, -2.6, 0, 0.5, BOIS_TRAIT, 120)
    # rivets aux extrémités : c'est ce qui fait lire les bouts de la planche
    couche = t.calque()
    for cote, cx in (("gauche", 4.4), ("droite", T - 4.4)):
        if bord == cote or bord == "seul":
            t.ellipse(cx - 1.6, 4.4, cx + 1.6, 7.6, BOIS_TRAIT + (255,), cible=couche)
            t.ellipse(cx - 1.1, 4.8, cx + 1.1, 6.9, eclaircir(BOIS_CLAIR, 0.3) + (255,), cible=couche)
    t.poser(couche, m)
    if bord:
        t.contour(BOIS_TRAIT, 0.75)
    return t.finir()


# --------------------------------------------------------------------------
# Blocs
# --------------------------------------------------------------------------
def _cadre_bloc(t, r=3.0):
    m = t.masque()
    t.arrondi(0, 0, T, T, r, 255, m)
    return m


def _bevel(t, m, clair, sombre):
    t.relief(m, 0, 2.2, 0.5, clair, 150)             # lumière sur l'arête haute
    t.relief(m, 0, -2.4, 0.6, sombre, 130)           # ombre en bas
    t.relief(m, 2.0, 0, 0.5, clair, 70)              # rehaut à gauche
    t.relief(m, -2.2, 0, 0.6, sombre, 90)            # ombre à droite


def bloc_brique():
    t = Tuile()
    m = _cadre_bloc(t, 2.6)
    t.peindre(m, [(0, PIERRE_HAUT), (14, PIERRE), (32, PIERRE_BAS)])
    couche = t.calque()
    for i, y0 in enumerate((1.5, 11.0, 20.5)):
        dec = 0.0 if i % 2 == 0 else 8.0
        t.rect(0, y0 - 0.5, T, y0 + 0.5, PIERRE_TRAIT + (200,), cible=couche)
        for jx in (dec + 0.0, dec + 16.0):
            if 1.0 < jx < T - 1.0:
                t.rect(jx - 0.5, y0, jx + 0.5, y0 + 9.5, PIERRE_TRAIT + (190,), cible=couche)
        t.rect(0, y0 + 0.6, T, y0 + 1.5, eclaircir(PIERRE_CLAIR, 0.3) + (120,), cible=couche)
    t.poser(couche, m)
    t.grain(m, 61, force=18)
    _bevel(t, m, PIERRE_CLAIR, PIERRE_TRAIT)
    t.contour(assombrir(PIERRE_TRAIT, 0.25), 1.0)
    return t.finir()


def bloc_gomme():
    t = Tuile()
    m = _cadre_bloc(t, 4.5)
    t.peindre(m, [(0, GOMME_CLAIR), (10, GOMME), (32, GOMME_BAS)])
    couche = t.calque()
    for k in range(-2, 5):
        x = k * 9.0
        t.ligne([(x, 34), (x + 20, -2)], eclaircir(GOMME_CLAIR, 0.45) + (110,), 3.0, cible=couche)
    t.poser(couche, m)
    _bevel(t, m, BLANC, GOMME_TRAIT)
    t.brillance(m, 3.5, 3.0, 15.0, 10.0, alpha=175, flou=0.9)
    t.brillance(m, 20.0, 4.0, 26.0, 8.0, alpha=120, flou=0.7)
    t.contour(GOMME_TRAIT, 1.0)
    return t.finir()


def bloc_glace():
    t = Tuile()
    m = _cadre_bloc(t, 4.0)
    t.peindre(m, [(0, GLACE_CLAIR), (11, GLACE), (32, GLACE_BAS)])
    couche = t.calque()
    t.polygone([(3, 26), (11, 12), (14, 14), (7, 28)], BLANC + (90,), cible=couche)
    t.polygone([(17, 29), (25, 13), (27, 15), (21, 30)], BLANC + (60,), cible=couche)
    t.ligne([(6, 6), (12, 13), (10, 19)], BLANC + (120,), 0.6, cible=couche)
    t.poser(couche, m)
    _bevel(t, m, BLANC, GLACE_TRAIT)
    t.brillance(m, 3.0, 2.5, 16.0, 9.5, alpha=200, flou=0.8)
    t.brillance(m, 21.0, 20.0, 29.0, 27.0, alpha=90, flou=1.2)
    t.contour(GLACE_TRAIT, 1.0)
    return t.finir()


def bloc_fissure():
    t = Tuile()
    m = _cadre_bloc(t, 2.6)
    t.peindre(m, [(0, melange(PIERRE_HAUT, (210, 200, 196), 0.5)),
                  (14, melange(PIERRE, (176, 168, 168), 0.5)),
                  (32, melange(PIERRE_BAS, (140, 132, 136), 0.5))])
    t.grain(m, 67, force=30)
    couche = t.calque()
    fissures = ([(16, 1), (14.5, 7), (17, 12), (13, 18), (15, 25), (12.5, 31)],
                [(14.5, 7), (8, 9)], [(17, 12), (24, 10)], [(13, 18), (5, 21)],
                [(15, 25), (23, 27)], [(23, 27), (28, 24)])
    for pts in fissures:
        t.ligne(pts, assombrir(PIERRE_TRAIT, 0.2) + (225,), 0.75, cible=couche)
        t.ligne([(x + 0.7, y + 0.4) for x, y in pts], PIERRE_CLAIR + (120,), 0.55, cible=couche)
    t.poser(couche, m)
    _bevel(t, m, PIERRE_CLAIR, PIERRE_TRAIT)
    t.contour(assombrir(PIERRE_TRAIT, 0.25), 1.0)
    return t.finir()


def bloc_choco():
    t = Tuile()
    m = _cadre_bloc(t, 2.8)
    t.peindre(m, [(0, CHOCO_CLAIR), (13, CHOCO), (32, CHOCO_BAS)])
    couche = t.calque()
    for i in range(2):
        for j in range(2):
            x0, y0 = 2.5 + i * 13.8, 2.5 + j * 13.8
            t.arrondi(x0, y0, x0 + 12.0, y0 + 12.0, 1.4, eclaircir(CHOCO, 0.16) + (255,), cible=couche)
            t.arrondi(x0 + 0.8, y0 + 0.8, x0 + 11.2, y0 + 6.0, 1.2,
                      eclaircir(CHOCO_CLAIR, 0.22) + (150,), cible=couche)
            t.rect(x0 + 0.8, y0 + 10.0, x0 + 11.2, y0 + 11.6, CHOCO_BAS + (150,), cible=couche)
    t.poser(couche, m)
    _bevel(t, m, eclaircir(CHOCO_CLAIR, 0.3), CHOCO_TRAIT)
    t.brillance(m, 4.0, 3.0, 14.0, 8.0, alpha=70, flou=1.0)
    t.contour(CHOCO_TRAIT, 1.0)
    return t.finir()


def qblock():
    t = Tuile()
    m = _cadre_bloc(t, 3.2)
    t.peindre(m, [(0, OR_CLAIR), (7, OR), (24, OR_BAS), (32, assombrir(OR_BAS, 0.18))])
    couche = t.calque()
    t.arrondi(2.6, 2.6, T - 2.6, T - 2.6, 2.2, OR_TRAIT + (70,), cible=couche)
    t.arrondi(3.4, 3.4, T - 3.4, T - 3.4, 1.8, melange(OR, OR_CLAIR, 0.35) + (255,), cible=couche)
    t.poser(couche, m)
    # rivets aux coins
    couche = t.calque()
    for cx, cy in ((4.6, 4.6), (T - 4.6, 4.6), (4.6, T - 4.6), (T - 4.6, T - 4.6)):
        t.ellipse(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, OR_TRAIT + (255,), cible=couche)
        t.ellipse(cx - 1.0, cy - 1.1, cx + 1.0, cy + 0.7, OR_CLAIR + (255,), cible=couche)
    t.poser(couche, m)
    # point d'interrogation
    pts = [(11.4, 13.0), (11.9, 10.2), (14.1, 8.5), (17.0, 8.6), (19.5, 10.0),
           (19.9, 12.4), (18.6, 14.4), (16.6, 15.9), (15.9, 17.6), (15.9, 19.0)]
    couche = t.calque()
    t.ligne(pts, OR_TRAIT + (255,), 3.4, cible=couche)
    t.ellipse(14.0, 20.6, 17.8, 24.2, OR_TRAIT + (255,), cible=couche)
    t.poser(couche, m)
    couche = t.calque()
    t.ligne([(x, y - 0.35) for x, y in pts], (255, 250, 225, 255), 1.5, cible=couche)
    t.ellipse(14.9, 21.4, 16.9, 23.4, (255, 250, 225, 255), cible=couche)
    t.poser(couche, m)
    _bevel(t, m, BLANC, OR_TRAIT)
    t.brillance(m, 3.0, 2.5, 13.0, 7.5, alpha=110, flou=0.9)
    t.contour(assombrir(OR_TRAIT, 0.3), 1.0)
    return t.finir()


# --------------------------------------------------------------------------
# Dangers
# --------------------------------------------------------------------------
def pics(vers_le_bas=False):
    t = Tuile()
    for i in range(4):
        x = 1.0 + i * 7.6
        t.polygone([(x, 30.0), (x + 3.8, 2.5), (x + 7.6, 30.0)], ACIER + (255,))
    t.rect(GX0, 28.5, GX1, T, ACIER_BAS + (255,))
    m = t.masque()
    t.rect(GX0, -2, GX1, 34, 255, m)
    m = ImageChops.multiply(m, t.im.split()[3])
    t.peindre(m, [(1, ACIER_CLAIR), (12, ACIER), (26, ACIER_BAS), (32, assombrir(ACIER_BAS, 0.2))])
    couche = t.calque()
    for i in range(4):
        x = 1.0 + i * 7.6
        t.polygone([(x + 2.6, 26.0), (x + 3.8, 3.5), (x + 4.6, 26.0)], BLANC + (170,), cible=couche)
        t.polygone([(x + 5.2, 27.0), (x + 4.0, 5.0), (x + 7.0, 27.0)], ACIER_TRAIT + (90,), cible=couche)
    t.rect(GX0, 28.8, GX1, 29.8, ACIER_CLAIR + (150,), cible=couche)
    t.poser(couche, m)
    t.contour(ACIER_TRAIT, 1.0)
    im = t.finir()
    return im.transpose(Image.FLIP_TOP_BOTTOM) if vers_le_bas else im


def ronces():
    t = Tuile()
    base = (146, 74, 174)
    pointe = (206, 130, 230)
    m = t.masque()
    t.ellipse(0.5, 12.0, 12.0, 26.0, 255, m)
    t.ellipse(8.0, 9.0, 24.0, 26.0, 255, m)
    t.ellipse(20.0, 13.0, 31.5, 26.0, 255, m)
    t.rect(GX0, 22.0, GX1, 27.0, 255, m)
    epines = ((3.0, 12.5, 1.6, 6.0), (8.0, 9.5, 1.7, 7.5), (13.5, 6.5, 1.9, 9.0),
              (19.0, 8.5, 1.7, 8.0), (24.5, 10.5, 1.6, 6.5), (29.5, 12.0, 1.5, 6.0))
    for ex, ey, ew, eh in epines:
        for k in (-T, 0, T):
            t.polygone([(ex - ew + k, ey + 4), (ex + k, ey - eh + 4), (ex + ew + k, ey + 4)], 255, m)
    t.peindre(m, [(0, pointe), (10, melange(pointe, base, 0.5)), (20, base), (27, assombrir(base, 0.3))])
    couche = t.calque()
    for ex, ey, ew, eh in epines:
        t.polygone([(ex - ew * 0.5, ey + 3), (ex - 0.2, ey - eh + 4.6), (ex + 0.3, ey + 3)],
                   eclaircir(pointe, 0.5) + (150,), cible=couche)
    t.ellipse(2.0, 15.0, 9.0, 20.0, eclaircir(pointe, 0.3) + (90,), cible=couche)
    t.poser(couche, m, flou=0.15)
    t.contour((62, 26, 84), 1.0)
    return t.finir()


def scie():
    t = Tuile()
    m = t.masque()
    dents = 12
    pts = []
    for i in range(dents * 2):
        a = math.pi * i / dents
        r = 15.0 if i % 2 == 0 else 11.6
        pts.append((16 + r * math.cos(a), 16 + r * math.sin(a)))
    t.polygone(pts, 255, m)
    t.ellipse(2.0, 2.0, 30.0, 30.0, 255, m)
    t.peindre(m, [(1, ACIER_CLAIR), (14, ACIER), (30, ACIER_BAS)])
    couche = t.calque()
    t.ellipse(6.5, 6.5, 25.5, 25.5, ACIER_TRAIT + (55,), cible=couche)
    t.ellipse(7.5, 7.5, 24.5, 24.5, melange(ACIER, ACIER_CLAIR, 0.4) + (255,), cible=couche)
    t.ellipse(12.0, 12.0, 20.0, 20.0, ACIER_TRAIT + (255,), cible=couche)
    t.ellipse(13.0, 12.8, 19.0, 18.6, ACIER_CLAIR + (255,), cible=couche)
    t.ellipse(14.6, 14.6, 17.4, 17.4, ACIER_TRAIT + (255,), cible=couche)
    for a in range(0, 360, 60):
        r = math.radians(a)
        t.ellipse(16 + 8.6 * math.cos(r) - 0.9, 16 + 8.6 * math.sin(r) - 0.9,
                  16 + 8.6 * math.cos(r) + 0.9, 16 + 8.6 * math.sin(r) + 0.9,
                  ACIER_TRAIT + (140,), cible=couche)
    t.poser(couche, m)
    t.brillance(m, 4.0, 3.5, 16.0, 11.0, alpha=140, flou=1.0)
    t.contour(ACIER_TRAIT, 1.0)
    return t.finir()


def gelee(couleurs, dessus=True, graine=0):
    """Slime / gomme toxique. `dessus` : surface ondulée et gouttes."""
    clair, moyen, bas, trait = couleurs
    t = Tuile()
    m = t.masque()
    if dessus:
        def surf(x):
            return 6.2 + 1.6 * math.sin(2 * math.pi * x / T + 0.4) + 0.8 * math.sin(4 * math.pi * x / T + 2.0)
        t.polygone([(GX0, 36)] + [(x, surf(x)) for x in _XS] + [(GX1, 36)], 255, m)
        for bx in (6.0, 15.0, 25.0):
            for k in (-T, 0, T):
                t.ellipse(bx - 3.0 + k, surf(bx) - 1.2, bx + 3.0 + k, surf(bx) + 3.4, 255, m)
        t.peindre(m, [(4, clair), (9, moyen), (20, bas), (32, assombrir(bas, 0.2))])
    else:
        t.rect(GX0, -2, GX1, 34, 255, m)
        t.peindre(m, [(0, moyen), (16, bas), (32, assombrir(bas, 0.22))])
    t.grain(m, 71 + graine, force=22)

    couche = t.calque()
    rng = random.Random(1300 + graine)
    haut = 9.0 if dessus else 3.0
    for _ in range(4):
        cx, cy = rng.uniform(4.0, 28.0), rng.uniform(haut, 27.0)
        r = rng.uniform(1.4, 2.8)
        t.ellipse(cx - r, cy - r, cx + r, cy + r, assombrir(bas, 0.22) + (120,), cible=couche)
        t.ellipse(cx - r + 0.5, cy - r + 0.5, cx + r - 0.5, cy + r - 0.5, clair + (70,), cible=couche)
    if dessus:
        t.ellipse(3.0, 5.4, 13.0, 9.0, eclaircir(clair, 0.5) + (150,), cible=couche)
        t.ellipse(18.0, 6.4, 24.0, 9.0, eclaircir(clair, 0.5) + (110,), cible=couche)
    t.poser(couche, m, flou=0.2)
    if dessus:
        couche = t.calque()
        t.ligne([(x, surf(x) + 0.5) for x in _XS], eclaircir(clair, 0.35) + (190,), 0.7, cible=couche)
        t.poser(couche, m)
        contour = t.masque()
        t.rect(GX0, -2, GX1, 34, 255, contour)
        a = ImageChops.multiply(t.im.split()[3], contour)
        dil = a
        for _ in range(int(0.8 * SS)):
            dil = dil.filter(ImageFilter.MaxFilter(3))
        bord = ImageChops.subtract(dil, a)
        couche = Image.new("RGBA", (W, S), trait + (0,))
        couche.putalpha(bord)
        t.im.alpha_composite(couche)
    return t.finir()


# --------------------------------------------------------------------------
# Objets & interactifs
# --------------------------------------------------------------------------
def piece():
    t = Tuile()
    m = t.masque()
    t.ellipse(4.5, 2.0, 27.5, 30.0, 255, m)
    t.peindre(m, [(2, OR_CLAIR), (10, OR), (26, OR_BAS), (30, assombrir(OR_BAS, 0.25))])
    couche = t.calque()
    t.ellipse(7.0, 4.5, 25.0, 27.5, OR_TRAIT + (85,), cible=couche)
    t.ellipse(8.0, 5.5, 24.0, 26.5, melange(OR, OR_CLAIR, 0.25) + (255,), cible=couche)
    # étoile centrale
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        r = 7.4 if i % 2 == 0 else 3.3
        pts.append((16 + r * math.cos(a), 16 + r * math.sin(a)))
    t.polygone(pts, OR_BAS + (255,), cible=couche)
    t.polygone([(x, y - 0.6) for x, y in pts], OR_CLAIR + (255,), cible=couche)
    t.poser(couche, m)
    t.relief(m, 0, 2.4, 0.5, BLANC, 140)
    t.relief(m, 0, -2.4, 0.6, OR_TRAIT, 120)
    t.brillance(m, 7.5, 4.0, 15.5, 11.0, alpha=165, flou=0.9)
    t.contour(OR_TRAIT, 1.0)
    return t.finir()


def ressort():
    t = Tuile()
    rouge, rouge_b = (244, 96, 104), (196, 56, 72)
    m = t.masque()
    t.arrondi(3.0, 24.0, 29.0, 31.0, 2.0, 255, m)      # socle
    t.arrondi(5.0, 7.0, 27.0, 13.5, 2.6, 255, m)       # plateau
    for y in (14.5, 18.0, 21.5):
        t.arrondi(7.0, y, 25.0, y + 3.0, 1.4, 255, m)  # spires
    t.peindre(m, [(6, eclaircir(rouge, 0.35)), (11, rouge), (14, ACIER_CLAIR),
                  (22, ACIER_BAS), (24, rouge), (31, rouge_b)])
    couche = t.calque()
    t.arrondi(5.8, 7.8, 26.2, 10.2, 1.6, eclaircir(rouge, 0.5) + (170,), cible=couche)
    for y in (14.5, 18.0, 21.5):
        t.arrondi(7.6, y + 0.4, 24.4, y + 1.2, 0.6, BLANC + (150,), cible=couche)
        t.arrondi(7.6, y + 2.2, 24.4, y + 2.9, 0.6, ACIER_TRAIT + (90,), cible=couche)
    t.arrondi(4.0, 25.0, 28.0, 27.0, 1.2, eclaircir(rouge, 0.4) + (140,), cible=couche)
    t.poser(couche, m)
    t.contour(assombrir(rouge_b, 0.45), 1.0)
    return t.finir()


def _mat(t, m, x=14.6, y0=-2, y1=34):
    t.rect(x, y0, x + 2.8, y1, 255, m)


def checkpoint_pole():
    t = Tuile()
    m = t.masque()
    _mat(t, m)
    t.uni(m, ACIER)
    couche = t.calque()
    t.rect(14.6, -2, 15.6, 34, ACIER_CLAIR + (230,), cible=couche)
    t.rect(16.8, -2, 17.4, 34, ACIER_TRAIT + (120,), cible=couche)
    t.poser(couche, m)
    t.contour(ACIER_TRAIT, 0.75)
    return t.finir()


def checkpoint_top():
    t = Tuile()
    m = t.masque()
    t.rect(14.6, 4.0, 17.4, 34, 255, m)
    t.ellipse(13.0, 1.0, 19.0, 7.0, 255, m)
    t.uni(m, ACIER)
    couche = t.calque()
    t.rect(14.6, 4.0, 15.6, 34, ACIER_CLAIR + (230,), cible=couche)
    t.rect(16.8, 4.0, 17.4, 34, ACIER_TRAIT + (120,), cible=couche)
    t.ellipse(13.6, 1.6, 17.2, 5.2, OR_CLAIR + (255,), cible=couche)
    t.ellipse(13.0, 1.0, 19.0, 7.0, OR + (0,), cible=couche)
    t.poser(couche, m)
    # boule dorée
    mb = t.masque()
    t.ellipse(12.8, 0.8, 19.2, 7.2, 255, mb)
    t.peindre(mb, [(0.8, OR_CLAIR), (3.0, OR), (7.2, OR_BAS)])
    t.brillance(mb, 13.6, 1.6, 16.6, 4.0, alpha=190, flou=0.4)
    # drapeau
    mf = t.masque()
    t.polygone([(17.4, 6.0), (30.0, 9.0), (26.5, 11.6), (30.0, 14.4), (17.4, 16.6)], 255, mf)
    t.peindre(mf, [(6, GOMME_CLAIR), (11, GOMME), (17, GOMME_BAS)])
    couche = t.calque()
    t.polygone([(18.0, 7.0), (27.5, 9.4), (25.5, 11.0), (18.0, 10.4)],
               eclaircir(GOMME_CLAIR, 0.5) + (130,), cible=couche)
    t.ellipse(20.0, 11.6, 23.4, 14.6, BLANC + (200,), cible=couche)
    t.poser(couche, mf)
    t.contour(assombrir(GOMME_TRAIT, 0.1), 0.9)
    return t.finir()


def checkpoint_base():
    t = Tuile()
    m = t.masque()
    t.rect(14.6, -2, 17.4, 26.0, 255, m)
    t.polygone([(6.0, 31.5), (26.0, 31.5), (23.0, 23.0), (9.0, 23.0)], 255, m)
    t.peindre(m, [(0, ACIER), (22.5, ACIER), (23.5, PIERRE_HAUT), (31.5, PIERRE_BAS)])
    couche = t.calque()
    t.rect(14.6, -2, 15.6, 24.0, ACIER_CLAIR + (230,), cible=couche)
    t.rect(16.8, -2, 17.4, 24.0, ACIER_TRAIT + (120,), cible=couche)
    t.polygone([(9.2, 23.6), (22.8, 23.6), (22.2, 25.4), (9.8, 25.4)],
               PIERRE_CLAIR + (180,), cible=couche)
    t.poser(couche, m)
    t.contour(PIERRE_TRAIT, 0.9)
    return t.finir()


def porte():
    t = Tuile()
    m = t.masque()
    t.rect(4.0, 8.0, 28.0, T, 255, m)
    t.ellipse(4.0, 1.0, 28.0, 15.0, 255, m)
    t.peindre(m, [(1, BOIS_CLAIR), (10, BOIS), (26, BOIS_BAS), (32, assombrir(BOIS_BAS, 0.25))])
    couche = t.calque()
    for x in (10.6, 16.0, 21.4):
        t.ligne([(x, 3.0), (x, 31.5)], assombrir(BOIS_BAS, 0.35) + (140,), 0.6, cible=couche)
        t.ligne([(x + 0.7, 3.0), (x + 0.7, 31.5)], eclaircir(BOIS_CLAIR, 0.3) + (90,), 0.6, cible=couche)
    t.rect(4.5, 17.0, 27.5, 19.2, assombrir(BOIS_BAS, 0.2) + (130,), cible=couche)
    t.rect(4.5, 19.2, 27.5, 20.2, eclaircir(BOIS_CLAIR, 0.3) + (110,), cible=couche)
    t.ellipse(20.0, 21.0, 24.2, 25.2, OR_TRAIT + (255,), cible=couche)
    t.ellipse(20.6, 21.4, 23.4, 24.2, OR + (255,), cible=couche)
    t.ellipse(21.0, 21.8, 22.4, 23.0, OR_CLAIR + (255,), cible=couche)
    t.poser(couche, m)
    t.relief(m, 0, 2.2, 0.6, BLANC, 110)
    t.relief(m, -2.4, 0, 0.8, BOIS_TRAIT, 120)
    t.contour(BOIS_TRAIT, 1.0)
    return t.finir()


def echelle():
    t = Tuile()
    m = t.masque()
    for x in (5.5, 23.0):
        t.rect(x, -2, x + 3.5, 34, 255, m)
    for y in (2.0, 12.6, 23.2):
        t.rect(5.5, y, 26.5, y + 2.8, 255, m)
    t.peindre(m, [(0, BOIS), (32, BOIS)])
    couche = t.calque()
    for x in (5.5, 23.0):
        t.rect(x, -2, x + 1.1, 34, eclaircir(BOIS_CLAIR, 0.15) + (255,), cible=couche)
        t.rect(x + 2.6, -2, x + 3.5, 34, BOIS_BAS + (255,), cible=couche)
    for y in (2.0, 12.6, 23.2):
        t.rect(5.5, y, 26.5, y + 0.9, eclaircir(BOIS_CLAIR, 0.2) + (255,), cible=couche)
        t.rect(5.5, y + 2.0, 26.5, y + 2.8, BOIS_BAS + (255,), cible=couche)
    t.poser(couche, m)
    t.grain(m, 83, force=16)
    t.contour(BOIS_TRAIT, 0.9)
    return t.finir()


def dalle_traversable():
    t = Tuile()
    m = t.masque()
    t.arrondi(GX0, 0, GX1, 11.0, 2.0, 255, m)
    t.peindre(m, [(0, DALLE_TRAIT), (0.95, DALLE_TRAIT), (1.05, eclaircir(DALLE_HAUT, 0.35)),
                  (3.0, DALLE_HAUT), (6.5, DALLE), (11.0, DALLE_BAS)])
    couche = t.calque()
    for x in (0.0, 16.0, 32.0):
        t.ligne([(x, 1.2), (x, 10.5)], DALLE_TRAIT + (110,), 0.55, cible=couche)
        t.ligne([(x + 0.6, 1.2), (x + 0.6, 10.5)], eclaircir(DALLE_HAUT, 0.4) + (90,), 0.5, cible=couche)
    t.rect(GX0, 1.05, GX1, 2.2, eclaircir(DALLE_HAUT, 0.55) + (130,), cible=couche)
    t.rect(GX0, 9.2, GX1, 11.0, assombrir(DALLE_BAS, 0.3) + (120,), cible=couche)
    t.poser(couche, m)
    t.grain(m, 91, force=14)
    return t.finir()


# --------------------------------------------------------------------------
# Décors
# --------------------------------------------------------------------------
def tombe():
    t = Tuile()
    m = t.masque()
    t.rect(8.0, 10.0, 24.0, 29.0, 255, m)
    t.ellipse(8.0, 4.0, 24.0, 18.0, 255, m)
    t.peindre(m, [(4, PIERRE_HAUT), (16, PIERRE), (29, PIERRE_BAS)])
    couche = t.calque()
    t.rect(14.6, 10.0, 17.4, 22.0, PIERRE_TRAIT + (170,), cible=couche)
    t.rect(11.0, 13.4, 21.0, 16.2, PIERRE_TRAIT + (170,), cible=couche)
    t.rect(15.2, 10.6, 16.6, 21.4, assombrir(PIERRE_BAS, 0.2) + (150,), cible=couche)
    t.ligne([(10.0, 24.0), (13.0, 27.0)], PIERRE_TRAIT + (110,), 0.5, cible=couche)
    t.poser(couche, m)
    t.relief(m, 2.2, 0, 0.5, PIERRE_CLAIR, 150)
    t.relief(m, -2.4, 0, 0.7, PIERRE_TRAIT, 140)
    t.contour(PIERRE_TRAIT, 1.0)
    # touffe d'herbe au pied
    t2 = Tuile()
    mg = t2.masque()
    t2.ellipse(3.0, 27.0, 29.0, 33.0, 255, mg)
    t2.peindre(mg, [(27, HERBE_VIF), (30, HERBE_MOY), (33, HERBE_SOMBRE)])
    t2.im.alpha_composite(t.im)
    t.im = t2.im
    return t.finir()


def os():
    t = Tuile()
    m = t.masque()
    for ang, cx, cy, lg in ((-16, 16, 20.0, 9.5), (24, 15, 25.0, 7.5)):
        a = math.radians(ang)
        dx, dy = lg * math.cos(a), lg * math.sin(a)
        t.ligne([(cx - dx, cy - dy), (cx + dx, cy + dy)], 255, 3.0, cible=m)
        for sx, sy in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
            nx, ny = -math.sin(a) * 2.0, math.cos(a) * 2.0
            t.ellipse(sx - nx - 2.0, sy - ny - 2.0, sx - nx + 2.0, sy - ny + 2.0, 255, cible=m)
            t.ellipse(sx + nx - 2.0, sy + ny - 2.0, sx + nx + 2.0, sy + ny + 2.0, 255, cible=m)
    t.ellipse(5.0, 6.0, 17.0, 17.0, 255, m)
    t.peindre(m, [(5, (255, 252, 240)), (14, (232, 226, 210)), (30, (196, 188, 176))])
    couche = t.calque()
    t.ellipse(8.0, 10.0, 10.6, 13.4, (86, 74, 82, 255), cible=couche)
    t.ellipse(12.0, 10.0, 14.6, 13.4, (86, 74, 82, 255), cible=couche)
    t.ellipse(9.8, 14.0, 12.4, 16.0, (120, 108, 112, 200), cible=couche)
    t.ellipse(6.4, 7.2, 12.0, 11.0, BLANC + (150,), cible=couche)
    t.poser(couche, m)
    t.contour((92, 78, 88), 1.0)
    return t.finir()


def torche():
    t = Tuile()
    m = t.masque()
    t.rect(13.6, 12.0, 18.4, 31.0, 255, m)
    t.peindre(m, [(12, BOIS_CLAIR), (20, BOIS), (31, BOIS_BAS)])
    couche = t.calque()
    t.rect(13.6, 12.0, 15.0, 31.0, eclaircir(BOIS_CLAIR, 0.25) + (255,), cible=couche)
    t.rect(17.4, 12.0, 18.4, 31.0, BOIS_TRAIT + (140,), cible=couche)
    for y in (17.0, 23.0):
        t.rect(13.6, y, 18.4, y + 0.7, BOIS_TRAIT + (110,), cible=couche)
    t.poser(couche, m)
    t.contour(BOIS_TRAIT, 0.9)
    # flamme
    mf = t.masque()
    t.polygone([(16.0, 0.5), (20.0, 5.5), (21.0, 10.0), (19.0, 14.0), (16.0, 15.0),
                (13.0, 14.0), (11.0, 10.0), (12.2, 5.0)], 255, mf)
    t.peindre(mf, [(0.5, (255, 250, 200)), (5.0, (255, 214, 82)), (10.0, (250, 146, 48)),
                   (15.0, (224, 92, 60))])
    couche = t.calque()
    t.polygone([(16.0, 4.0), (18.2, 8.0), (17.4, 12.0), (16.0, 13.2), (14.6, 12.0), (13.9, 8.0)],
               (255, 246, 190, 220), cible=couche)
    t.poser(couche, mf, flou=0.25)
    return t.finir()


def cristal():
    t = Tuile()
    grands = ([(16.0, 3.0), (21.5, 12.0), (19.5, 29.5), (12.5, 29.5), (10.5, 12.0)],)
    petits = ([(24.5, 13.0), (28.5, 19.0), (27.0, 29.5), (22.0, 29.5), (21.0, 19.0)],
              [(7.5, 17.0), (10.5, 21.0), (9.5, 29.5), (5.0, 29.5), (4.0, 21.0)])
    for pts in petits:
        m = t.masque()
        t.polygone(pts, 255, m)
        t.peindre(m, [(12, eclaircir(GOO_CLAIR, 0.3)), (20, GOO), (30, GOO_BAS)])
        couche = t.calque()
        t.polygone([(pts[0][0], pts[0][1]), (pts[1][0], pts[1][1]),
                    (pts[2][0], pts[2][1]), ((pts[2][0] + pts[3][0]) / 2, pts[2][1])],
                   BLANC + (60,), cible=couche)
        t.poser(couche, m)
    for pts in grands:
        m = t.masque()
        t.polygone(pts, 255, m)
        t.peindre(m, [(3, GLACE_CLAIR), (12, GLACE), (30, GLACE_BAS)])
        couche = t.calque()
        t.polygone([(16.0, 3.4), (18.0, 12.0), (17.0, 29.0), (14.6, 29.0), (14.0, 12.0)],
                   BLANC + (110,), cible=couche)
        t.polygone([(18.6, 12.4), (21.2, 12.6), (19.2, 29.0), (17.4, 29.0)],
                   GLACE_TRAIT + (70,), cible=couche)
        t.poser(couche, m)
    t.contour(GLACE_TRAIT, 0.9)
    couche = t.calque()
    t.ellipse(10.0, 26.0, 24.0, 31.5, (180, 230, 255, 70), cible=couche)
    t.poser(couche, flou=0.6)
    return t.finir()


def champignon(grand=False):
    t = Tuile()
    if grand:
        cx, cy, rx, ry, pied = 16.0, 14.0, 13.0, 8.5, 5.0
        haut_pied, bas_pied = 15.0, 31.0
    else:
        cx, cy, rx, ry, pied = 16.0, 19.0, 8.5, 6.0, 3.6
        haut_pied, bas_pied = 20.0, 31.0
    mp = t.masque()
    t.arrondi(cx - pied, haut_pied, cx + pied, bas_pied, 1.6, 255, mp)
    t.peindre(mp, [(haut_pied, (255, 248, 234)), (bas_pied, (216, 196, 188))])
    couche = t.calque()
    t.rect(cx - pied, haut_pied, cx - pied + 1.5, bas_pied, BLANC + (200,), cible=couche)
    t.rect(cx + pied - 1.6, haut_pied, cx + pied, bas_pied, (188, 168, 166, 190), cible=couche)
    t.poser(couche, mp)

    mc = t.masque()
    t.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, 255, mc)
    t.rect(cx - rx, cy, cx + rx, cy + ry * 0.55, 255, mc)
    t.peindre(mc, [(cy - ry, GOMME_CLAIR), (cy - ry * 0.2, GOMME), (cy + ry * 0.7, GOMME_BAS)])
    couche = t.calque()
    pois = ((-0.45, -0.35, 0.26), (0.38, -0.2, 0.2), (0.0, -0.62, 0.17), (-0.05, 0.05, 0.22))
    for px, py, pr in pois:
        t.ellipse(cx + px * rx - pr * rx, cy + py * ry - pr * ry * 1.25,
                  cx + px * rx + pr * rx, cy + py * ry + pr * ry * 1.25,
                  (255, 248, 242, 235), cible=couche)
    t.ellipse(cx - rx * 0.85, cy - ry * 0.85, cx - rx * 0.1, cy - ry * 0.3,
              BLANC + (95,), cible=couche)
    t.rect(cx - rx, cy + ry * 0.2, cx + rx, cy + ry * 0.6, GOMME_TRAIT + (60,), cible=couche)
    t.poser(couche, mc, flou=0.15)
    t.contour(assombrir(GOMME_TRAIT, 0.1), 1.0)
    return t.finir()


def fleur():
    t = Tuile()
    mt = t.masque()
    t.ligne([(16.0, 31.0), (15.4, 24.0), (16.4, 18.0)], 255, 1.3, cible=mt)
    t.ellipse(17.0, 21.0, 24.0, 25.0, 255, mt)
    t.ellipse(8.5, 24.0, 15.0, 28.0, 255, mt)
    t.peindre(mt, [(18, HERBE), (31, HERBE_SOMBRE)])
    couche = t.calque()
    t.ellipse(18.0, 21.6, 22.6, 23.6, eclaircir(HERBE_VIF, 0.2) + (150,), cible=couche)
    t.poser(couche, mt)

    mp = t.masque()
    for i in range(6):
        a = math.radians(i * 60 - 90)
        px, py = 16.0 + 5.4 * math.cos(a), 14.0 + 5.4 * math.sin(a)
        t.ellipse(px - 4.1, py - 4.1, px + 4.1, py + 4.1, 255, mp)
    t.peindre(mp, [(4, GOMME_CLAIR), (13, GOMME), (23, GOMME_BAS)])
    couche = t.calque()
    for i in range(6):
        a = math.radians(i * 60 - 90)
        px, py = 16.0 + 5.4 * math.cos(a), 14.0 + 5.4 * math.sin(a)
        t.ellipse(px - 2.8, py - 3.2, px + 1.6, py + 0.6, eclaircir(GOMME_CLAIR, 0.5) + (130,),
                  cible=couche)
    t.poser(couche, mp, flou=0.2)

    mc = t.masque()
    t.ellipse(11.8, 9.8, 20.2, 18.2, 255, mc)
    t.peindre(mc, [(9.8, OR_CLAIR), (13, OR), (18.2, OR_BAS)])
    t.brillance(mc, 13.0, 11.0, 17.0, 14.0, alpha=170, flou=0.4)
    t.contour(assombrir(GOMME_TRAIT, 0.15), 0.9)
    return t.finir()


def touffe():
    t = Tuile()
    m = t.masque()
    brins = ((7.0, 31.5, 4.0, 14.0), (11.5, 31.5, 1.2, 8.0), (16.0, 31.5, -0.5, 6.0),
             (20.0, 31.5, -3.0, 12.0), (25.0, 31.5, -5.0, 17.0))
    for bx, by, dx, h in brins:
        t.polygone([(bx - 1.9, by), (bx + dx, by - h), (bx + dx + 1.0, by - h + 1.2),
                    (bx + 1.9, by)], 255, m)
    t.peindre(m, [(13, HERBE_VIF), (22, HERBE), (28, HERBE_MOY), (32, HERBE_SOMBRE)])
    couche = t.calque()
    for bx, by, dx, h in brins:
        t.polygone([(bx - 0.6, by - 1.0), (bx + dx, by - h + 0.6), (bx + dx + 0.5, by - h + 1.6),
                    (bx + 0.5, by - 1.0)], eclaircir(HERBE_VIF, 0.4) + (140,), cible=couche)
    t.poser(couche, m)
    t.contour(HERBE_TRAIT, 0.65)
    return t.finir()


def etoile():
    t = Tuile()
    m = t.masque()
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        r = 14.0 if i % 2 == 0 else 5.8
        pts.append((16 + r * math.cos(a), 16 + r * math.sin(a)))
    t.polygone(pts, 255, m)
    t.peindre(m, [(2, (255, 252, 208)), (12, OR), (30, OR_BAS)])
    couche = t.calque()
    t.polygone([(16, 3.0), (19.0, 13.0), (16, 19.0), (13.0, 13.0)], (255, 252, 226, 190), cible=couche)
    t.poser(couche, m, flou=0.3)
    t.brillance(m, 10.0, 6.0, 16.0, 11.0, alpha=140, flou=0.7)
    t.contour(OR_TRAIT, 1.0)
    return t.finir()


def galets():
    t = Tuile()
    galets = ((8.5, 25.0, 6.5, 4.6), (20.5, 26.5, 5.6, 3.8), (15.0, 20.5, 4.4, 3.2))
    for cx, cy, rx, ry in galets:
        m = t.masque()
        t.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, 255, m)
        t.peindre(m, [(cy - ry, PIERRE_HAUT), (cy, PIERRE), (cy + ry, PIERRE_BAS)])
        t.brillance(m, cx - rx * 0.8, cy - ry * 0.85, cx + rx * 0.1, cy - ry * 0.1,
                    alpha=130, flou=0.5)
    t.contour(PIERRE_TRAIT, 0.9)
    return t.finir()


def nuage(bord=None):
    t = Tuile()

    def haut(x):
        return 8.0 - 3.4 * abs(math.sin(math.pi * x / 16.0)) ** 0.8

    m = t.masque()
    t.polygone([(GX0, 26.0)] + [(x, haut(x)) for x in _XS] + [(GX1, 26.0)], 255, m)
    if bord in ("gauche", "seul"):
        vide = Image.new("L", (W, S), 0)
        ImageDraw.Draw(vide).rectangle(Tuile.boite(GX0, -4, 5.0, 36), fill=255)
        m = ImageChops.subtract(m, vide)
        t.ellipse(2.0, 9.0, 18.0, 26.0, 255, m)
        t.ellipse(5.0, 5.0, 21.0, 22.0, 255, m)
    if bord in ("droite", "seul"):
        vide = Image.new("L", (W, S), 0)
        ImageDraw.Draw(vide).rectangle(Tuile.boite(T - 5.0, -4, GX1, 36), fill=255)
        m = ImageChops.subtract(m, vide)
        t.ellipse(T - 18.0, 9.0, T - 2.0, 26.0, 255, m)
        t.ellipse(T - 21.0, 5.0, T - 5.0, 22.0, 255, m)
    t.peindre(m, [(2, BLANC), (14, (248, 252, 255)), (21, BLANC_BLEU), (26, (196, 216, 244))])
    t.relief(m, 0, 3.0, 1.0, BLANC, 200)
    t.relief(m, 0, -3.0, 1.2, (150, 180, 220), 120)
    return t.finir()


def colline():
    t = Tuile()
    m = t.masque()
    t.ellipse(-1.5, 6.0, 33.5, 54.0, 255, m)
    t.peindre(m, [(6, HERBE_VIF), (12, HERBE), (24, HERBE_MOY), (32, HERBE_SOMBRE)])
    t.grain(m, 101, force=18)
    couche = t.calque()
    t.ellipse(3.0, 9.0, 17.0, 17.0, eclaircir(HERBE_VIF, 0.35) + (110,), cible=couche)
    t.poser(couche, m, flou=0.6)
    return t.finir()


def tronc():
    t = Tuile()
    m = t.masque()
    t.polygone([(10.5, -2), (21.5, -2), (23.0, 34), (9.0, 34)], 255, m)
    t.peindre(m, [(0, BOIS), (32, BOIS_BAS)])
    couche = t.calque()
    t.polygone([(10.5, -2), (13.6, -2), (12.4, 34), (9.0, 34)],
               eclaircir(BOIS_CLAIR, 0.15) + (255,), cible=couche)
    t.polygone([(19.4, -2), (21.5, -2), (23.0, 34), (20.6, 34)], BOIS_TRAIT + (150,), cible=couche)
    for y in (4.0, 15.0, 26.0):
        t.ligne([(12.0, y), (14.5, y + 2.0), (12.4, y + 4.0)], BOIS_TRAIT + (110,), 0.5, cible=couche)
    t.poser(couche, m)
    t.grain(m, 107, force=16)
    t.contour(BOIS_TRAIT, 0.9)
    return t.finir()


def feuillage():
    t = Tuile()
    m = t.masque()
    for cx, cy, r in ((16.0, 15.0, 15.0), (6.0, 20.0, 8.5), (26.0, 20.0, 8.5),
                      (10.0, 8.0, 7.5), (22.0, 8.0, 7.5)):
        t.ellipse(cx - r, cy - r, cx + r, cy + r, 255, m)
    t.rect(4.0, 20.0, 28.0, 30.0, 255, m)
    t.peindre(m, [(0, eclaircir(HERBE_VIF, 0.1)), (8, HERBE), (20, HERBE_MOY), (32, HERBE_SOMBRE)])
    t.grain(m, 113, force=24)
    couche = t.calque()
    for cx, cy, r in ((9.0, 7.0, 4.6), (20.0, 5.5, 4.0), (25.0, 15.0, 3.4)):
        t.ellipse(cx - r, cy - r, cx + r, cy + r, eclaircir(HERBE_VIF, 0.4) + (120,), cible=couche)
    t.poser(couche, m, flou=0.5)
    t.relief(m, 0, -3.0, 1.0, assombrir(HERBE_SOMBRE, 0.3), 140)
    t.contour(HERBE_TRAIT, 1.0)
    return t.finir()


# --------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------
def construire():
    tuiles = {}

    # -- ligne 0 : herbe & terre --
    tuiles["grass_left"] = sol("gauche", "terre", herbe=True, variante=0)
    tuiles["grass_mid"] = sol(None, "terre", herbe=True, variante=0)
    tuiles["grass_right"] = sol("droite", "terre", herbe=True, variante=0)
    tuiles["grass_single"] = sol("seul", "terre", herbe=True, variante=0)
    tuiles["grass_mid_b"] = sol(None, "terre", herbe=True, variante=1)
    tuiles["dirt_left"] = sol("gauche", "terre", variante=2)
    tuiles["dirt_mid"] = sol(None, "terre", variante=2)
    tuiles["dirt_right"] = sol("droite", "terre", variante=2)
    tuiles["dirt_bottom"] = sol(None, "terre", variante=3, bas=True)

    # -- ligne 1 : plateformes & blocs --
    tuiles["plat_left"] = plateforme("gauche")
    tuiles["plat_mid"] = plateforme(None)
    tuiles["plat_right"] = plateforme("droite")
    tuiles["blk_brick"] = bloc_brique()
    tuiles["blk_gum"] = bloc_gomme()
    tuiles["blk_ice"] = bloc_glace()
    tuiles["blk_cracked"] = bloc_fissure()
    tuiles["blk_choco"] = bloc_choco()

    # -- ligne 2 : dangers --
    tuiles["spikes_up"] = pics(False)
    tuiles["spikes_down"] = pics(True)
    tuiles["thorns"] = ronces()
    tuiles["saw"] = scie()
    tuiles["slime_top"] = gelee((SLIME_CLAIR, SLIME, SLIME_BAS, SLIME_TRAIT), True, 0)
    tuiles["slime_body"] = gelee((SLIME_CLAIR, SLIME, SLIME_BAS, SLIME_TRAIT), False, 1)
    tuiles["goo_top"] = gelee((GOO_CLAIR, GOO, GOO_BAS, GOO_TRAIT), True, 2)
    tuiles["goo_body"] = gelee((GOO_CLAIR, GOO, GOO_BAS, GOO_TRAIT), False, 3)

    # -- ligne 3 : interactifs --
    tuiles["qblock"] = qblock()
    tuiles["coin"] = piece()
    tuiles["spring"] = ressort()
    tuiles["checkpoint_top"] = checkpoint_top()
    tuiles["checkpoint_pole"] = checkpoint_pole()
    tuiles["checkpoint_base"] = checkpoint_base()
    tuiles["door"] = porte()
    tuiles["ladder"] = echelle()

    # -- ligne 4 : décors au sol --
    tuiles["grave"] = tombe()
    tuiles["bones"] = os()
    tuiles["torch"] = torche()
    tuiles["crystal"] = cristal()
    tuiles["mushroom_sm"] = champignon(False)
    tuiles["mushroom_lg"] = champignon(True)
    tuiles["flower"] = fleur()
    tuiles["grass_tuft"] = touffe()

    # -- ligne 5 : décors d'arrière-plan --
    tuiles["cloud_left"] = nuage("gauche")
    tuiles["cloud_mid"] = nuage(None)
    tuiles["cloud_right"] = nuage("droite")
    tuiles["hill"] = colline()
    tuiles["trunk"] = tronc()
    tuiles["canopy"] = feuillage()
    tuiles["star"] = etoile()
    tuiles["stepping_stones"] = galets()

    # -- lignes 6 & 8 : roche --
    tuiles["grassrock_left"] = sol("gauche", "roche", herbe=True, variante=0)
    tuiles["grassrock_mid"] = sol(None, "roche", herbe=True, variante=0)
    tuiles["grassrock_right"] = sol("droite", "roche", herbe=True, variante=0)
    tuiles["grassrock_single"] = sol("seul", "roche", herbe=True, variante=0)
    tuiles["grassrock_mid_b"] = sol(None, "roche", herbe=True, variante=1)
    tuiles["grassrock_mid_c"] = sol(None, "roche", herbe=True, variante=2)
    tuiles["rock_left"] = sol("gauche", "roche", variante=3)
    tuiles["rock_mid"] = sol(None, "roche", variante=3)
    tuiles["rock_right"] = sol("droite", "roche", variante=3)
    tuiles["rock_mid_b"] = sol(None, "roche", variante=4)
    tuiles["rock_mid_c"] = sol(None, "roche", variante=5)
    tuiles["rock_bottom"] = sol(None, "roche", variante=6, bas=True)
    tuiles["rock_bottom_b"] = sol(None, "roche", variante=7, bas=True)

    # -- ligne 7 : château (dalles + maçonnerie) --
    tuiles["path_left"] = sol("gauche", "dalle", sommet=True, variante=0)
    tuiles["path_mid"] = sol(None, "dalle", sommet=True, variante=0)
    tuiles["path_right"] = sol("droite", "dalle", sommet=True, variante=0)
    tuiles["path_single"] = sol("seul", "dalle", sommet=True, variante=0)
    tuiles["path_mid_b"] = sol(None, "dalle", sommet=True, variante=1)
    tuiles["path_mid_c"] = sol(None, "dalle", sommet=True, variante=2)
    tuiles["masonry_left"] = sol("gauche", "brique", variante=0)
    tuiles["masonry_mid"] = sol(None, "brique", variante=0)
    tuiles["masonry_right"] = sol("droite", "brique", variante=0)
    tuiles["path_slab"] = dalle_traversable()
    return tuiles


def assembler(tuiles):
    with open(TILESETS / "tileset32_map.json", encoding="utf-8") as f:
        meta = json.load(f)
    feuille = Image.new("RGBA", (meta["columns"] * T, meta["rows"] * T), (0, 0, 0, 0))
    manquantes = []
    for info in meta["tiles"]:
        im = tuiles.get(info["name"])
        if im is None:
            manquantes.append(info["name"])
            continue
        feuille.paste(im, (info["col"] * T, info["row"] * T))
    if manquantes:
        raise SystemExit("Tuiles manquantes : " + ", ".join(manquantes))
    inutiles = sorted(set(tuiles) - {i["name"] for i in meta["tiles"]})
    if inutiles:
        raise SystemExit("Tuiles hors grille : " + ", ".join(inutiles))
    return feuille


if __name__ == "__main__":
    feuille = assembler(construire())
    chemin = TILESETS / "tileset_32x32.png"
    feuille.save(chemin)
    print(f"  {chemin.relative_to(ROOT)}  {feuille.width}x{feuille.height}")
