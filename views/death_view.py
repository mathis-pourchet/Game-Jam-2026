"""Après la mort, un seul message : « + 6 ans ».

Une mort normale reste dans le noir ; une mort spéciale reste dans la lumière dorée de sa
transition (voir views/death_fx.py), puis mène au choix du pouvoir.
"""
import arcade

from settings import COLOR_GOLD, KEYS_CONFIRM, SCREEN_HEIGHT, SCREEN_WIDTH
from views import screen
from views.death_fx import LIGHT, draw_rays
from views.ui import OutlinedText

AUTO_CONTINUE = 1.9     # s avant de continuer tout seul
SKIP_AFTER = 0.5        # s avant qu'une touche puisse passer l'écran


class DeathCardView(arcade.View):
    def __init__(self, game, outcome):
        super().__init__()
        self.game = game
        self.outcome = outcome
        self.special = outcome.offer_upgrade
        self.time = 0.0
        self.camera = screen.make_camera()
        years = game.progression.age_cfg["years_per_death"]
        color = COLOR_GOLD if self.special else (215, 215, 225)
        self.text = OutlinedText(f"+ {years} ans", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 40, color=color, size=130,
                                 thickness=8)

    def on_show_view(self):
        screen.set_mouse(self.window, False)
        if self.outcome.aging_stage > 0 and not self.outcome.game_over:
            self.game.audio.play("aging")

    def on_update(self, delta_time):
        self.time += delta_time
        if self.time > AUTO_CONTINUE:
            self.proceed()

    def on_key_press(self, key, modifiers):
        if self.time > SKIP_AFTER and key in KEYS_CONFIRM | {arcade.key.J, arcade.key.X}:
            self.proceed()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.time > SKIP_AFTER:
            self.proceed()

    def proceed(self):
        if self.window.current_view is not self:
            return
        if self.outcome.game_over:
            from views.game_over_view import GameOverView
            self.window.show_view(GameOverView(self.game))
        elif self.outcome.offer_upgrade:
            from views.upgrade_view import UpgradeView
            self.window.show_view(UpgradeView(self.game, self.outcome))
        else:
            self.game.respawn(self.outcome)
            self.window.show_view(self.game)

    def on_draw(self):
        screen.begin_frame(self, self.camera)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        if self.special:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, LIGHT)
            draw_rays(w / 2, h / 2, self.time * 0.6, 120)
        appear = min(1.0, self.time / 0.25)
        self.text.set_position(w / 2, h / 2 - 40 + (1 - appear) ** 2 * 60)    # le texte tombe en place
        self.text.set_alpha(255 * appear)
        self.text.draw()
