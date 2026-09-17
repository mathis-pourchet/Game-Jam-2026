"""Petits outils d'interface : texte avec contour, panneaux, barres de vie.

Pour dessiner vite (voir views/batch.py), `panel` et `health_bar` acceptent un `batch`,
et OutlinedText peut rejoindre un pyglet.graphics.Batch.
"""
import arcade
import pyglet

from settings import COLOR_OUTLINE, FONT_TITLE

# Dans un batch pyglet, l'ordre n'est garanti qu'entre groupes : le contour, puis le texte.
SHADOW_GROUP = pyglet.graphics.Group(order=0)
MAIN_GROUP = pyglet.graphics.Group(order=1)


class OutlinedText:
    """Texte « cartoon » avec un contour sombre (4 copies décalées + une ombre + le texte).

    Avec `batch`, le texte est dessiné par batch.draw() et draw() ne fait rien.
    """

    def __init__(self, text, x, y, color=(255, 255, 255), size=24, anchor_x="center", anchor_y="baseline",
                 font=FONT_TITLE, outline=COLOR_OUTLINE, thickness=3, width=None, multiline=False, align="left",
                 batch=None):
        kw = dict(font_size=size, anchor_x=anchor_x, anchor_y=anchor_y, font_name=font,
                  width=width, multiline=multiline, align=align, batch=batch)
        self.offsets = [(-thickness, -thickness), (thickness, -thickness), (-thickness, thickness),
                        (thickness, thickness), (0, -thickness - 1)]
        self.outline = outline
        self.batch = batch
        shadow_group, main_group = (SHADOW_GROUP, MAIN_GROUP) if batch else (None, None)
        self.shadows = [arcade.Text(text, x + dx, y + dy, outline, group=shadow_group, **kw)
                        for dx, dy in self.offsets]
        self.main = arcade.Text(text, x, y, color, group=main_group, **kw)
        self._text = text
        self._color = color
        self._pos = (x, y)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        if value != self._text:
            self._text = value
            for t in self.shadows + [self.main]:
                t.text = value

    def set_color(self, color):
        if color != self._color:
            self._color = color
            self.main.color = color

    def set_alpha(self, alpha):
        alpha = max(0, min(255, int(alpha)))
        self.main.color = tuple(self._color[:3]) + (alpha,)
        for s in self.shadows:
            s.color = tuple(self.outline[:3]) + (alpha,)

    def set_position(self, x, y):
        if (x, y) == self._pos:
            return
        self._pos = (x, y)
        self.main.x, self.main.y = x, y
        for (dx, dy), s in zip(self.offsets, self.shadows):
            s.x, s.y = x + dx, y + dy

    @property
    def content_width(self):
        return self.main.content_width

    def draw(self):
        if self.batch is not None:
            return
        for s in self.shadows:
            s.draw()
        self.main.draw()


def health_color(ratio):
    """Vert quand la vie est pleine, jaune à mi-vie, rouge quand elle est presque vide."""
    if ratio > 0.5:
        return (110, 230, 120)
    if ratio > 0.25:
        return (255, 200, 60)
    return (255, 70, 70)


def _rect(batch, left, right, bottom, top, color):
    if batch is None:
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)
    else:
        batch.rect(left, right, bottom, top, color)


def _outline(batch, left, right, bottom, top, color, width):
    if batch is None:
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, color, width)
    else:
        batch.outline(left, right, bottom, top, color, width)


def health_bar(left, bottom, width, height, hp, max_hp, trail=None, border=COLOR_OUTLINE, border_width=2, batch=None):
    """Barre de vie : fond sombre, traînée claire (dégâts récents), remplissage coloré, contour."""
    ratio = max(0.0, min(1.0, hp / max_hp))
    _rect(batch, left, left + width, bottom, bottom + height, (55, 30, 55))
    if trail is not None:
        trail_ratio = max(0.0, min(1.0, trail / max_hp))
        if trail_ratio > ratio:
            _rect(batch, left + width * ratio, left + width * trail_ratio, bottom, bottom + height, (255, 235, 190))
    if ratio > 0:
        _rect(batch, left, left + width * ratio, bottom, bottom + height, health_color(ratio))
        _rect(batch, left, left + width * ratio, bottom + height * 0.62, bottom + height, (255, 255, 255, 55))
    _outline(batch, left, left + width, bottom, bottom + height, border, border_width)


def panel(left, right, bottom, top, fill=(30, 22, 48, 210), border=(255, 255, 255, 60), width=2, batch=None):
    _rect(batch, left, right, bottom, top, fill)
    if border:
        _outline(batch, left, right, bottom, top, border, width)
