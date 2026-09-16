"""Interface en jeu : barre de vie, stats, âge, pièces, chrono et barre du boss.

Volontairement muette : aucun message ni texte narratif pendant le jeu. Seules
restent les jauges, les icônes et l'âge de Finn.

Tout le HUD part en deux appels de dessin : les formes et icônes (DrawBatch), puis les
textes (un batch pyglet). Dessinés un par un, c'était une soixantaine d'appels par image.
"""
import pyglet

from entities import assets
from settings import COLOR_GOLD, COLOR_OUTLINE, SCREEN_HEIGHT, SCREEN_WIDTH
from systems.progression_system import STAT_ORDER
from views.batch import DrawBatch
from views.ui import OutlinedText, health_bar, panel


class Hud:
    def __init__(self, game):
        self.game = game
        self.heart = assets.texture("heart_full.png")
        self.hp_trail = 0.0
        self.last_time = 0.0
        self.hourglass = assets.texture("hourglass.png")
        self.coin = assets.tileset("coin")
        self.icons = {s: assets.texture(f"icon_{s}.png") for s in STAT_ORDER}
        self.shapes = DrawBatch()
        self.texts = pyglet.graphics.Batch()
        top = SCREEN_HEIGHT
        self.t_hp = OutlinedText("", 0, top - 37, size=15, thickness=2, anchor_y="center", batch=self.texts)
        self.t_age = OutlinedText("", SCREEN_WIDTH / 2 - 50, top - 46, size=22, anchor_x="left", batch=self.texts)
        self.t_coins = OutlinedText("", SCREEN_WIDTH - 118, top - 44, size=22, anchor_x="left", color=COLOR_GOLD,
                                    batch=self.texts)
        self.t_time = OutlinedText("", SCREEN_WIDTH - 24, top - 80, size=18, anchor_x="right", batch=self.texts)

    def draw(self):
        g = self.game
        prog = g.progression
        player = g.player
        top = SCREEN_HEIGHT
        b = self.shapes
        b.begin()

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
        panel(12, max(bar_left + bar_w + 12, 194), top - 124, top - 12, batch=b)
        b.texture(self.heart, 22, top - 50, 30, 27)
        low = hp / max_hp <= 0.25 and not player.dead and int(g.time * 4) % 2 == 0
        health_bar(bar_left, top - 50, bar_w, 26, hp, max_hp, trail=self.hp_trail,
                   border=(255, 90, 90) if low else COLOR_OUTLINE, border_width=3 if low else 2, batch=b)
        self.t_hp.text = f"{hp} / {max_hp}"
        self.t_hp.set_position(bar_left + bar_w / 2, top - 37)
        for i, stat in enumerate(STAT_ORDER):
            x = 22 + i * 40
            b.texture(self.icons[stat], x, top - 94, 28, 28)
            info = prog.describe(stat)
            for k in range(info["max"]):
                color = info["color"] if k < info["level"] else (70, 60, 90)
                b.rect(x + k * 7, x + k * 7 + 5, top - 108, top - 102, color)

        # --- âge de Finn (haut centre) : le nombre de morts reste caché ---
        panel(SCREEN_WIDTH / 2 - 85, SCREEN_WIDTH / 2 + 85, top - 62, top - 12, batch=b)
        b.texture(self.hourglass, SCREEN_WIDTH / 2 - 78, top - 51, 21, 27)
        self.t_age.text = f"{prog.age_years} ans"
        self.t_age.set_color((255, 190, 120) if prog.is_aging else (255, 255, 255))

        # --- pièces et chrono (haut droite) ---
        panel(SCREEN_WIDTH - 170, SCREEN_WIDTH - 12, top - 96, top - 12, batch=b)
        b.texture(self.coin, SCREEN_WIDTH - 160, top - 52, 32, 32)
        self.t_coins.text = f"x {g.score.coins}"
        minutes, seconds = divmod(int(g.score.elapsed), 60)
        self.t_time.text = f"{minutes:02d}:{seconds:02d}"

        # --- boss : jauge seule, sans nom ni annonce ---
        boss = g.boss
        if boss and boss.active and not boss.dead:
            w = 520
            left = SCREEN_WIDTH / 2 - w / 2
            panel(left - 10, left + w + 10, 18, 60, fill=(30, 10, 30, 220), batch=b)
            b.rect(left, left + w, 26, 46, (60, 20, 50))
            ratio = max(0.0, boss.hp / boss.max_hp)
            b.rect(left, left + w * ratio, 26, 46, (255, 70, 140) if boss.phase == 1 else (255, 50, 60))
            b.outline(left, left + w, 26, 46, (255, 255, 255), 2)

        b.draw()
        self.texts.draw()
