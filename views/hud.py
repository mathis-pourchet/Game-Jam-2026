"""Interface en jeu : barre de vie, stats, morts/âge, pièces, chrono, barre du boss, messages."""
import arcade

from entities import assets
from settings import COLOR_GOLD, COLOR_OUTLINE, FONT_PIXEL, FONT_TITLE, SCREEN_HEIGHT, SCREEN_WIDTH
from systems.progression_system import STAT_ORDER
from views.ui import OutlinedText, health_bar, panel

PHASES = {0: ("Jeune héros", (140, 230, 255)), 1: ("Vieillissant", (255, 190, 120)), 2: ("Très vieux", (255, 130, 110))}


class Hud:
    def __init__(self, game):
        self.game = game
        self.heart = assets.texture("heart_full.png")
        self.hp_trail = 0.0
        self.last_time = 0.0
        self.skull = assets.texture("skull.png")
        self.hourglass = assets.texture("hourglass.png")
        self.coin = assets.tileset("coin")
        self.icons = {s: assets.texture(f"icon_{s}.png") for s in STAT_ORDER}
        top = SCREEN_HEIGHT
        self.t_hp = OutlinedText("", 0, top - 37, size=15, thickness=2, anchor_y="center")
        self.t_deaths =OutlinedText("", SCREEN_WIDTH / 2 - 60, top - 44, size=22, anchor_x="left")
        self.t_age = OutlinedText("", SCREEN_WIDTH / 2 - 60, top - 80, size=18, anchor_x="left")
        self.t_phase = OutlinedText("", SCREEN_WIDTH / 2, top - 106, size=13, thickness=2)
        self.t_coins = OutlinedText("", SCREEN_WIDTH - 118, top - 44, size=22, anchor_x="left", color=COLOR_GOLD)
        self.t_time = OutlinedText("", SCREEN_WIDTH - 24, top - 80, size=18, anchor_x="right")
        self.t_boss = OutlinedText("", SCREEN_WIDTH / 2, 62, size=20, color=(255, 170, 210))
        self.t_toast = OutlinedText("", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 190, size=34, thickness=4)
        self.t_sub = OutlinedText("", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 228, size=18, thickness=2)
        self.t_mute = arcade.Text("M : son", SCREEN_WIDTH - 20, 14, (255, 255, 255, 150), 8,
                                  anchor_x="right", font_name=FONT_PIXEL)

    def draw(self):
        g = self.game
        prog = g.progression
        player = g.player
        top = SCREEN_HEIGHT

        # --- barre de vie et stats (haut gauche) ---
        max_hp = prog.max_hp
        hp = max(0, min(player.hp, max_hp))
        dt = max(0.0, g.time - self.last_time)
        self.last_time = g.time
        if hp >= self.hp_trail:
            self.hp_trail = hp     # soin : pas de traînée
        else:
            self.hp_trail = max(hp, min(max_hp, self.hp_trail) - max_hp * 0.6 * dt)
        bar_left, bar_w = 58, 150 + (max_hp - 100) * 0.8   # la barre s'allonge avec la Résistance
        panel(12, max(bar_left + bar_w + 12, 194), top - 124, top - 12)
        arcade.draw_texture_rect(self.heart, arcade.LBWH(22, top - 50, 30, 27), pixelated=True)
        low = hp / max_hp <= 0.25 and not player.dead and int(g.time * 4) % 2 == 0
        health_bar(bar_left, top - 50, bar_w, 26, hp, max_hp, trail=self.hp_trail,
                   border=(255, 90, 90) if low else COLOR_OUTLINE, border_width=3 if low else 2)
        self.t_hp.text = f"{hp} / {max_hp}"
        self.t_hp.set_position(bar_left + bar_w / 2, top - 37)
        self.t_hp.draw()
        for i, stat in enumerate(STAT_ORDER):
            x = 22 + i * 40
            arcade.draw_texture_rect(self.icons[stat], arcade.LBWH(x, top - 94, 28, 28), pixelated=True)
            info = prog.describe(stat)
            for k in range(info["max"]):
                color = info["color"] if k < info["level"] else (70, 60, 90)
                arcade.draw_lrbt_rectangle_filled(x + k * 7, x + k * 7 + 5, top - 108, top - 102, color)

        # --- morts et âge (haut centre) ---
        deaths, max_deaths = g.death_manager.deaths, g.death_manager.max_deaths
        panel(SCREEN_WIDTH / 2 - 115, SCREEN_WIDTH / 2 + 115, top - 100, top - 12)
        arcade.draw_texture_rect(self.skull, arcade.LBWH(SCREEN_WIDTH / 2 - 105, top - 50, 30, 27), pixelated=True)
        arcade.draw_texture_rect(self.hourglass, arcade.LBWH(SCREEN_WIDTH / 2 - 101, top - 86, 21, 27), pixelated=True)
        danger = deaths >= max_deaths - 2
        self.t_deaths.text = f"Morts {deaths} / {max_deaths}"
        self.t_deaths.set_color((255, 110, 110) if danger else (255, 255, 255))
        self.t_age.text = f"Âge : {prog.age_years} ans"
        label, color = PHASES[prog.aging_stage]
        if prog.aging_stage == 0 and prog.power > 0:
            _, color = (f"Muscles niveau {prog.muscle_level}", COLOR_GOLD)
        # self.t_phase.text = _
        self.t_phase.set_color(color)
        self.t_deaths.draw()
        self.t_age.draw()
        self.t_phase.draw()

        # --- pièces et chrono (haut droite) ---
        panel(SCREEN_WIDTH - 170, SCREEN_WIDTH - 12, top - 96, top - 12)
        arcade.draw_texture_rect(self.coin, arcade.LBWH(SCREEN_WIDTH - 160, top - 52, 32, 32), pixelated=True)
        self.t_coins.text = f"x {g.score.coins}"
        minutes, seconds = divmod(int(g.score.elapsed), 60)
        self.t_time.text = f"{minutes:02d}:{seconds:02d}"
        self.t_coins.draw()
        self.t_time.draw()

        # --- boss ---
        boss = g.boss
        if boss and boss.active and not boss.dead:
            w = 520
            left = SCREEN_WIDTH / 2 - w / 2
            panel(left - 10, left + w + 10, 18, 92, fill=(30, 10, 30, 220))
            arcade.draw_lrbt_rectangle_filled(left, left + w, 26, 46, (60, 20, 50))
            ratio = max(0.0, boss.hp / boss.max_hp)
            arcade.draw_lrbt_rectangle_filled(left, left + w * ratio, 26, 46,
                                              (255, 70, 140) if boss.phase == 1 else (255, 50, 60))
            arcade.draw_lrbt_rectangle_outline(left, left + w, 26, 46, (255, 255, 255), 2)
            self.t_boss.text = g.cfg["boss"]["name"] + ("  -  ENRAGÉ !" if boss.enraged else "")
            self.t_boss.draw()

        # --- messages ---
        if g.toast_time > 0:
            alpha = 255 * min(1.0, g.toast_time / 0.5)
            self.t_toast.text = g.toast_title
            self.t_sub.text = g.toast_sub
            self.t_toast.set_alpha(alpha)
            self.t_sub.set_alpha(alpha)
            self.t_toast.draw()
            if g.toast_sub:
                self.t_sub.draw()
        self.t_mute.draw()
