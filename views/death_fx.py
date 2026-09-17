"""Transitions de mort. Deux ambiances opposées, pour que le joueur comprenne tout de
suite quelle mort lui donne des pouvoirs :

- mort normale : les couleurs s'éteignent, flash rouge, puis un iris se referme sur Finn
  dans le noir ;
- mort spéciale (renaissance plus fort) : ralenti, la scène s'assombrit pendant que Finn
  brille dans un halo doré (éclair, rayons courts, petites ondes, étincelles qui montent),
  puis l'iris se referme sur Finn dans une pénombre chaude (celle de l'écran de mort).
"""
import math

import arcade
from PIL import Image

from settings import SCREEN_HEIGHT, SCREEN_WIDTH

DURATION = 2.0
GOLD = (255, 205, 70)
PALE = (255, 240, 200)
ROSE = (255, 150, 120)
EMBER = (26, 19, 12)    # fond sombre et chaud de la mort spéciale (le noir de la mort normale, réchauffé)
HOLE = 0.2          # rayon du trou de l'iris, en fraction de la taille de sa texture

_iris = None
_glow = None


def iris_texture():
    """Carré blanc opaque percé d'un disque transparent au bord adouci."""
    global _iris
    if _iris is None:
        # Dégradé radial de Pillow (256x256) : valeur = distance au centre x 1,414 (255 dans les coins).
        inner, outer = (HOLE - 0.02) * 256 * 1.4142, (HOLE + 0.02) * 256 * 1.4142
        alpha = Image.radial_gradient("L").point(
            lambda v: int(255 * min(1.0, max(0.0, (v - inner) / (outer - inner)))))
        img = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
        img.putalpha(alpha)
        _iris = arcade.Texture(img, hash="iris_mort")
    return _iris


def glow_texture():
    """Halo blanc : opaque au centre, qui s'efface doucement vers le bord (coins transparents)."""
    global _glow
    if _glow is None:
        alpha = Image.radial_gradient("L").point(lambda v: int(255 * max(0.0, 1 - v / 181) ** 2))
        img = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
        img.putalpha(alpha)
        _glow = arcade.Texture(img, hash="halo_mort")
    return _glow


def draw_glow(cx, cy, size, color, alpha):
    """Halo coloré de diamètre `size` centré sur (cx, cy)."""
    half = size / 2
    arcade.draw_texture_rect(glow_texture(), arcade.LRBT(cx - half, cx + half, cy - half, cy + half),
                             color=arcade.types.Color(*color), alpha=int(alpha))


def draw_iris(sx, sy, radius, color):
    """Tout est recouvert de `color`, sauf un disque de rayon `radius` autour de (sx, sy)."""
    w, h = SCREEN_WIDTH, SCREEN_HEIGHT
    if radius <= 1:
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, color)
        return
    half = radius / HOLE / 2
    l, r, b, t = sx - half, sx + half, sy - half, sy + half
    arcade.draw_texture_rect(iris_texture(), arcade.LRBT(l, r, b, t), color=arcade.types.Color(*color))
    # bandes autour du carré ; tant que l'iris est grand, le carré déborde de l'écran et elles n'existent pas
    for sl, sr, sb, st in ((-10, l + 1, -10, h + 10), (r - 1, w + 10, -10, h + 10),
                           (l, r, -10, b + 1), (l, r, t - 1, h + 10)):
        if sl < sr and sb < st:
            arcade.draw_lrbt_rectangle_filled(sl, sr, sb, st, color)


def draw_rays(sx, sy, angle, alpha, count=16, length=1500, width=0.07):
    """Rayons de lumière dorés qui partent de (sx, sy) ; `width` = demi-angle d'un rayon."""
    color = (*GOLD, int(alpha))
    for i in range(count):
        a = angle + i * math.tau / count
        arcade.draw_triangle_filled(sx, sy,
                                    sx + math.cos(a - width) * length, sy + math.sin(a - width) * length,
                                    sx + math.cos(a + width) * length, sy + math.sin(a + width) * length, color)


class DeathTransition:
    def __init__(self, special):
        self.special = special
        self.time = 0.0

    @property
    def done(self):
        return self.time >= DURATION

    def update(self, dt):
        self.time += dt

    def time_scale(self):
        """Ralenti sur le corps au début d'une mort spéciale."""
        return 0.25 if self.special and self.time < 0.7 else 1.0

    def draw(self, sx, sy, now):
        """(sx, sy) : Finn dans l'image logique ; `now` fait tourner les rayons."""
        if self.special:
            self._draw_special(sx, sy, now)
        else:
            self._draw_normal(sx, sy)

    def _draw_normal(self, sx, sy):
        t, w, h = self.time, SCREEN_WIDTH, SCREEN_HEIGHT
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (40, 40, 48, int(150 * min(1.0, t / 1.2))))
        if t < 0.25:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (200, 30, 40, int(140 * (1 - t / 0.25))))
        k = min(1.0, max(0.0, (t - 0.55) / 1.25))
        draw_iris(sx, sy, 900 * (1 - k) ** 2, (0, 0, 0))

    def _draw_special(self, sx, sy, now):
        """Tout se passe autour de Finn : la scène s'assombrit, lui reste dans un halo doré."""
        t, w, h = self.time, SCREEN_WIDTH, SCREEN_HEIGHT
        glow = min(1.0, t / 0.4)
        arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (*EMBER, int(120 * min(1.0, t / 0.8))))
        pulse = 1 + 0.08 * math.sin(now * 5)
        draw_glow(sx, sy, 330 * pulse * glow, GOLD, 120 * glow)
        draw_glow(sx, sy, 150 * pulse, ROSE, 70 * glow)
        draw_rays(sx, sy, now * 0.9, 45 * glow, count=12, length=30 + 90 * glow, width=0.05)
        for start in (0.0, 0.35):                           # deux petites ondes dorées
            age = t - start
            if 0 <= age < 0.7:
                arcade.draw_circle_outline(sx, sy, 20 + age * 260, (*PALE, int(200 * (1 - age / 0.7))), 3)
        if t < 0.3:                                         # éclair bref, sur Finn seulement
            draw_glow(sx, sy, 220, (255, 255, 255), 230 * (1 - t / 0.3))
        k = min(1.0, max(0.0, (t - 0.9) / 1.0))
        if k > 0:
            draw_iris(sx, sy, 900 * (1 - k) ** 2, EMBER)
