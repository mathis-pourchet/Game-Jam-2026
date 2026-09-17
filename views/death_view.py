"""Après la mort : le nouvel âge de Finn et une petite pique tirée au hasard.

Une mort normale reste dans le noir. Une mort spéciale reste sobre elle aussi, mais dans une
pénombre chaude : un halo doré qui respire derrière le texte, quelques braises qui montent et
un texte couleur or pâle (voir views/death_fx.py), puis elle mène au choix du pouvoir.
"""
import math
import random

import arcade

from settings import KEYS_CONFIRM, SCREEN_HEIGHT, SCREEN_WIDTH
from views import screen
from views.death_fx import EMBER, GOLD, draw_glow
from views.ui import OutlinedText

AUTO_CONTINUE = 2.8     # s avant de continuer tout seul (le temps de lire la pique)
SKIP_AFTER = 0.5        # s avant qu'une touche puisse passer l'écran
PALE_GOLD = (240, 212, 140)
MOTES = 18              # braises dorées de la mort spéciale
TAUNT_DELAY = 0.35      # s avant que la pique apparaisse, sous l'âge

TAUNTS = (
    "La vieillesse, c'est pas une stratégie.",
    "Tu comptes finir avant la retraite ?",
    "Jake aurait déjà fini. En dormant.",
    "Courageux. Pas doué, mais courageux.",
    "Les zombies commencent à te reconnaître.",
    "C'était voulu, bien sûr.",
)
_last_taunt = None


def pick_taunt():
    """Une pique au hasard, jamais deux fois la même d'affilée."""
    global _last_taunt
    _last_taunt = random.choice([t for t in TAUNTS if t != _last_taunt])
    return _last_taunt


def draw_motes(t, w, h, alpha):
    """Petites braises qui montent lentement ; positions tirées de l'indice, sans état."""
    for i in range(MOTES):
        x = (i * 0.618 % 1) * w + math.sin(t * 1.3 + i) * 12
        speed = 35 + (i * 37 % 40)
        y = (i * 0.391 % 1) * h + t * speed
        y %= h + 20
        fade = min(1.0, y / 120, (h - y) / 160) if 0 < y < h else 0.0
        size = 4 if i % 3 else 6
        a = alpha * fade * (0.55 + 0.45 * math.sin(t * 3 + i * 2.1))
        if a > 1:
            arcade.draw_lrbt_rectangle_filled(x, x + size, y, y + size, (*GOLD, int(a)))


class DeathCardView(arcade.View):
    def __init__(self, game, outcome):
        super().__init__()
        self.game = game
        self.outcome = outcome
        self.special = outcome.offer_upgrade
        self.time = 0.0
        self.camera = screen.make_camera()
        color = PALE_GOLD if self.special else (215, 215, 225)
        self.text = OutlinedText(f"{game.progression.age_years} ans", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10,
                                 color=color, size=130, thickness=8)
        self.taunt = OutlinedText(pick_taunt(), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 110,
                                  color=(205, 180, 125) if self.special else (160, 160, 175), size=30, thickness=3)

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
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, EMBER)
            glow = min(1.0, self.time / 0.5)
            pulse = 0.85 + 0.15 * math.sin(self.time * 2.4)
            draw_glow(w / 2, h / 2 - 5, 760 * pulse, GOLD, 95 * glow)
            draw_motes(self.time, w, h, 170 * glow)
        appear = min(1.0, self.time / 0.25)
        self.text.set_position(w / 2, h / 2 - 10 + (1 - appear) ** 2 * 60)    # l'âge tombe en place
        self.text.set_alpha(255 * appear)
        self.text.draw()
        self.taunt.set_alpha(255 * min(1.0, max(0.0, (self.time - TAUNT_DELAY) / 0.3)))
        self.taunt.draw()
