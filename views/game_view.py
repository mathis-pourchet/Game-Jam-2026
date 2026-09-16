"""Vue principale : le niveau, Finn, les zombies, le boss et la boucle mort / renaissance."""
import json
import math
import random
from collections import deque

import arcade

from entities import assets
from entities.enemy import Boss, ButlerBoss, Champion, Enemy, FireKing, Jumper, Shockwave
from entities.player import InputState, Player
from entities.trap import Coin, Door, HeartPickup, Npc, Saw, Spring
from settings import (COLOR_GOLD, CONFIG, FIXED_DT, HEART_HEAL, KEYS_ATTACK, KEYS_DOWN, KEYS_JUMP, KEYS_LEFT,
                      KEYS_PAUSE, KEYS_RIGHT, KEYS_UP, RESPAWN_BACK_TILES, ROOT, SCREEN_HEIGHT, SCREEN_WIDTH,
                      SPECIAL_DEATH_WINDOW, SPRING_VELOCITY, STOMP_BOUNCE, TILE)
from systems.death_manager import DeathCause, DeathManager, Respawn
from systems.effects import Effects
from systems.level_manager import HAZARD_BOXES, HAZARD_DAMAGE, LevelSprites, load_level, tile_sprite
from systems.physics import BREAKABLE, EMPTY, GATE, QBLOCK, USED, rects_overlap, tile_range
from systems.progression_system import ProgressionSystem
from systems.score_system import ScoreSystem
from views import screen
from views.background import Background
from views.death_fx import DeathTransition, iris_texture
from views.hud import Hud
from views.player_fx import PlayerFx
from views.tip_bubble import TipBubble
from views.ui import OutlinedText, health_bar

ENEMY_CLASSES = {"zombie": Enemy, "jumper": Jumper, "champion": Champion, "king": FireKing}
# Le boss d'un niveau est choisi par "boss"."kind" dans config/levels.json
BOSS_CLASSES = {"ice_king": Boss, "butler": ButlerBoss}


def load_level_config(index=0):
    with open(CONFIG / "levels.json", encoding="utf-8") as f:
        return json.load(f)["levels"][index]


