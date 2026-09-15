"""Monstres : zombie (niveau 1), sorcier squelette (niveau 2, champion) et le Roi des Glaces (boss final)."""
import math
import random

import arcade

from entities import assets
from settings import GRAVITY, MAX_FALL_SPEED, TILE
from systems.death_manager import DeathCause
from systems.physics import Body, ground_ahead, move_body, rects_overlap, wall_ahead


def monster_art(kind):
    """Textures (droite, gauche) et animations d'un monstre de assets/sprites/monsters.json."""
    meta = assets.meta("monsters.json")[kind]
    cw, ch = meta["cell"]
    right, left = assets.frames(meta["file"], cw, ch, meta["count"])
    return meta["anims"], right, left, ch, meta["foot"]


def seq_frame(seq, t, fps, loop=True):
    i = int(t * fps)
    return seq[i % len(seq)] if loop else seq[min(i, len(seq) - 1)]


class Enemy:
    """Monstre niveau 1 : le zombie. Patrouille, court vers Finn et lui bondit dessus."""
    art = "zombie"
    score_kind = "zombie"
    w, h = 30, 48
    max_hp = 1
    speed = 42
    chase_speed = 88
    sight = 7 * TILE
    damage = 1
    cause = DeathCause.NORMAL
    knockback = 1.0
    stomp_kills = True
    uses_platforms = True   # peut se poser sur les plateformes traversables

    def __init__(self, x, bottom):
        self.home = (x, bottom)
        self.anims, self.right, self.left, self.cell_h, self.foot = monster_art(self.art)
        self.sprite = arcade.Sprite(self.right[0])
        self.body = Body(0, 0, self.w, self.h)
        self.reset()

    def reset(self):
        self.body.place_center_bottom(*self.home)
        self.body.vx = self.body.vy = 0
        self.hp = self.max_hp
        self.facing = -1
        self.dead = False
        self.removed = False
        self.dying = 0.0
        self.hurt_timer = 0.0
        self.anim_time = random.random()
        self.groan_timer = random.uniform(3, 8)
        self.state = "patrol"
        self.state_time = 0.0
        self.cooldown = random.uniform(0.5, 1.5)
        self.reset_extra()
        self.update_sprite()

    def reset_extra(self):
        """État propre à chaque type de monstre (surchargé par les sous-classes)."""

    # ------------------------------------------------------------------
    @property
    def center_x(self):
        return self.body.center_x

    def contact_box(self):
        b = self.body
        return (b.x + 3, b.y, b.right - 3, b.top - 4)

    def attack_boxes(self):
        """Zones d'attaque au corps à corps : liste de (rect, dégâts)."""
        return []

    def update(self, dt, level, player, events):
        if self.dead:
            self.dying += dt
            self.anim_time += dt
            if self.dying > self.death_duration():
                self.removed = True
            self.update_sprite()
            return
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.state_time -= dt
        self.think(dt, level, player, events)
        self.body.vy = max(-MAX_FALL_SPEED, self.body.vy - GRAVITY * dt)
        move_body(self.body, level.grid, dt, oneway=self.uses_platforms)
        if self.body.top < 0:
            self.dead = True
            self.removed = True
        self.anim_time += dt
        self.groan_timer -= dt
        if self.groan_timer <= 0:
            self.groan_timer = random.uniform(5, 10)
            if abs(player.body.center_x - self.center_x) < 9 * TILE:
                events.append(("sound", "zombie_groan", 0.5))
        self.update_sprite()

    def think(self, dt, level, player, events):
        b = self.body
        if self.hurt_timer > 0:
            return
        if self.state == "lunge":
            if self.state_time <= 0.3 and b.on_ground:
                self.state = "patrol"
                b.vx = 0
            return
        dx = player.body.center_x - b.center_x
        dy = player.body.y - b.y
        chasing = not player.dead and abs(dx) < self.sight and abs(dy) < 2.5 * TILE
        if chasing and abs(dx) > 6:
            self.facing = 1 if dx > 0 else -1
        if chasing and b.on_ground and abs(dx) < 96 and abs(dy) < 40 and self.cooldown <= 0:
            self.state, self.state_time = "lunge", 0.6
            self.cooldown = 1.8
            b.vx = self.facing * 250
            b.vy = 280
            return
        speed = self.chase_speed if chasing else self.speed
        if b.on_ground and (wall_ahead(b, level.grid, self.facing) or not ground_ahead(b, level.grid, self.facing)):
            if chasing:
                speed = 0
            else:
                self.facing = -self.facing
        if b.on_ground:
            b.vx = self.facing * speed

    def take_hit(self, damage, source_x, events, stomp=False):
        if self.dead or self.hurt_timer > 0.12:
            return False
        self.hp -= damage if not (stomp and self.stomp_kills) else self.hp
        self.hurt_timer = 0.32
        direction = 1 if self.center_x >= source_x else -1
        if not stomp:
            self.body.vx = 170 * direction * self.knockback
            self.body.vy = 230 * self.knockback
        events.append(("sound", "stomp" if stomp else "hit", 1.0))
        if self.hp <= 0:
            self.die(events)
        return True

    def die(self, events):
        self.dead = True
        self.dying = 0.0
        self.anim_time = 0.0
        self.body.vx = 0
        events.append(("enemy_dead", self))

    def death_duration(self):
        return 0.9

    # ------------------------------------------------------------------
    def frame(self):
        a = self.anims
        if self.dead:
            return seq_frame(a["die"], self.dying, 7, loop=False)
        if self.hurt_timer > 0:
            return seq_frame(a["hurt"], self.anim_time, 10)
        if self.state == "lunge" and "lunge" in a:
            return seq_frame(a["lunge"], 0.6 - self.state_time, 8, loop=False)
        speed = abs(self.body.vx)
        if speed > self.speed + 10:
            return seq_frame(a["run"], self.anim_time, 12)
        if speed > 1:
            return seq_frame(a["walk"], self.anim_time, 8)
        return seq_frame(a["idle"], self.anim_time, 6)

    def update_sprite(self):
        self.sprite.texture = (self.right if self.facing > 0 else self.left)[self.frame()]
        self.sprite.center_x = self.body.center_x
        self.sprite.center_y = self.body.y + self.cell_h / 2 - self.foot
        self.sprite.color = (255, 150, 150) if self.hurt_timer > 0.2 else (255, 255, 255)
        fade = (self.death_duration() - self.dying) / 0.3 if self.dead else 1.0
        self.sprite.alpha = int(255 * max(0.0, min(1.0, fade)))


