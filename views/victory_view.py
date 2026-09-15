"""Victoire : score détaillé, rang (moins de morts = meilleur rang) et record."""
import math
import random

import arcade

from entities import assets
from settings import COLOR_GOLD, KEYS_CONFIRM, SCREEN_HEIGHT, SCREEN_WIDTH
from systems.score_system import ScoreSystem
from views.background import Background
from views.ui import OutlinedText, panel

RANK_COLORS = {"S": (255, 214, 60), "A": (120, 230, 140), "B": (130, 200, 255), "C": (230, 170, 255)}


class VictoryView(arcade.View):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.time = 0.0
        self.background = Background()
        deaths = game.death_manager.deaths
        score = game.score
        self.total = score.final_score(deaths)
        self.letter, self.rank_title = ScoreSystem.rank(deaths)
        self.record = score.save_if_best(game.cfg["id"], self.total, deaths)
        cx = SCREEN_WIDTH / 2
        self.title = OutlinedText("VICTOIRE !", cx, SCREEN_HEIGHT - 110, color=COLOR_GOLD, size=78, thickness=6)
        self.sub = OutlinedText("Le Roi des Glaces est vaincu. Ooo est sauvé !", cx, SCREEN_HEIGHT - 158, size=24)
        minutes, seconds = divmod(int(score.elapsed), 60)
        stats = [
            ("Morts", f"{deaths} / {game.death_manager.max_deaths}"),
            ("Âge final de Finn", f"{game.progression.age_years} ans"),
            ("Temps", f"{minutes:02d}:{seconds:02d}"),
            ("Pièces", str(score.coins)),
            ("Ennemis vaincus", str(score.kills)),
        ]
        self.rows = []
        y = SCREEN_HEIGHT - 226
        for label, value in stats + [("", "")] + list(score.breakdown(deaths).items()):
            if label:
                if isinstance(value, int):
                    value = f"{value:+d}" if label != "Base" else str(value)
                self.rows.append((OutlinedText(label, cx - 330, y, size=19, anchor_x="left", thickness=2),
                                  OutlinedText(value, cx + 10, y, size=19, anchor_x="right", thickness=2)))
            y -= 28
        self.t_score = OutlinedText(f"SCORE : {self.total}", cx - 160, 150, size=36, color=COLOR_GOLD)
        self.t_record = OutlinedText("NOUVEAU RECORD !", cx - 160, 112, size=20, color=(255, 140, 190))
        self.t_rank = OutlinedText(self.letter, cx + 250, 225, size=150, thickness=7,
                                   color=RANK_COLORS.get(self.letter, (255, 255, 255)))
        self.t_rank_title = OutlinedText(self.rank_title, cx + 250, 180, size=24)
        self.hint = OutlinedText("ENTRÉE : menu        R : rejouer", cx, 40, size=18, thickness=2)
        variant = game.progression.visual_variant
        right, _ = game.player.textures[variant]
        anims = game.player.variant_anims[variant]
        self.finn_frames = [right[i] for i in anims["jump"] + anims["idle"]]
        self.jake_frames = assets.frames("jake.png", 30, 26, 4)[1]
        self.confetti = [[random.uniform(0, SCREEN_WIDTH), random.uniform(SCREEN_HEIGHT, SCREEN_HEIGHT * 2),
                          random.uniform(60, 160), random.choice([(255, 120, 190), (255, 214, 60), (120, 230, 140),
                                                                  (130, 200, 255)]), random.uniform(0, 6)]
                         for _ in range(90)]

    def on_show_view(self):
        self.game.audio.stop_music()

    def on_update(self, delta_time):
        self.time += delta_time
        if self.time > 4.0 and self.game.audio.current_music is None:
            self.game.audio.play_music("music_menu")
        for c in self.confetti:
            c[1] -= c[2] * delta_time
            c[4] += delta_time * 4
            if c[1] < -10:
                c[1] = SCREEN_HEIGHT + 10
                c[0] = random.uniform(0, SCREEN_WIDTH)

    def on_key_press(self, key, modifiers):
        if self.time < 1.0:
            return
        if key in KEYS_CONFIRM:
            from views.menu_view import MenuView
            self.window.show_view(MenuView())
        elif key == arcade.key.R:
            self.game.new_run()
            self.window.show_view(self.game)

    def on_draw(self):
        self.clear()
        self.background.draw(self.time * 60, SCREEN_HEIGHT / 2, self.time)
        panel(SCREEN_WIDTH / 2 - 360, SCREEN_WIDTH / 2 + 40, 90, SCREEN_HEIGHT - 196, fill=(30, 22, 48, 200))
        self.title.draw()
        self.sub.draw()
        for i, (label, value) in enumerate(self.rows):
            if self.time > 0.3 + i * 0.12:
                label.draw()
                value.draw()
        if self.time > 1.6:
            self.t_score.draw()
            if self.record:
                self.t_record.draw()
        if self.time > 2.2:
            self.t_rank.draw()
            self.t_rank_title.draw()
        hop = abs(math.sin(self.time * 4)) * 26
        finn = self.finn_frames[0 if hop > 8 else 2]
        arcade.draw_texture_rect(finn, arcade.XYWH(SCREEN_WIDTH / 2 + 200, 480 + hop, 192, 128), pixelated=True)
        jake = self.jake_frames[2 + int(self.time * 5) % 2]
        arcade.draw_texture_rect(jake, arcade.XYWH(SCREEN_WIDTH / 2 + 330, 452, 90, 78), pixelated=True)
        for x, y, _, color, rot in self.confetti:
            arcade.draw_lrbt_rectangle_filled(x, x + 6 * abs(math.cos(rot)) + 1, y, y + 10, color)
        self.hint.draw()
