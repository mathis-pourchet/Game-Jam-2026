"""Bulle du chien : une ligne par action, avec les touches dessinées comme sur un clavier.

Une ligne de config/levels.json ressemble à :
    {"keys": [["Q", "D"], ["LEFT", "RIGHT"]], "action": "Bouger"}
Les groupes de touches sont séparés par « / ». LEFT, RIGHT, UP et DOWN sont dessinées
en flèches : la police du jeu n'a pas ces caractères.

Le fond et les touches partent en un appel de dessin (DrawBatch), les textes en un autre.
"""
import arcade
import pyglet

from settings import COLOR_OUTLINE, FONT_TITLE
from views.batch import DrawBatch

ARROWS = {"LEFT", "RIGHT", "UP", "DOWN"}
WHITE = (255, 255, 255)
KEY_H = 40          # hauteur d'une touche
KEY_PAD = 13        # marge du texte dans une touche
GAP = 8             # entre deux touches
ROW_GAP = 12        # entre deux lignes
MARGIN = 20         # bord de la bulle
ACTION_GAP = 28     # entre les touches et le nom de l'action


class TipBubble:
    def __init__(self, rows):
        self.shapes = DrawBatch()
        self.texts = pyglet.graphics.Batch()
        self.rows = []
        for row in rows:
            items = []      # (genre, valeur, largeur) ; genre : "key", "arrow" ou "sep"
            for g, group in enumerate(row["keys"]):
                if g:
                    sep = arcade.Text("/", 0, 0, (150, 140, 170), 22, font_name=FONT_TITLE, anchor_y="center",
                                      batch=self.texts)
                    items.append(("sep", sep, sep.content_width))
                for key in group:
                    if key in ARROWS:
                        items.append(("arrow", key, KEY_H))
                    else:
                        label = arcade.Text(key, 0, 0, COLOR_OUTLINE, 18, font_name=FONT_TITLE,
                                            anchor_x="center", anchor_y="center", batch=self.texts)
                        items.append(("key", label, max(KEY_H, label.content_width + 2 * KEY_PAD)))
            keys_w = sum(w for _, _, w in items) + GAP * (len(items) - 1)
            action = arcade.Text(row["action"].upper(), 0, 0, COLOR_OUTLINE, 26, font_name=FONT_TITLE,
                                 anchor_y="center", batch=self.texts)
            self.rows.append((items, keys_w, action))
        self.keys_col = max(keys_w for _, keys_w, _ in self.rows)
        action_w = max(action.content_width for _, _, action in self.rows)
        self.width = 2 * MARGIN + self.keys_col + ACTION_GAP + action_w
        self.height = 2 * MARGIN + len(self.rows) * KEY_H + (len(self.rows) - 1) * ROW_GAP

    def draw(self, left, bottom, tail_x):
        w, h = self.width, self.height
        b = self.shapes
        b.begin()
        b.rect(left, left + w, bottom, bottom + h, WHITE)
        b.outline(left, left + w, bottom, bottom + h, COLOR_OUTLINE, 4)
        arrows = []
        y = bottom + h - MARGIN - KEY_H / 2
        for items, _, action in self.rows:
            x = left + MARGIN
            for kind, value, width in items:
                if kind == "sep":
                    self._place(value, x, y)
                else:
                    self._keycap(b, x, y, width)
                    if kind == "key":
                        self._place(value, x + width / 2, y + 3)
                    else:
                        arrows.append((x + width / 2, y + 3, value))
                x += width + GAP
            self._place(action, left + MARGIN + self.keys_col + ACTION_GAP, y)
            y -= KEY_H + ROW_GAP
        # queue de la bulle : un triangle sombre dessous, le corps, puis un triangle blanc qui efface le bord
        arcade.draw_triangle_filled(tail_x - 18, bottom + 4, tail_x + 18, bottom + 4, tail_x, bottom - 24,
                                    COLOR_OUTLINE)
        b.draw()
        arcade.draw_triangle_filled(tail_x - 13, bottom + 3, tail_x + 13, bottom + 3, tail_x, bottom - 18, WHITE)
        for cx, cy, direction in arrows:
            self._arrow(cx, cy, direction)
        self.texts.draw()

    @staticmethod
    def _place(text, x, y):
        if text.x != x or text.y != y:
            text.x, text.y = x, y

    @staticmethod
    def _keycap(b, x, y, width):
        bottom, top = y - KEY_H / 2, y + KEY_H / 2
        b.rect(x, x + width, bottom, top, (190, 182, 210))          # flanc de la touche
        b.rect(x, x + width, bottom + 6, top, (250, 248, 255))      # dessus
        b.outline(x, x + width, bottom, top, COLOR_OUTLINE, 2)

    @staticmethod
    def _arrow(cx, cy, direction):
        s = 9
        points = {
            "RIGHT": (cx + s, cy, cx - s * 0.7, cy + s, cx - s * 0.7, cy - s),
            "LEFT": (cx - s, cy, cx + s * 0.7, cy + s, cx + s * 0.7, cy - s),
            "UP": (cx, cy + s, cx - s, cy - s * 0.7, cx + s, cy - s * 0.7),
            "DOWN": (cx, cy - s, cx - s, cy + s * 0.7, cx + s, cy + s * 0.7),
        }[direction]
        arcade.draw_triangle_filled(*points, COLOR_OUTLINE)
