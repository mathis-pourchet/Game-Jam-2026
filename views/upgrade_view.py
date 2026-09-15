"""Écran « Renaissance » : le joueur choisit la stat que la mort améliore."""
import math

import arcade

from entities import assets
from settings import COLOR_GOLD, COLOR_OUTLINE, KEYS_CONFIRM, KEYS_LEFT, KEYS_RIGHT, SCREEN_HEIGHT, SCREEN_WIDTH
from views.ui import OutlinedText, panel

CARD_W, CARD_H, GAP = 270, 330, 40


class UpgradeView(arcade.View):
    def __init__(self, game, outcome):
        super().__init__()
        self.game = game
        self.outcome = outcome
        self.time = 0.0
        prog = game.progression
        self.choices = prog.rebirth_choices()
        self.selected = 0
        self.glow = assets.texture("glow.png")
        self.title = OutlinedText("RENAISSANCE", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 120, color=COLOR_GOLD, size=64,
                                  thickness=5)
        self.sub = OutlinedText("La mort te rend plus fort... Choisis ton don :", SCREEN_WIDTH / 2,
                                SCREEN_HEIGHT - 168, size=24)
        self.hint = OutlinedText("Flèches pour choisir, ENTRÉE pour valider  (ou 1, 2, 3 / clic)",
                                 SCREEN_WIDTH / 2, 50, size=17, thickness=2)
        self.cards = []
        total = len(self.choices) * CARD_W + (len(self.choices) - 1) * GAP
        left = SCREEN_WIDTH / 2 - total / 2
        for i, stat in enumerate(self.choices):
            info = prog.describe(stat)
            x = left + i * (CARD_W + GAP)
            cx = x + CARD_W / 2
            bottom = SCREEN_HEIGHT / 2 - CARD_H / 2 - 40
            self.cards.append({
                "stat": stat, "info": info, "rect": (x, x + CARD_W, bottom, bottom + CARD_H),
                "icon": assets.texture(f"icon_{stat}.png"),
                "name": OutlinedText(info["label"], cx, bottom + 150, color=info["color"], size=30),
                "effect": arcade.Text(info["effect"], cx, bottom + 118, (240, 240, 250), 14, width=CARD_W - 30,
                                      multiline=True, align="center", anchor_x="center", anchor_y="top",
                                      font_name="Luckiest Guy"),
                "level": OutlinedText(f"Niv. {info['level']}  >  {info['level'] + 1}", cx, bottom + 22, size=18,
                                      thickness=2),
                "key": OutlinedText(str(i + 1), x + 22, bottom + CARD_H - 38, size=20, thickness=2),
            })

    def on_show_view(self):
        self.game.audio.play("rebirth")

    def on_update(self, delta_time):
        self.time += delta_time

    def choose(self, index):
        if self.time < 0.4 or not self.choices:
            return
        stat = self.choices[index]
        prog = self.game.progression
        muscles_before = prog.muscle_level
        prog.upgrade(stat)
        self.game.audio.play("select")
        self.game.respawn(self.outcome)
        info = prog.describe(stat)
        sub = info["effect"]
        if prog.muscle_level > muscles_before and not prog.is_aging:
            sub = f"Finn se muscle : niveau {prog.muscle_level} !"
        self.game.show_toast(f"+1 {info['label']} !", sub, 2.6)
        self.window.show_view(self.game)

    def on_key_press(self, key, modifiers):
        if key in KEYS_LEFT:
            self.selected = (self.selected - 1) % len(self.choices)
            self.game.audio.play("menu_move")
        elif key in KEYS_RIGHT:
            self.selected = (self.selected + 1) % len(self.choices)
            self.game.audio.play("menu_move")
        elif key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3, arcade.key.NUM_1, arcade.key.NUM_2,
                     arcade.key.NUM_3):
            index = {arcade.key.KEY_1: 0, arcade.key.KEY_2: 1, arcade.key.KEY_3: 2,
                     arcade.key.NUM_1: 0, arcade.key.NUM_2: 1, arcade.key.NUM_3: 2}[key]
            if index < len(self.choices):
                self.choose(index)
        elif key in KEYS_CONFIRM:
            self.choose(self.selected)

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
            self.choose(index)

    def on_draw(self):
        self.game.on_draw()
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (40, 16, 60, 215))
        self.title.draw()
        self.sub.draw()
        for i, card in enumerate(self.cards):
            l, r, b, t = card["rect"]
            chosen = i == self.selected
            lift = 14 + math.sin(self.time * 5) * 4 if chosen else 0
            color = card["info"]["color"]
            if chosen:
                size = CARD_W * 1.9
                arcade.draw_texture_rect(self.glow, arcade.XYWH((l + r) / 2, (b + t) / 2 + lift, size, size * 1.2),
                                         color=arcade.types.Color(*color[:3]), alpha=120)
            panel(l, r, b + lift, t + lift, fill=(34, 24, 56, 245) if chosen else (26, 18, 40, 235),
                  border=color if chosen else (255, 255, 255, 50), width=4 if chosen else 2)
            arcade.draw_texture_rect(card["icon"], arcade.XYWH((l + r) / 2, t - 90 + lift, 96, 96), pixelated=True)
            self._draw_lifted(card, lift)
            for k in range(card["info"]["max"]):
                c = color if k <= card["info"]["level"] else (70, 60, 90)
                if k == card["info"]["level"]:
                    c = (255, 255, 255) if int(self.time * 4) % 2 else color
                px = (l + r) / 2 - card["info"]["max"] * 14 / 2 + k * 14
                arcade.draw_lrbt_rectangle_filled(px, px + 10, b + 52 + lift, b + 62 + lift, c)
                arcade.draw_lrbt_rectangle_outline(px, px + 10, b + 52 + lift, b + 62 + lift, COLOR_OUTLINE, 1)
        self.hint.draw()

    @staticmethod
    def _draw_lifted(card, lift):
        for key in ("name", "level", "key"):
            text = card[key]
            x, y = text.main.x, text.main.y
            text.set_position(x, y + lift)
            text.draw()
            text.set_position(x, y)
        effect = card["effect"]
        effect.y += lift
        effect.draw()
        effect.y -= lift
