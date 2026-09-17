"""Dessin groupé : des dizaines de petits rectangles et d'icônes en UN seul appel à la carte graphique.

Chaque arcade.draw_lrbt_rectangle_filled / draw_texture_rect est un appel de dessin séparé : le
HUD à lui seul en faisait une quarantaine par image. Ici chaque forme est un sprite réutilisé d'une
SpriteList : l'ordre d'ajout est l'ordre d'affichage, et tout part d'un coup avec draw(). Chaque
emplacement retient son dernier état, et un sprite n'est modifié que si sa forme a changé.

À réserver aux petites formes plutôt fixes (HUD, bulle du chien). Mesuré en boucle réelle : pour le
décor (de très grands quadrilatères) et les barres de vie des monstres (qui bougent sans cesse), les
appels directs restent plus rapides.

À chaque image :
    batch.begin()
    batch.rect(left, right, bottom, top, color)
    batch.texture(texture, left, bottom, width, height)
    batch.draw()
"""
import arcade
from PIL import Image

_white = None


def white_texture():
    global _white
    if _white is None:
        _white = arcade.Texture(Image.new("RGBA", (4, 4), (255, 255, 255, 255)), hash="blanc_4x4")
    return _white


def rgba(color):
    """Couleur à 4 composantes : sur un sprite réutilisé, une couleur à 3 composantes
    garderait l'opacité de son usage précédent."""
    return tuple(color) if len(color) == 4 else (color[0], color[1], color[2], 255)


class DrawBatch:
    def __init__(self, pixelated=True):
        self.sprites = arcade.SpriteList()
        self.textures = []      # texture de chaque emplacement
        self.shapes = []        # (cx, cy, largeur, hauteur, couleur) de chaque emplacement
        self.shown = []         # l'emplacement est-il visible ?
        self.used = 0
        self.pixelated = pixelated

    def begin(self):
        self.used = 0

    def _put(self, texture, cx, cy, width, height, color):
        i = self.used
        self.used += 1
        shape = (cx, cy, width, height, color)
        if i == len(self.sprites):
            sprite = arcade.Sprite(texture)
            sprite.position = (cx, cy)
            sprite.size = (width, height)
            sprite.color = color
            self.sprites.append(sprite)
            self.textures.append(texture)
            self.shapes.append(shape)
            self.shown.append(True)
            return
        sprite = self.sprites[i]
        if not self.shown[i]:
            sprite.visible = True
            self.shown[i] = True
        if self.textures[i] is not texture:
            sprite.texture = texture
            self.textures[i] = texture
        old = self.shapes[i]
        if old == shape:
            return
        if old[0] != cx or old[1] != cy:
            sprite.position = (cx, cy)
        if old[2] != width or old[3] != height:
            sprite.size = (width, height)
        if old[4] != color:
            sprite.color = color
        self.shapes[i] = shape

    def rect(self, left, right, bottom, top, color):
        if right <= left or top <= bottom:
            return
        self._put(white_texture(), (left + right) / 2, (bottom + top) / 2, right - left, top - bottom, rgba(color))

    def outline(self, left, right, bottom, top, color, width=1):
        h = width / 2
        self.rect(left - h, right + h, bottom - h, bottom + h, color)
        self.rect(left - h, right + h, top - h, top + h, color)
        self.rect(left - h, left + h, bottom + h, top - h, color)
        self.rect(right - h, right + h, bottom + h, top - h, color)

    def texture(self, texture, left, bottom, width, height, color=(255, 255, 255, 255)):
        self._put(texture, left + width / 2, bottom + height / 2, width, height, rgba(color))

    def draw(self):
        for i in range(self.used, len(self.sprites)):      # emplacements non utilisés cette image
            if self.shown[i]:
                self.sprites[i].visible = False
                self.shown[i] = False
        self.sprites.draw(pixelated=self.pixelated)
