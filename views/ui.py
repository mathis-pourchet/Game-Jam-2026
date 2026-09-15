"""Petits outils d'interface : texte avec contour, panneaux."""
import arcade

from settings import COLOR_OUTLINE, FONT_TITLE


class OutlinedText:
    """Texte « cartoon » avec un contour sombre (4 copies décalées + le texte)."""

    def __init__(self, text, x, y, color=(255, 255, 255), size=24, anchor_x="center", anchor_y="baseline",
                 font=FONT_TITLE, outline=COLOR_OUTLINE, thickness=3, width=None, multiline=False, align="left"):
        kw = dict(font_size=size, anchor_x=anchor_x, anchor_y=anchor_y, font_name=font,
                  width=width, multiline=multiline, align=align)
        self.offsets = [(-thickness, -thickness), (thickness, -thickness), (-thickness, thickness),
                        (thickness, thickness), (0, -thickness - 1)]
        self.outline = outline
        self.shadows = [arcade.Text(text, x + dx, y + dy, outline, **kw) for dx, dy in self.offsets]
        self.main = arcade.Text(text, x, y, color, **kw)
        self._text = text
        self._color = color

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
        self.main.x, self.main.y = x, y
        for (dx, dy), s in zip(self.offsets, self.shadows):
            s.x, s.y = x + dx, y + dy

    @property
    def content_width(self):
        return self.main.content_width

    def draw(self):
        for s in self.shadows:
            s.draw()
        self.main.draw()


def panel(left, right, bottom, top, fill=(30, 22, 48, 210), border=(255, 255, 255, 60), width=2):
    arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, fill)
    if border:
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, border, width)
