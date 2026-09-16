"""Choix du niveau : une carte par niveau décrit dans config/levels.json."""
import json
import math

import arcade

from settings import COLOR_GOLD, CONFIG, FONT_TITLE, KEYS_CONFIRM, KEYS_LEFT, KEYS_RIGHT, SCREEN_HEIGHT, SCREEN_WIDTH
from systems.score_system import ScoreSystem
from views.background import Background
from views.ui import OutlinedText, panel

CARD_W, CARD_H, GAP = 380, 300, 50


def load_levels():
    with open(CONFIG / "levels.json", encoding="utf-8") as f:
        return json.load(f)["levels"]


class LevelSelectView(arcade.View):
    def __init__(self):
        super().__init__()
        self.time = 0.0
        self.selected = 0
        self.levels = load_levels()
        self.background = Background()
        cx = SCREEN_WIDTH / 2
        self.title = OutlinedText("CHOISIS TON NIVEAU", cx, SCREEN_HEIGHT - 110, color=COLOR_GOLD, size=56,
                                  thickness=5)
        self.hint = OutlinedText("Gauche / Droite + ENTRÉE        ÉCHAP : retour", cx, 56, size=18, thickness=2)
        scores = ScoreSystem()
        self.cards = []
        total = len(self.levels) * CARD_W + (len(self.levels) - 1) * GAP
        left = cx - total / 2
        bottom = SCREEN_HEIGHT / 2 - CARD_H / 2 - 30
        for i, level in enumerate(self.levels):
            x = left + i * (CARD_W + GAP)
            mid = x + CARD_W / 2
            best = scores.load_best(level["id"])
            record = f"Record : {best['score']} pts" if best else "Jamais terminé"
            self.cards.append({
                "level": level,
                "rect": (x, x + CARD_W, bottom, bottom + CARD_H),
                "number": OutlinedText(str(level["id"]), mid, bottom + CARD_H - 92, size=72, color=COLOR_GOLD),
                "name": OutlinedText(level["name"], mid, bottom + 132, size=28),
                "hint": arcade.Text(level.get("hint", ""), mid, bottom + 106, (235, 235, 245), 15,
                                    width=CARD_W - 50, multiline=True, align="center", anchor_x="center",
                                    anchor_y="top", font_name=FONT_TITLE),
                "record": OutlinedText(record, mid, bottom + 26, size=16, thickness=2, color=(200, 205, 225)),
            })

    def on_show_view(self):
        self.window.audio.play_music("music_menu")

    def on_update(self, delta_time):
        self.time += delta_time

    def start(self):
        self.window.audio.play("select")
        from views.game_view import GameView
        self.window.show_view(GameView(level_index=self.selected))

    def back(self):
        from views.menu_view import MenuView
        self.window.show_view(MenuView())

    def on_key_press(self, key, modifiers):
        if key == arcade.key.M:
            self.window.audio.toggle_mute()
        elif key in KEYS_LEFT:
            self.selected = (self.selected - 1) % len(self.cards)
            self.window.audio.play("menu_move")
        elif key in KEYS_RIGHT:
            self.selected = (self.selected + 1) % len(self.cards)
            self.window.audio.play("menu_move")
        elif key in KEYS_CONFIRM:
            self.start()
        elif key in (arcade.key.ESCAPE, arcade.key.BACKSPACE):
            self.back()

    def _card_at(self, x, y):
        for i, card in enumerate(self.cards):
            l, r, b, t = card["rect"]
            if l <= x <= r and b <= y <= t:
                return i
        return None

    def on_mouse_motion(self, x, y, dx, dy):
        index = self._card_at(x, y)
        if index is not None:
            self.selected = index

    def on_mouse_press(self, x, y, button, modifiers):
        index = self._card_at(x, y)
        if index is not None:
            self.selected = index
            self.start()

    def on_draw(self):
        self.clear()
        self.background.draw(self.time * 50, SCREEN_HEIGHT / 2, self.time)
        self.title.draw()
        for i, card in enumerate(self.cards):
            l, r, b, t = card["rect"]
            chosen = i == self.selected
            lift = 12 + math.sin(self.time * 5) * 4 if chosen else 0
            panel(l, r, b + lift, t + lift, fill=(34, 24, 56, 245) if chosen else (26, 18, 40, 225),
                  border=COLOR_GOLD if chosen else (255, 255, 255, 50), width=4 if chosen else 2)
            for key in ("number", "name", "record"):
                text = card[key]
                x, y = text.main.x, text.main.y
                text.set_position(x, y + lift)
                text.draw()
                text.set_position(x, y)
            hint = card["hint"]
            hint.y += lift
            hint.draw()
            hint.y -= lift
        self.hint.draw()