class GameView(arcade.View):
    def __init__(self, level_index=0, start_col=None):
        super().__init__()
        self.cfg = load_level_config(level_index)
        self.audio = self.window.audio
        self.progression = ProgressionSystem()
        self.score = ScoreSystem()
        self.death_manager = DeathManager(self.progression, self.cfg["max_deaths"])
        self.level = load_level(ROOT / self.cfg["map"])
        self.tiles = LevelSprites(self.level)
        self.start = self.level.spawn("player")
        if start_col is not None:   # option de test : démarrer plus loin dans la map
            self.start.tx = start_col
        self.boss_respawn = self.level.spawn("boss_respawn") or self.start
        grid = self.level.grid
        self.ceiling = [any(grid.blocking(tx, grid.height - 1 - r) for r in range(3)) for tx in range(grid.width)]

        self.player = Player(self.progression)
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player.sprite)
        self.input = InputState()
        self.keys = set()
        self.camera = screen.make_camera()
        self.gui_camera = screen.make_camera()
        self.cam_x, self.cam_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        self.effects = Effects(self.window.ctx)
        self.player_fx = PlayerFx(self)
        self.background = Background()
        self.hud = Hud(self)
        self.graves = arcade.SpriteList()
        self.tip_bubbles = {}
        self.play_time = 0.0          # temps de jeu réel (hors pause) pour dater les coups reçus
        self.special_hit = None       # (cause, play_time) du dernier coup d'un champion ou du boss
        self.transition = None
        self.death_outcome = None
        self.pause_title = OutlinedText("PAUSE", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 60, size=60, thickness=4)
        self.pause_help = OutlinedText("Échap : reprendre     R : recommencer     Q : menu",
                                       SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 20, size=20, thickness=2)
        self.time = 0.0
        self.state = "play"
        self.state_time = 0.0
        self.killer = None
        self.gate_closed = False
        self.new_run()
        # Préparé pendant le chargement plutôt qu'en plein jeu : la texture de la 1re mort,
        # et une 1re image (shaders, envoi des textures et des lettres au GPU : ~50 ms).
        iris_texture()
        self.on_draw()

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def new_run(self):
        """Nouvelle partie : stats, morts, score et map remis à zéro."""
        self.progression.reset()
        self.score.reset()
        self.death_manager.reset()
        self.graves.clear()
        self.effects.clear()
        self.special_hit = None
        self.transition = None
        self.reset_map()
        self.place_player(self.start.x, self.start.bottom)
        self.state = "play"
        self.audio.play_music(self.cfg["music"])

    def on_show_view(self):
        screen.set_mouse(self.window, self.state == "paused")

    def reset_map(self):
        lvl = self.level
        self.tiles.reset_dynamic(lvl)
        self.set_gate(False)
        self.enemies = []
        self.enemy_sprites = arcade.SpriteList()
        self.enemy_glows = arcade.SpriteList()
        self.boss = None
        for s in lvl.spawns:
            if s.kind in ENEMY_CLASSES:
                self.add_enemy(ENEMY_CLASSES[s.kind](s.x, s.bottom))
            elif s.kind == "boss":
                boss_class = BOSS_CLASSES[self.cfg["boss"].get("kind", "ice_king")]
                self.boss = boss_class(s.x, s.bottom, self.cfg["boss"]["hp"])
                self.add_enemy(self.boss)
        self.saws = [Saw(s.x, s.bottom + TILE / 2, vertical=s.kind == "saw_v")
                     for s in lvl.spawns if s.kind in ("saw_h", "saw_v")]
        self.springs = [Spring(s.x, s.bottom) for s in lvl.spawns_of("spring")]
        self.coins = [Coin(s.x, s.bottom + TILE / 2) for s in lvl.spawns_of("coin")]
        self.hearts = [HeartPickup(s.x, s.bottom + TILE / 2) for s in lvl.spawns_of("heart")]
        self.npcs = [Npc(s.kind, s.x, s.bottom, s.data) for s in lvl.spawns if s.kind in ("jake", "sign")]
        door = lvl.spawn("door")
        self.door = Door(door.x, door.bottom) if door else None
        self.objects = arcade.SpriteList()
        for group in (self.npcs, self.springs, self.saws, self.coins, self.hearts):
            for obj in group:
                self.objects.append(obj.sprite)
        if self.door:
            self.objects.append(self.door.sprite)
        self.projectiles = []
        self.projectile_sprites = arcade.SpriteList()
        self.boss_defeated = False
        self.safe_positions = deque(maxlen=80)
        self.safe_timer = 0.0

    def add_enemy(self, enemy, summoned=False):
        enemy.summoned = summoned
        enemy.glow = None
        self.enemies.append(enemy)
        self.enemy_sprites.append(enemy.sprite)
        if isinstance(enemy, (Champion, Boss)):
            enemy.glow = arcade.Sprite(assets.texture("glow.png"))
            enemy.glow.color = (90, 255, 160) if isinstance(enemy, Champion) else (130, 200, 255)
            self.enemy_glows.append(enemy.glow)

    def remove_enemy(self, enemy):
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        enemy.sprite.remove_from_sprite_lists()
        if enemy.glow:
            enemy.glow.remove_from_sprite_lists()

    def add_projectile(self, projectile):
        self.projectiles.append(projectile)
        self.projectile_sprites.append(projectile.sprite)

    def place_player(self, x, bottom):
        self.player.reset(x, bottom)
        self.last_ground = (x, bottom)
        self.update_camera(0, snap=True)

    def set_gate(self, closed):
        self.gate_closed = closed
        for cell in self.level.gate_cells:
            self.level.grid.set(*cell, GATE if closed else EMPTY)
        self.tiles.gate.visible = closed

    def in_boss_zone(self):
        gx = self.level.gate_x
        return gx is not None and not self.boss_defeated and self.player.body.center_x > gx

    # ------------------------------------------------------------------
    # Entrées
    # ------------------------------------------------------------------
    def near_ladder(self):
        b = self.player.body
        tx = math.floor(b.center_x / TILE)
        cells = {(tx, math.floor((b.y + 2) / TILE)), (tx, math.floor(b.center_y / TILE)),
                 (tx, math.floor((b.y - 4) / TILE))}
        return self.player.on_ladder or bool(cells & self.level.ladders)

    def sync_input(self):
        k, inp = self.keys, self.input
        inp.left = bool(k & KEYS_LEFT)
        inp.right = bool(k & KEYS_RIGHT)
        inp.up = bool(k & KEYS_UP)
        inp.down = bool(k & KEYS_DOWN)
        inp.jump_held = bool(k & KEYS_JUMP)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.M:
            self.audio.toggle_mute()
            return
        if self.state == "paused":
            if key in KEYS_PAUSE:
                self.state = "play"
            elif key == arcade.key.R:
                self.new_run()
            elif key in (arcade.key.Q, arcade.key.BACKSPACE):
                from views.menu_view import MenuView
                self.window.show_view(MenuView())
            return
        if key in KEYS_PAUSE and self.state == "play":
            self.state = "paused"
            self.keys.clear()
            self.sync_input()
            return
        self.keys.add(key)
        if key in KEYS_JUMP and not (key in KEYS_UP and self.near_ladder()):
            self.input.jump_pressed = True
        if key in KEYS_ATTACK:
            self.input.attack_pressed = True
        self.sync_input()

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)
        self.sync_input()

    # ------------------------------------------------------------------
    # Boucle de jeu
    # ------------------------------------------------------------------
    def on_update(self, delta_time):
        dt = min(delta_time, 0.05)
        self.time += dt
        screen.set_mouse(self.window, self.state == "paused")    # curseur visible seulement en pause
        if self.state == "paused":
            return
        # Le même nombre de pas de physique à chaque image (2 à 60 images/s). L'ancien accumulateur
        # ajoutait un 3e pas à ~8 % des images, car le minuteur du système est toujours un peu en
        # retard : Finn et le décor « sautaient » plusieurs fois par seconde. La taille du pas suit le
        # temps réel écoulé, la vitesse du jeu reste donc exacte.
        steps = max(1, min(6, round(dt / FIXED_DT)))
        for _ in range(steps):
            self.step(dt / steps)
        for coin in self.coins:
            coin.update(self.time)
        for heart in self.hearts:
            heart.update(self.time)
        self.update_glows()
        self.player_fx.update(dt)
        self.effects.update(dt)
        self.update_camera(dt)

    def step(self, dt):
        if self.state == "play":
            self.step_play(dt)
        elif self.state == "dying":
            self.step_dying(dt)
        elif self.state == "victory":
            self.step_victory(dt)

    def step_play(self, dt):
        p, lvl = self.player, self.level
        b = p.body
        self.play_time += dt
        self.score.tick(dt)
        for ev in p.update(dt, self.input, lvl):
            self.on_player_event(ev)
        self.input.consume()
        for saw in self.saws:
            saw.update(dt)
        for spring in self.springs:
            spring.update(dt)
        for npc in self.npcs:
            npc.update(dt, b.center_x, b.y)
        events = []
        for e in self.enemies:
            if e is self.boss or abs(e.body.center_x - b.center_x) < 1500:
                e.update(dt, lvl, p, events)
        for pr in self.projectiles:
            pr.update(dt, lvl, events)
        if not p.dead:
            self.collide(events)
        self.handle_events(events)
        self.cleanup()
        self.boss_logic()
        if self.boss and self.boss.dead and not self.boss.removed and random.random() < dt * 10:
            bb = self.boss.body
            self.effects.burst(random.uniform(bb.x, bb.right), random.uniform(bb.y, bb.top),
                               random.choice([(200, 240, 255), (130, 200, 255), (255, 255, 255)]), 16)
            self.audio.play("hit", 0.6, min_interval=0.1)
        if p.dead:
            self.start_dying()
            return
        if b.on_ground:
            self.last_ground = (b.center_x, b.y)
            self.safe_timer += dt
            if self.safe_timer > 0.3 and not self.hazard_near():
                self.safe_timer = 0.0
                last = self.safe_positions[-1] if self.safe_positions else None
                if last is None or abs(last[0] - b.center_x) >= TILE or abs(last[1] - b.y) >= TILE:
                    self.safe_positions.append((b.center_x, b.y))

    # ------------------------------------------------------------------
    def on_player_event(self, ev):
        kind = ev[0]
        b = self.player.body
        if kind == "jump":
            self.audio.play("jump", 0.5)
            self.player_fx.on_jump()
        elif kind == "attack":
            self.audio.play("sword", 0.7)
            self.player_fx.on_attack()
        elif kind == "land":
            self.effects.dust(b.center_x, b.y)
        elif kind == "bump":
            self.bump_block(ev[1])

    def bump_block(self, cell):
        lvl = self.level
        value = lvl.grid.get(*cell)
        cx, cy = cell[0] * TILE + TILE / 2, cell[1] * TILE + TILE / 2
        if value == QBLOCK:
            lvl.grid.set(*cell, USED)
            self.tiles.use_qblock(cell)
            self.audio.play("bump")
            if lvl.dynamic[cell]["reward"] == "heart":
                heart = HeartPickup(cx, cy + TILE)
                self.hearts.append(heart)
                self.objects.append(heart.sprite)
                self.audio.play("powerup", 0.7)
            else:
                self.score.add_coin()
                self.audio.play("coin", 0.8)
                self.effects.pop_coin(cx, cy + TILE)
        elif value == BREAKABLE:
            self.break_block(cell)
        else:
            self.audio.play("bump", 0.4)

    def break_block(self, cell):
        self.tiles.remove_block(self.level, cell)
        self.audio.play("break")
        x, y = cell[0] * TILE + TILE / 2, cell[1] * TILE + TILE / 2
        self.effects.emit(x, y, (150, 110, 90), 14, speed=(150, 380), life=(0.4, 0.8), gravity=1300, size=(3, 5))
        self.effects.shake(3, 0.1)

    def hazard_at(self, rect):
        l, bottom, r, t = rect[0] + 3, rect[1], rect[2] - 3, rect[3] - 6
        for tx in tile_range(l, r):
            for ty in tile_range(bottom, t):
                kind = self.level.hazards.get((tx, ty))
                if kind:
                    hl, hb, hr, ht = HAZARD_BOXES[kind]
                    box = (tx * TILE + hl, ty * TILE + hb, tx * TILE + hr, ty * TILE + ht)
                    if rects_overlap((l, bottom, r, t), box):
                        return kind, tx * TILE + TILE / 2
        return None

    def hazard_near(self):
        b = self.player.body
        grid = self.level.grid
        ty = math.floor(b.y / TILE)
        for tx in range(math.floor(b.x / TILE) - 2, math.floor(b.right / TILE) + 3):
            for dy in (-1, 0, 1):
                if (tx, ty + dy) in self.level.hazards:
                    return True
        if not (grid.standable(math.floor(b.x / TILE), ty - 1) and grid.standable(math.floor(b.right / TILE), ty - 1)):
            return True
        if self.in_boss_zone():
            return True
        return any(abs(s.x - b.center_x) < 4 * TILE and abs(s.y - b.center_y) < 4 * TILE for s in self.saws)

    def hurt_player(self, damage, source_x, cause, killer):
        if not self.player.hurt(damage, source_x, cause):
            return False
        if cause in (DeathCause.CHAMPION, DeathCause.BOSS):
            self.special_hit = (cause, self.play_time)
        self.audio.play("hurt")
        self.effects.shake(6, 0.2)
        b = self.player.body
        self.effects.emit(b.center_x, b.center_y, (255, 80, 90), 10, gravity=600)
        self.player_fx.on_hurt()
        if self.player.dead:
            self.killer = killer
        return True

    def kill_player(self, cause):
        if not self.player.dead:
            self.player.die(cause)
            self.killer = None

    def collide(self, events):
        p, prog = self.player, self.progression
        b = p.body
        prect = (b.x, b.y, b.right, b.top)

        for coin in [c for c in self.coins if rects_overlap(prect, c.box())]:
            self.coins.remove(coin)
            coin.sprite.remove_from_sprite_lists()
            self.score.add_coin()
            self.audio.play("coin", 0.7)
            self.effects.emit(coin.x, coin.y, (255, 230, 120), 6, speed=(60, 160), life=(0.2, 0.4), gravity=0, glow=True)
        for heart in [h for h in self.hearts if rects_overlap(prect, h.box())]:
            self.hearts.remove(heart)
            heart.sprite.remove_from_sprite_lists()
            p.heal(HEART_HEAL)
            self.audio.play("powerup")
            self.effects.emit(heart.x, heart.y + 12, (120, 240, 140), 10, speed=(60, 180), gravity=-40,
                              life=(0.3, 0.6), glow=True)

        if b.vy <= 0:
            feet = (b.x + 2, b.y - 2, b.right - 2, b.y + 8)
            for spring in self.springs:
                if rects_overlap(feet, spring.box()):
                    p.bounce(SPRING_VELOCITY, False)
                    spring.trigger()
                    self.audio.play("spring")
                    break

        box = p.attack_box()
        if box:
            for e in self.enemies:
                if e.dead or id(e) in p.hit_ids:
                    continue
                er = e.contact_box()
                if rects_overlap(box, er) and e.take_hit(prog.damage, b.center_x, events):
                    p.hit_ids.add(id(e))
                    self.effects.hit((max(box[0], er[0]) + min(box[2], er[2])) / 2, b.center_y + 8)
                    self.effects.shake(3, 0.08)
            for pr in self.projectiles:
                if pr.breakable and not pr.removed and rects_overlap(box, pr.box()):
                    pr.removed = True
                    events.append(("splat", pr.x, pr.y, pr.color))
            for tx in tile_range(box[0], box[2]):
                for ty in tile_range(box[1], box[3]):
                    if self.level.grid.get(tx, ty) == BREAKABLE:
                        self.break_block((tx, ty))

        for e in self.enemies:
            if e.dead or (e is self.boss and not e.active):
                continue
            er = e.contact_box()
            if rects_overlap(prect, er):
                if b.vy < -30 and b.y >= er[3] - 18:
                    e.take_hit(prog.damage, b.center_x, events, stomp=True)
                    p.bounce(STOMP_BOUNCE, self.input.jump_held)
                    self.effects.dust(b.center_x, b.y)
                else:
                    self.hurt_player(e.damage, e.body.center_x, e.cause, e)
            for rect, damage in e.attack_boxes():
                if rects_overlap(prect, rect):
                    self.hurt_player(damage, e.body.center_x, e.cause, e)

        for pr in self.projectiles:
            if not pr.removed and pr.harmful and rects_overlap(prect, pr.box()):
                if self.hurt_player(pr.damage, pr.x, pr.cause, pr.owner) and pr.breakable:
                    pr.removed = True
                    events.append(("splat", pr.x, pr.y, pr.color))
        for saw in self.saws:
            if rects_overlap(prect, saw.box()):
                self.hurt_player(saw.damage, saw.x, DeathCause.NORMAL, None)
        hazard = self.hazard_at(prect)
        if hazard:
            kind, hx = hazard
            if kind.startswith("goo"):
                self.kill_player(DeathCause.NORMAL)
            else:
                self.hurt_player(HAZARD_DAMAGE[kind], hx, DeathCause.NORMAL, None)
        if b.top < -20:
            self.kill_player(DeathCause.NORMAL)

    def handle_events(self, events):
        for ev in events:
            kind = ev[0]
            if kind == "sound":
                self.audio.play(ev[1], ev[2])
            elif kind == "shake":
                self.effects.shake(ev[1], ev[2])
            elif kind == "enemy_dead":
                self.on_enemy_dead(ev[1])
            elif kind == "summon":
                gx = self.level.gate_x or 0
                x = min(max(ev[1], gx + 4 * TILE), (self.level.width - 6) * TILE)
                minion = Enemy(x, ev[2])
                minion.facing = 1 if self.player.body.center_x > x else -1
                self.add_enemy(minion, summoned=True)
                self.effects.burst(x, ev[2] + 30, (180, 90, 220), 20)
            elif kind == "shockwave":
                self.add_projectile(Shockwave(ev[1], ev[2], ev[3], ev[4], owner=self.boss))
            elif kind == "projectile":
                self.add_projectile(ev[1])
            elif kind == "splat":
                self.effects.emit(ev[1], ev[2], ev[3], 12, speed=(80, 240), gravity=700, life=(0.3, 0.6), glow=True)

    def on_enemy_dead(self, enemy):
        self.score.add_kill(enemy.score_kind)
        x, y = enemy.body.center_x, enemy.body.center_y
        if isinstance(enemy, Boss):
            self.on_boss_defeated()
            return
        color = {"champion": (120, 255, 170)}.get(enemy.score_kind, (190, 220, 120))
        self.effects.burst(x, y, color, 22)
        if isinstance(enemy, Champion):
            heart = HeartPickup(x, enemy.body.y + 40)
            self.hearts.append(heart)
            self.objects.append(heart.sprite)
            for i in range(3):
                self.score.add_coin()
                self.effects.pop_coin(x + (i - 1) * 24, y)
            self.audio.play("powerup")

    def on_boss_defeated(self):
        self.boss_defeated = True
        self.set_gate(False)
        if self.door:
            self.door.set_open(True)
        self.audio.stop_music()
        self.audio.play("boss_roar", 0.8, speed=0.7)
        self.effects.shake(16, 1.2)
        for e in self.enemies:
            if e.summoned and not e.dead:
                e.die([])
        for pr in self.projectiles:
            pr.removed = True

    def cleanup(self):
        for e in [e for e in self.enemies if e.removed]:
            self.remove_enemy(e)
        for pr in [pr for pr in self.projectiles if pr.removed]:
            self.projectiles.remove(pr)
            pr.sprite.remove_from_sprite_lists()

    def boss_logic(self):
        boss, b = self.boss, self.player.body
        gx = self.level.gate_x
        if boss and gx is not None and not self.boss_defeated and not self.gate_closed and not self.player.dead:
            if b.x > gx + 2 * TILE:
                self.set_gate(True)
                self.audio.play("gate")
                self.effects.shake(8, 0.3)
                events = []
                boss.activate(events)
                self.handle_events(events)
                self.audio.play_music(self.cfg["boss_music"])
        if self.boss_defeated and self.door and self.door.open and rects_overlap((b.x, b.y, b.right, b.top), self.door.box()):
            self.start_victory()

    # ------------------------------------------------------------------
    # Mort, renaissance, victoire
    # ------------------------------------------------------------------
    def death_cause(self):
        """Qui a tué Finn : si un champion ou le boss l'a touché juste avant, c'est lui qui compte,
        même si le coup fatal vient d'un zombie, d'un piège ou d'une chute."""
        cause = self.player.death_cause or DeathCause.NORMAL
        recent = self.special_hit
        if cause == DeathCause.NORMAL and recent and self.play_time - recent[1] <= SPECIAL_DEATH_WINDOW:
            cause = recent[0]
        return cause

    def start_dying(self):
        self.state = "dying"
        self.state_time = 0.0
        self.death_in_boss = self.in_boss_zone()
        self.death_pos = self.last_ground
        self.death_outcome = self.death_manager.handle_death(self.death_cause(), self.death_pos, self.death_in_boss)
        special = self.death_outcome.offer_upgrade
        self.transition = DeathTransition(special)
        self.audio.stop_music()
        b = self.player.body
        if special:        # la mort qui rend plus fort : explosion de lumière
            self.audio.play("death_special")
            self.effects.burst(b.center_x, b.center_y, COLOR_GOLD, 50)
            self.effects.emit(b.center_x, b.center_y, (255, 245, 200), 40, speed=(200, 520), gravity=-60,
                              life=(0.5, 1.1), glow=True, size=(2, 5))
            self.effects.shake(14, 0.5)
        else:              # la mort normale : cendres grises
            self.audio.play("death")
            self.effects.emit(b.center_x, b.center_y, (120, 115, 125), 26, speed=(30, 120), gravity=-40,
                              life=(0.8, 1.6), size=(2, 4))
            self.effects.shake(8, 0.35)
        self.keys.clear()
        self.sync_input()

    def step_dying(self, dt):
        self.state_time += dt
        self.transition.update(dt)
        self.player.update(dt * self.transition.time_scale(), self.input, self.level)
        if self.transition.done:
            self.finish_death()

    def finish_death(self):
        self.state = "dead"
        self.add_grave(*self.death_pos)
        from views.death_view import DeathCardView
        self.window.show_view(DeathCardView(self, self.death_outcome))

    def add_grave(self, x, bottom):
        """Une tombe muette marque l'endroit de chaque mort (sans numéro)."""
        sprite = tile_sprite("grave", 0, 0)
        sprite.center_x, sprite.center_y = x, bottom + TILE / 2
        self.graves.append(sprite)

    def reset_boss(self):
        for e in [e for e in self.enemies if e.summoned]:
            self.remove_enemy(e)
        if self.boss:
            if self.boss not in self.enemies:
                self.add_enemy(self.boss)
            self.boss.reset()
        self.set_gate(False)

    def respawn_spot(self, killer):
        """Quelques cases avant le lieu de la mort, sur un sol sûr et loin du tueur."""
        death_x = self.death_pos[0]
        avoid = killer.home[0] if killer is not None else None
        for x, y in reversed(self.safe_positions):
            if abs(x - death_x) < RESPAWN_BACK_TILES * TILE:
                continue
            if avoid is not None and abs(x - avoid) < 4 * TILE:
                continue
            return x, y
        if self.safe_positions:
            return self.safe_positions[0]
        return self.start.x, self.start.bottom

    def respawn(self, outcome):
        """Appelé après l'écran de mort (et le choix de stat éventuel). La map n'est pas réinitialisée."""
        self.effects.clear()
        for pr in self.projectiles:
            pr.sprite.remove_from_sprite_lists()
        self.projectiles = []
        self.transition = None
        self.special_hit = None
        if outcome.respawn == Respawn.BOSS_GATE:
            self.reset_boss()
            x, bottom = self.boss_respawn.x, self.boss_respawn.bottom
        else:
            killer = self.killer
            if killer is not None and killer in self.enemies:
                killer.reset()
            x, bottom = self.respawn_spot(killer)
        self.place_player(x, bottom)
        self.player.invuln = 1.8
        self.state = "play"
        self.killer = None
        self.keys.clear()
        self.sync_input()
        self.audio.play_music(self.cfg["music"])
        cx, cy = self.player.body.center_x, self.player.body.center_y
        if outcome.aging_stage > 0:
            self.effects.emit(cx, cy, (200, 200, 220), 30, speed=(60, 200), gravity=-80, life=(0.6, 1.2), size=(2, 4))
        else:
            color = COLOR_GOLD if outcome.offer_upgrade else (190, 230, 255)
            self.effects.emit(cx, cy, color, 36, speed=(100, 320), gravity=-100, life=(0.5, 1.1), glow=True, size=(2, 5))

    def start_victory(self):
        self.state = "victory"
        self.state_time = 0.0
        self.audio.stop_music()
        self.audio.play("victory")
        self.keys.clear()
        self.sync_input()

    def step_victory(self, dt):
        self.state_time += dt
        self.player.sprite.alpha = max(0, int(255 * (1 - self.state_time / 1.2)))
        if self.state_time > 1.6:
            self.state = "done"
            from views.victory_view import VictoryView
            self.window.show_view(VictoryView(self))

    # ------------------------------------------------------------------
    # Caméra et effets visuels
    # ------------------------------------------------------------------
    def update_camera(self, dt, snap=False):
        b = self.player.body
        half_w, half_h = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        tx = b.center_x + self.player.facing * 70
        ty = b.center_y + 60
        min_x, max_x = half_w, self.level.pixel_width - half_w
        if self.gate_closed:
            min_x = max(min_x, min(max_x, self.level.gate_x - TILE + half_w))
        tx = min(max(tx, min_x), max_x)
        ty = min(max(ty, half_h), self.level.pixel_height - half_h)
        if snap:
            self.cam_x, self.cam_y = tx, ty
        else:
            k = 1 - math.exp(-dt * 5)
            self.cam_x += (tx - self.cam_x) * k
            self.cam_y += (ty - self.cam_y) * k * 0.8
        ox, oy = self.effects.offset()
        self.camera.position = (round(self.cam_x + ox), round(self.cam_y + oy))

    def update_glows(self):
        """Halos des champions et du boss (celui de Finn est géré par PlayerFx)."""
        for e in self.enemies:
            if e.glow:
                e.glow.center_x, e.glow.center_y = e.body.center_x, e.body.center_y
                e.glow.scale = e.body.h / 26 * (1 + math.sin(self.time * 5 + e.home[0]) * 0.07)
                e.glow.alpha = 0 if e.dead else 100

    def dusk_amount(self):
        x = self.camera.position[0]
        return max(0.0, min(1.0, (x - 190 * TILE) / (60 * TILE)))

    def cave_amount(self):
        x = self.camera.position[0]
        tx0 = max(0, int((x - SCREEN_WIDTH / 2) // TILE))
        tx1 = min(len(self.ceiling) - 1, int((x + SCREEN_WIDTH / 2) // TILE))
        cols = self.ceiling[tx0:tx1 + 1]
        return sum(cols) / len(cols) if cols else 0.0

    # ------------------------------------------------------------------
    # Dessin
    # ------------------------------------------------------------------
    def tip_bubble(self, index):
        if index not in self.tip_bubbles:
            tips = self.cfg.get("tips", [])
            self.tip_bubbles[index] = TipBubble(tips[index]) if index is not None and index < len(tips) else None
        return self.tip_bubbles[index]

    def draw_bubbles(self):
        if self.state != "play":
            return
        for npc in self.npcs:
            bubble = self.tip_bubble(npc.tip) if npc.talking else None
            if bubble is None:
                continue
            bottom = npc.bottom + (84 if npc.kind == "jake" else 60)
            view_left = self.camera.position[0] - SCREEN_WIDTH / 2 + 10
            left = min(max(npc.x - bubble.width / 2, view_left), view_left + SCREEN_WIDTH - 20 - bubble.width)
            bubble.draw(left, bottom, npc.x)

    def draw_enemy_bars(self):
        """Petite barre de vie au-dessus de chaque monstre visible (sauf le boss, qui a la sienne)."""
        view_left = self.camera.position[0] - SCREEN_WIDTH / 2 - 80
        view_right = view_left + SCREEN_WIDTH + 160
        # dessin direct : groupées dans une SpriteList, ces barres qui bougent sans cesse coûtaient plus cher (mesuré)
        for e in self.enemies:
            if e.dead or not e.health_bar or not view_left < e.body.center_x < view_right:
                continue
            w = max(36, e.body.w + 6)
            health_bar(e.body.center_x - w / 2, e.body.top + 12, w, 6, e.hp, e.max_hp, trail=e.hp_shown)

    def on_draw(self):
        screen.begin_frame(self, self.gui_camera)
        screen.fit(self.camera)
        cx, cy = self.camera.position
        self.background.draw(cx, cy, self.time, self.dusk_amount(), self.cave_amount())
        self.camera.use()
        ctx = self.window.ctx
        additive = (ctx.SRC_ALPHA, ctx.ONE)   # additif qui respecte l'alpha du halo
        self.tiles.deco.draw(pixelated=True)
        self.graves.draw(pixelated=True)
        self.tiles.terrain.draw(pixelated=True)
        self.tiles.dynamic.draw(pixelated=True)
        self.objects.draw(pixelated=True)
        self.enemy_glows.draw(blend_function=additive)
        self.player_fx.draw_aura(additive)
        self.enemy_sprites.draw(pixelated=True)
        self.player_fx.draw_ghosts()
        self.player_list.draw(pixelated=True)
        self.projectile_sprites.draw(pixelated=True)
        self.tiles.gate.draw(pixelated=True)
        self.draw_enemy_bars()
        self.effects.draw()
        self.draw_bubbles()
        self.gui_camera.use()
        self.hud.draw()
        if self.state == "dying" and self.transition:
            b = self.player.body
            self.transition.draw(b.center_x - cx + SCREEN_WIDTH / 2, b.center_y - cy + SCREEN_HEIGHT / 2, self.time)
        if self.state == "paused":
            arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (10, 5, 20, 170))
            self.pause_title.draw()
            self.pause_help.draw()
