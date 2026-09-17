"""Effets visuels volontairement « too much » sur Finn : on doit VOIR ses pouvoirs et sa vieillesse.

Rien ne touche aux sprites. Les pouvoirs se lisent par la taille (ProgressionSystem.visual_scale),
un halo, des étincelles aux couleurs des stats acquises, des images rémanentes quand il court vite,
une onde verte à chaque saut et une gerbe de feu à chaque coup d'épée. La vieillesse se lit par la
teinte grise et le dos voûté (Player.update_sprite), la poussière qui tombe de lui et la sueur
quand il court.
"""
import math
import random

import arcade

from entities import assets

STAT_COLORS = {"jump": (110, 230, 120), "speed": (255, 214, 60), "force": (255, 110, 60),
               "resistance": (255, 120, 190)}
GHOSTS = 6
DUST = (175, 170, 165)


class PlayerFx:
    def __init__(self, game):
        self.game = game
        self.aura = arcade.Sprite(assets.texture("glow.png"))
        self.aura_list = arcade.SpriteList()
        self.aura_list.append(self.aura)
        self.ghosts = arcade.SpriteList()
        for _ in range(GHOSTS):
            ghost = arcade.Sprite(game.player.sprite.texture)
            ghost.alpha = 0
            self.ghosts.append(ghost)
        self.ghost_timer = 0.0
        self.ghost_next = 0
        self.dust_timer = 0.0

    @property
    def prog(self):
        return self.game.progression

    @property
    def body(self):
        return self.game.player.body

    # ------------------------------------------------------------------
    # Réactions aux actions de Finn
    # ------------------------------------------------------------------
    def on_jump(self):
        prog, b, effects = self.prog, self.body, self.game.effects
        if prog.is_aging:                         # les vieux genoux soulèvent la poussière
            effects.emit(b.center_x, b.y + 4, DUST, 8, speed=(30, 90), angle=(20, 160), gravity=300,
                         life=(0.3, 0.6), size=(2, 4))
            return
        level = prog.levels["jump"]
        if not level:
            return
        color = STAT_COLORS["jump"]
        for low, high in ((-15, 15), (165, 195)):   # onde qui file des deux côtés des pieds
            effects.emit(b.center_x, b.y + 3, color, 6 + 5 * level, speed=(140, 200 + 70 * level),
                         angle=(low, high), gravity=0, life=(0.2, 0.45), glow=True, size=(2.5, 4))
        effects.emit(b.center_x, b.y, color, 4 + 4 * level, speed=(80, 180), angle=(250, 290), gravity=-200,
                     life=(0.2, 0.4), glow=True, size=(2, 3))

    def on_attack(self):
        prog = self.prog
        level = prog.levels["force"]
        if not level or prog.is_aging:
            return
        b, effects = self.body, self.game.effects
        facing = self.game.player.facing
        x = b.center_x + facing * (b.w / 2 + 20 + 6 * level)
        angle = (-40, 40) if facing > 0 else (140, 220)
        effects.emit(x, b.center_y + 8, STAT_COLORS["force"], 8 + 7 * level, speed=(160, 260 + 90 * level),
                     angle=angle, gravity=250, life=(0.15, 0.35), glow=True, size=(2.5, 3.5 + level))
        effects.emit(x, b.center_y + 8, (255, 230, 150), 4 + 3 * level, speed=(60, 160), angle=angle, gravity=0,
                     life=(0.1, 0.25), glow=True, size=(3, 5))
        effects.shake(1.5 + 1.2 * level, 0.09)

    def on_hurt(self):
        prog, b, effects = self.prog, self.body, self.game.effects
        level = prog.levels["resistance"]
        if prog.is_aging:                         # un vieil homme, ça part en poussière
            effects.emit(b.center_x, b.center_y, DUST, 14, speed=(40, 140), gravity=200, life=(0.4, 0.8),
                         size=(2, 4))
        elif level:                               # le bouclier encaisse : éclats roses
            effects.emit(b.center_x, b.center_y, STAT_COLORS["resistance"], 10 + 8 * level,
                         speed=(120, 220 + 40 * level), gravity=0, life=(0.25, 0.5), glow=True, size=(2.5, 4.5))

    # ------------------------------------------------------------------
    # Chaque image
    # ------------------------------------------------------------------
    def update(self, dt):
        game, prog, b = self.game, self.prog, self.body
        playing = game.state == "play" and not game.player.dead
        scale = prog.visual_scale[1]
        strength = prog.aura_strength
        pulse = 1 + math.sin(game.time * 7) * 0.1
        self.aura.center_x = b.center_x
        self.aura.center_y = b.y + 28 * scale
        self.aura.scale = (1.8 + 2.4 * strength) * scale * pulse
        self.aura.color = (255, 200, 70) if prog.power < 4 else (255, 120, 40)
        self.aura.alpha = int(235 * strength) if playing else 0
        owned = [stat for stat, level in prog.levels.items() if level > 0]
        if playing and owned and not prog.is_aging and random.random() < 0.3 + 0.7 * strength:
            game.effects.emit(b.x + random.uniform(-10, b.w + 10), b.y + random.uniform(0, 56 * scale),
                              STAT_COLORS[random.choice(owned)], 1 + prog.power // 4, speed=(40, 120),
                              angle=(70, 110), gravity=-90, life=(0.4, 0.9), glow=True, size=(2, 3.5))
        self._update_ghosts(dt, playing)
        if playing and prog.is_aging:
            self._update_old(dt)

    def _update_ghosts(self, dt, playing):
        prog, player = self.prog, self.game.player
        for ghost in self.ghosts:
            ghost.alpha = max(0, ghost.alpha - int(700 * dt))
        level = prog.levels["speed"]
        if not (playing and level and not prog.is_aging and abs(player.body.vx) > 150):
            return
        self.ghost_timer -= dt
        if self.ghost_timer > 0:
            return
        self.ghost_timer = 0.055 - 0.007 * level
        ghost = self.ghosts[self.ghost_next]
        self.ghost_next = (self.ghost_next + 1) % GHOSTS
        sprite = player.sprite
        ghost.texture = sprite.texture
        ghost.scale = sprite.scale
        ghost.position = sprite.position
        ghost.color = STAT_COLORS["speed"]
        ghost.alpha = 80 + 30 * level

    def _update_old(self, dt):
        prog, b = self.prog, self.body
        self.dust_timer -= dt
        if self.dust_timer > 0:
            return
        stage = prog.aging_stage
        running = b.on_ground and abs(b.vx) > 60
        self.dust_timer = random.uniform(0.15, 0.35) if running else random.uniform(0.35, 0.7)
        effects = self.game.effects
        effects.emit(b.x + random.uniform(0, b.w), b.y + random.uniform(8, 48), DUST, 2 * stage, speed=(10, 40),
                     angle=(240, 300), gravity=150, life=(0.5, 1.0), size=(2, 3.5))
        if running:                               # essoufflé : des gouttes de sueur
            head = b.y + 60 * prog.visual_scale[1]
            effects.emit(b.center_x - self.game.player.facing * 10, head, (140, 200, 255), stage + 1,
                         speed=(70, 140), angle=(70, 110), gravity=800, life=(0.3, 0.5), size=(2, 3))

    def draw_aura(self, blend):
        self.aura_list.draw(blend_function=blend)

    def draw_ghosts(self):
        self.ghosts.draw(pixelated=True)
