"""Écran « Tu es mort ! » : compteur, âge, vieillissement, puis renaissance."""
import arcade

from settings import COLOR_GOLD, KEYS_CONFIRM, SCREEN_HEIGHT, SCREEN_WIDTH
from systems.death_manager import DeathCause, Respawn
from views.ui import OutlinedText

CAUSES = {
    DeathCause.NORMAL: "Terrassé par un zombie ou un piège...",
    DeathCause.CHAMPION: "Vaincu par un sorcier squelette (CHAMPION) !",
    DeathCause.BOSS: "Gelé par le Roi des Glaces !",
}


class DeathCardView(arcade.View):
    def __init__(self, game, outcome):
        super().__init__()
        self.game = game
        self.outcome = outcome
        self.time = 0.0
        prog = game.progression
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        self.lines = [
            OutlinedText("TU ES MORT !", cx, cy + 150, color=(255, 90, 110), size=72, thickness=5),
            OutlinedText(CAUSES.get(outcome.cause, ""), cx, cy + 92, size=24),
            OutlinedText(f"Morts : {outcome.deaths} / {outcome.max_deaths}", cx, cy + 30, size=34),
            OutlinedText(f"Finn a maintenant {prog.age_years} ans", cx, cy - 16, size=24, color=(200, 220, 255)),
        ]
        if outcome.game_over:
            info, color = "Trop de morts... toutes tes forces sont perdues !", (255, 90, 90)
        elif outcome.stat_lost:
            label = prog.stats_cfg[outcome.stat_lost]["label"]
            info, color = f"Le temps passe... tu perds 1 niveau de {label} !", (255, 170, 110)
        elif outcome.aging_stage > 0:
            info, color = "Finn vieillit... ses forces l'abandonnent.", (255, 170, 110)
        elif outcome.offer_upgrade:
            info, color = "Mais la mort te rend PLUS FORT...", COLOR_GOLD
        elif outcome.respawn == Respawn.BOSS_GATE:
            info, color = "Tu reviens devant l'arène du Roi des Glaces.", (255, 255, 255)
        else:
            info, color = "Retour au tout début de la map !", (255, 255, 255)
        self.lines.append(OutlinedText(info, cx, cy - 76, size=26, color=color))
        left = outcome.max_deaths - outcome.deaths
        if not outcome.game_over:
            warn = "DERNIÈRE CHANCE !" if left == 1 else f"Encore {left} morts avant de tout perdre"
            if outcome.became_older and outcome.aging_stage == 1:
                warn = "Finn devient VIEUX : chaque mort lui coûtera une stat"
            self.lines.append(OutlinedText(warn, cx, cy - 120, size=18, thickness=2,
                                           color=(255, 120, 120) if left <= 2 else (230, 230, 240)))
        self.hint = OutlinedText("Appuie sur ENTRÉE", cx, 70, size=18, thickness=2)

    def on_show_view(self):
        if self.outcome.aging_stage > 0 and not self.outcome.game_over:
            self.game.audio.play("aging")

    def on_update(self, delta_time):
        self.time += delta_time
        if self.time > 5.0:
            self.proceed()

    def on_key_press(self, key, modifiers):
        if self.time > 0.7 and key in KEYS_CONFIRM | {arcade.key.J, arcade.key.X}:
            self.proceed()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.time > 0.7:
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
        self.game.on_draw()
        alpha = min(200, int(self.time * 500))
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (25, 0, 20, alpha))
        for i, line in enumerate(self.lines):
            appear = min(1.0, max(0.0, (self.time - i * 0.15) * 4))
            if appear > 0:
                line.set_alpha(255 * appear)
                line.draw()
        if self.time > 0.7 and int(self.time * 2) % 2 == 0:
            self.hint.draw()