class Jumper(Enemy):
    """Zombie (niveau 1) qui avance par grands bonds vers Finn."""
    score_kind = "jumper"
    max_hp = 2

    def reset_extra(self):
        self.hop_timer = random.uniform(0.6, 1.4)

    def think(self, dt, level, player, events):
        b = self.body
        if self.hurt_timer > 0:
            return
        dx = player.body.center_x - b.center_x
        if b.on_ground:
            b.vx *= 0.8
            self.hop_timer -= dt
            if self.hop_timer <= 0 and not player.dead and abs(dx) < 9 * TILE:
                self.facing = 1 if dx > 0 else -1
                b.vy = 640
                b.vx = self.facing * random.uniform(130, 180)
                self.hop_timer = random.uniform(1.0, 1.6)

    def frame(self):
        if not self.dead and self.hurt_timer <= 0:
            lunge = self.anims["lunge"]
            if not self.body.on_ground:
                return lunge[1] if self.body.vy > 0 else lunge[3]
            if self.hop_timer < 0.25:
                return lunge[0]
            return seq_frame(self.anims["idle"], self.anim_time, 6)
        return super().frame()


class Champion(Enemy):
    """Monstre niveau 2 : le sorcier squelette. Griffe de près, lance des boules de feu de loin.
    Mourir face à lui fait renaître Finn plus fort."""
    art = "lich"
    score_kind = "champion"
    w, h = 40, 70
    max_hp = 5
    speed = 45
    chase_speed = 100
    sight = 10 * TILE
    cause = DeathCause.CHAMPION
    knockback = 0.3
    stomp_kills = False
    SWIPE_DAMAGE = 2

    def reset_extra(self):
        self.cast_cd = random.uniform(1.0, 2.0)

    def think(self, dt, level, player, events):
        b = self.body
        self.cast_cd = max(0.0, self.cast_cd - dt)
        s = self.state
        if s in ("swipe_windup", "swipe", "cast_windup", "cast_release", "recover"):
            b.vx = 0
            if self.state_time > 0:
                return
            if s == "swipe_windup":
                self.state, self.state_time = "swipe", 0.3
                events.append(("sound", "sword", 0.6))
            elif s == "swipe":
                self.state, self.state_time = "recover", 0.7
            elif s == "cast_windup":
                self.state, self.state_time = "cast_release", 0.45
                x = b.center_x + self.facing * (b.w / 2 + 18)
                y = b.y + b.h * 0.6
                events.append(("projectile", Projectile("proj_fireball.png", x, y, self.facing * 290, 0, 1,
                                                        DeathCause.CHAMPION, life=3.5, radius=13,
                                                        color=(120, 255, 170), owner=self)))
                events.append(("sound", "spit", 0.9))
            else:
                self.state = "patrol"
            return
        if self.hurt_timer > 0.2:
            return
        dx = player.body.center_x - b.center_x
        dy = player.body.y - b.y
        near_home = abs(b.center_x - self.home[0]) < 10 * TILE
        chasing = not player.dead and abs(dx) < self.sight and abs(dy) < 3 * TILE and near_home
        if chasing:
            self.facing = 1 if dx > 0 else -1
            if abs(dx) < 92 and abs(dy) < 60:
                self.state, self.state_time = "swipe_windup", 0.4
                b.vx = 0
                return
            if abs(dx) > 130 and abs(dy) < 1.5 * TILE and self.cast_cd <= 0:
                self.state, self.state_time = "cast_windup", 0.55
                self.cast_cd = 2.6
                b.vx = 0
                return
        elif not near_home:
            self.facing = 1 if self.home[0] > b.center_x else -1
        speed = self.chase_speed if chasing else self.speed
        if b.on_ground and (wall_ahead(b, level.grid, self.facing) or not ground_ahead(b, level.grid, self.facing)):
            if chasing:
                speed = 0
            else:
                self.facing = -self.facing
        if b.on_ground:
            b.vx = self.facing * speed

    def attack_boxes(self):
        if self.state != "swipe" or self.dead:
            return []
        b = self.body
        y0, y1 = b.y + b.h * 0.2, b.y + b.h * 0.85
        if self.facing > 0:
            return [((b.right - 6, y0, b.right + 76, y1), self.SWIPE_DAMAGE)]
        return [((b.x - 76, y0, b.x + 6, y1), self.SWIPE_DAMAGE)]

    def death_duration(self):
        return 1.2

    def frame(self):
        a = self.anims
        s = self.state
        if self.dead:
            return seq_frame(a["die"], self.dying, 5, loop=False)
        if s == "swipe_windup":
            return a["attack"][min(1, int((0.4 - self.state_time) / 0.2))]
        if s == "swipe":
            return a["attack"][2 + min(1, int((0.3 - self.state_time) / 0.15))]
        if s == "cast_windup":
            return a["cast"][min(1, int((0.55 - self.state_time) / 0.28))]
        if s == "cast_release":
            return a["cast"][2]
        if s == "recover" and self.hurt_timer <= 0:
            return seq_frame(a["idle"], self.anim_time, 5)
        return super().frame()


