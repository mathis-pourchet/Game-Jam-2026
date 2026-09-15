"""Game over : trop de morts, tout est réinitialisé (stats, niveau, score)."""
import math

import arcade

from entities import assets
from settings import KEYS_CONFIRM, SCREEN_HEIGHT, SCREEN_WIDTH
from views.ui import OutlinedText


class GameOverView(arcade.View):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.time = 0.0
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        deaths = game.death_manager.deaths
        self.texts = [
            OutlinedText("GAME OVER", cx, cy + 170, color=(255, 80, 100), size=84, thickness=6),
            OutlinedText("Finn est tombé en poussière...", cx, cy + 112, size=28),
            OutlinedText(f"{deaths} morts : les stats, le niveau et le score sont réinitialisés.", cx, cy + 70,
                         size=20, thickness=2, color=(220, 200, 230)),
        ]
        self.hint = OutlinedText("ENTRÉE : retenter l'aventure        ÉCHAP : menu", cx, 60, size=20, thickness=2)
        right, _ = game.player.textures["old2"]
        self.finn = right[game.player.anims["dead"][0]]
        self.grave = assets.tileset("grave")
        self.bones = assets.tileset("bones")

    def on_show_view(self):
        self.game.audio.stop_music()
        self.game.audio.play("game_over")

    def on_update(self, delta_time):
        self.time += delta_time

    def on_key_press(self, key, modifiers):
        if self.time < 0.8:
            return
        if key in KEYS_CONFIRM:
            self.game.new_run()
            self.window.show_view(self.game)
        elif key == arcade.key.ESCAPE:
            from views.menu_view import MenuView
            self.window.show_view(MenuView())

    def on_draw(self):
        self.clear((22, 10, 34))
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, cy - 150, (48, 28, 60))
        bob = math.sin(self.time * 2) * 3
        arcade.draw_texture_rect(self.grave, arcade.XYWH(cx + 150, cy - 86, 128, 128), pixelated=True)
        arcade.draw_texture_rect(self.bones, arcade.XYWH(cx - 170, cy - 130, 64, 64), pixelated=True)
        arcade.draw_texture_rect(self.finn, arcade.XYWH(cx - 20, cy - 118 + bob, 288, 192), pixelated=True)
        for i, text in enumerate(self.texts):
            text.set_alpha(255 * min(1.0, max(0.0, (self.time - i * 0.3) * 2)))
            text.draw()
        if self.time > 0.8 and int(self.time * 2) % 2 == 0:
            self.hint.draw()