class Boss(Enemy):
    """Le Roi des Glaces : vol + ondes de glace, éclats de glace, pluie de stalactites."""
    art = "boss"
    score_kind = "boss"
    w, h = 92, 150
    speed = 95
    cause = DeathCause.BOSS
    knockback = 0.0
    stomp_kills = False
    uses_platforms = False  # retombe toujours au sol (ses ondes de glace courent par terre)

    def __init__(self, x, bottom, hp):
        self.max_hp = hp
        super().__init__(x, bottom)

    def reset_extra(self):
        self.active = False
        self.state = "sleep"
        self.phase = 1
        self.pattern = 0
        self.flash = 0.0
        self.airborne = False

    @property
    def enraged(self):
        return self.phase == 2

    def activate(self, events):
        if not self.active:
            self.active = True
            self._set("intro", 1.8)
            events.append(("sound", "boss_roar", 1.0))
            events.append(("shake", 10, 0.8))

    def _set(self, state, duration):
        self.state = state
        self.state_time = duration

    def _next_attack(self, dx):
        fast = self.enraged
        if abs(dx) < 200 and random.random() < 0.5:
            self._set("blizzard_windup", 0.6 if fast else 0.8)
            return
        order = ["walk", "crouch", "shards_windup", "walk", "blizzard_windup", "shards_windup"]
        choice = order[self.pattern % len(order)]
        self.pattern += 1
        durations = {"walk": random.uniform(1.4, 2.2), "crouch": 0.4 if fast else 0.55,
                     "shards_windup": 0.45 if fast else 0.6, "blizzard_windup": 0.6 if fast else 0.8}
        self._set(choice, durations[choice])

    def think(self, dt, level, player, events):
        b = self.body
        self.flash = max(0.0, self.flash - dt)
        if self.state == "sleep":
            b.vx = 0
            return
        dx = player.body.center_x - b.center_x
        mult = 1.4 if self.enraged else 1.0
        if self.state in ("walk", "crouch", "shards_windup", "blizzard_windup", "intro") and abs(dx) > 10:
            self.facing = 1 if dx > 0 else -1

        if self.phase == 1 and self.hp <= self.max_hp / 2:
            self.phase = 2
            self._set("intro", 1.3)
            events.append(("sound", "boss_roar", 1.0))
            events.append(("shake", 12, 0.8))
            for side in (-1, 1):
                events.append(("summon", b.center_x + side * 260, b.y + 200))
            return

        s = self.state
        if s == "intro":
            b.vx = 0
            if self.state_time <= 0:
                self._next_attack(dx)
        elif s == "walk":
            b.vx = self.facing * self.speed * mult
            if wall_ahead(b, level.grid, self.facing):
                b.vx = 0
            if self.state_time <= 0 or abs(dx) < 70:
                self._next_attack(dx)
        elif s == "crouch":
            b.vx = 0
            if self.state_time <= 0:
                b.vy = 980
                flight = 2 * 980 / GRAVITY
                b.vx = max(-460.0, min(460.0, dx / flight))
                self.airborne = True
                self._set("air", 3.0)
                events.append(("sound", "jump", 0.8))
        elif s == "air":
            if self.airborne and b.on_ground and b.vy <= 0:
                self.airborne = False
                b.vx = 0
                events.append(("sound", "boss_slam", 1.0))
                events.append(("shake", 14, 0.45))
                for side in (-1, 1):
                    events.append(("shockwave", b.center_x + side * (b.w / 2), b.y, side, 360 * mult))
                self._set("recover", 0.45 if self.enraged else 0.75)
        elif s == "shards_windup":
            b.vx = 0
            if self.state_time <= 0:
                sx, sy = b.center_x + self.facing * 60, b.y + b.h * 0.62
                aim = math.atan2(player.body.center_y - sy, player.body.center_x - sx)
                spreads = (-0.36, -0.18, 0, 0.18, 0.36) if self.enraged else (-0.18, 0, 0.18)
                for spread in spreads:
                    angle = aim + spread
                    events.append(("projectile", Projectile("proj_ice.png", sx, sy, math.cos(angle) * 430,
                                                            math.sin(angle) * 430, 1, DeathCause.BOSS, life=3.0,
                                                            radius=14, orient=True, color=(200, 240, 255),
                                                            owner=self)))
                events.append(("sound", "spit", 1.0))
                self._set("shards", 0.5)
        elif s == "blizzard_windup":
            b.vx = 0
            if self.state_time <= 0:
                count = 7 if self.enraged else 5
                top = min(22 * TILE - 24, player.body.top + 360)
                for i in range(count):
                    x = player.body.center_x + (i - (count - 1) / 2) * 72 + random.uniform(-14, 14)
                    events.append(("projectile", Projectile("proj_ice.png", x, top, 0, -1, 1, DeathCause.BOSS,
                                                            gravity=1400, delay=0.55 + abs(i - count // 2) * 0.08,
                                                            life=4.0, radius=12, orient=True,
                                                            color=(200, 240, 255), owner=self)))
                events.append(("sound", "aging", 0.7))
                self._set("blizzard", 0.8)
        elif s in ("shards", "blizzard"):
            b.vx = 0
            if self.state_time <= 0:
                self._set("recover", 0.45 if self.enraged else 0.7)
        elif s == "recover":
            b.vx = 0
            if self.state_time <= 0:
                self._next_attack(dx)

    def contact_box(self):
        b = self.body
        return (b.x + 12, b.y, b.right - 12, b.top - 20)

    def take_hit(self, damage, source_x, events, stomp=False):
        if self.dead or self.state == "sleep" or self.flash > 0:
            return False
        self.hp -= damage
        self.flash = 0.22
        events.append(("sound", "hit", 1.0))
        if self.hp <= 0:
            self.die(events)
        return True

    def death_duration(self):
        return 2.4

    def frame(self):
        a = self.anims
        s = self.state
        if self.dead:
            return seq_frame(a["die"], self.dying, 3, loop=False)
        if self.flash > 0:
            return a["hurt"][int((0.22 - self.flash) * 18) % len(a["hurt"])]
        if s in ("sleep", "recover"):
            return seq_frame(a["idle"], self.anim_time, 6)
        if s == "intro":
            return seq_frame(a["taunt"], self.anim_time, 6)
        if s == "walk":
            return seq_frame(a["float"], self.anim_time, 10)
        if s in ("crouch", "shards_windup"):
            return a["charge"][0]
        if s == "air":
            return seq_frame(a["glide"], self.anim_time, 8)
        if s == "shards":
            return a["shoot"][0]
        if s in ("blizzard_windup", "blizzard"):
            return seq_frame(a["overhead"], self.anim_time, 6)
        return seq_frame(a["idle"], self.anim_time, 6)

    def update_sprite(self):
        super().update_sprite()
        if self.enraged and not self.dead:
            self.sprite.color = (190, 215, 255)


class Projectile:
    """Projectile d'un monstre : boule de feu, éclat de glace, stalactite (avec avertissement)."""
    breakable = True

    def __init__(self, texture, x, y, vx, vy, damage, cause, gravity=0.0, life=4.0, delay=0.0, radius=12,
                 orient=False, color=(255, 255, 255), owner=None):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.damage, self.cause, self.owner = damage, cause, owner
        self.gravity, self.life, self.delay, self.radius = gravity, life, delay, radius
        self.orient = orient
        self.color = color
        tex = assets.texture(texture)
        if not orient and vx < 0:
            tex = tex.flip_left_right()
        self.sprite = arcade.Sprite(tex, center_x=x, center_y=y)
        self.removed = False
        self._orient()

    @property
    def harmful(self):
        return self.delay <= 0

    def box(self):
        r = self.radius
        return (self.x - r, self.y - r, self.x + r, self.y + r)

    def _orient(self):
        if self.orient and (self.vx or self.vy):
            self.sprite.angle = -math.degrees(math.atan2(self.vy, self.vx))

    def update(self, dt, level, events):
        if self.delay > 0:
            self.delay -= dt
            self.sprite.alpha = 110 + int(80 * abs(math.sin(self.delay * 18)))
            return
        self.sprite.alpha = 255
        self.vy = max(-MAX_FALL_SPEED, self.vy - self.gravity * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.sprite.center_x, self.sprite.center_y = self.x, self.y
        self._orient()
        if self.life <= 0 or level.grid.blocking(math.floor(self.x / TILE), math.floor(self.y / TILE)):
            self.removed = True
            events.append(("splat", self.x, self.y, self.color))


class Shockwave:
    """Onde de glace qui court au sol quand le boss retombe."""
    damage = 1
    cause = DeathCause.BOSS
    breakable = False
    harmful = True
    color = (200, 240, 255)

    def __init__(self, x, y, direction, speed, owner=None):
        self.x, self.y, self.dir, self.speed, self.owner = x, y, direction, speed, owner
        self.sprite = arcade.Sprite(assets.texture("shockwave.png"), scale=3)
        if direction < 0:
            self.sprite.texture = self.sprite.texture.flip_left_right()
        self.life = 2.2
        self.removed = False

    def box(self):
        return (self.x - 22, self.y, self.x + 22, self.y + 30)

    def update(self, dt, level, events):
        self.x += self.dir * self.speed * dt
        self.life -= dt
        wall = level.grid.blocking(math.floor((self.x + self.dir * 24) / TILE), math.floor((self.y + 8) / TILE))
        if wall or self.life <= 0:
            self.removed = True
        self.sprite.center_x = self.x
        self.sprite.center_y = self.y + 16 + math.sin(self.life * 30) * 2
        self.sprite.alpha = int(255 * min(1.0, self.life / 0.4))


def overlaps(rect_a, rect_b):
    return rects_overlap(rect_a, rect_b)
