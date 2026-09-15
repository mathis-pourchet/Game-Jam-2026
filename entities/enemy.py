"""Zombies bonbons : zombie normal, sauteur, champion et le Roi Zombie (boss)."""
import math
import random

import arcade

from entities import assets
from settings import GRAVITY, MAX_FALL_SPEED, TILE
from systems.death_manager import DeathCause
from systems.physics import Body, ground_ahead, move_body, rects_overlap, wall_ahead


def _zombie_frames(variant):
    meta = assets.meta("zombie.json")
    cw, ch = meta["cells"][variant]
    name = f"zombie_{variant}.png"
    right, left = assets.frames(name, cw, ch, meta["count"])
    return meta["anims"], right, left, ch, assets.foot_offset(name, cw, ch, meta["count"])


class Enemy:
    variant = "normal"
    score_kind = "zombie"
    scale = 2.0
    w, h = 26, 44
    max_hp = 1
    speed = 42
    chase_speed = 78
    sight = 7 * TILE
    damage = 1
    cause = DeathCause.NORMAL
    knockback = 1.0
    stomp_kills = True

    def __init__(self, x, bottom):
        self.home = (x, bottom)
        self.anims, self.right, self.left, self.cell_h, self.foot = _zombie_frames(self.variant)
        self.sprite = arcade.Sprite(self.right[0], scale=self.scale)
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
        self.reset_extra()
        self.update_sprite()

    def reset_extra(self):
        """État propre à chaque type d'ennemi (surchargé par les sous-classes)."""

    # ------------------------------------------------------------------
    @property
    def center_x(self):
        return self.body.center_x

    def contact_box(self):
        b = self.body
        return (b.x + 3, b.y, b.right - 3, b.top - 4)

    def attack_boxes(self):
        """Zones d'attaque spéciales : liste de (rect, dégâts)."""
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
        self.think(dt, level, player, events)
        self.body.vy = max(-MAX_FALL_SPEED, self.body.vy - GRAVITY * dt)
        move_body(self.body, level.grid, dt)
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
        dx = player.body.center_x - b.center_x
        dy = player.body.y - b.y
        chasing = not player.dead and abs(dx) < self.sight and abs(dy) < 2.5 * TILE
        if chasing and abs(dx) > 6:
            self.facing = 1 if dx > 0 else -1
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
        return 0.45

    # ------------------------------------------------------------------
    def frame(self):
        a = self.anims
        if self.dead:
            seq = a["burst"]
            return seq[min(len(seq) - 1, int(self.dying / self.death_duration() * len(seq)))]
        if self.hurt_timer > 0:
            return a["stun"][int(self.anim_time * 10) % len(a["stun"])]
        if abs(self.body.vx) > 1:
            return a["walk"][int(self.anim_time * (6 + abs(self.body.vx) / 10)) % len(a["walk"])]
        return a["walk"][0]

    def update_sprite(self):
        tex = (self.right if self.facing > 0 else self.left)[self.frame()]
        self.sprite.texture = tex
        self.sprite.scale = self.scale
        self.sprite.center_x = self.body.center_x
        self.sprite.center_y = self.body.y + (self.cell_h / 2 - self.foot) * self.scale
        self.sprite.color = (255, 150, 150) if self.hurt_timer > 0.2 else (255, 255, 255)


class Jumper(Enemy):
    """Zombie bleu qui bondit vers Finn."""
    variant = "jumper"
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
            hop = self.anims["hop"]
            if not self.body.on_ground:
                return hop[1] if self.body.vy > 0 else hop[2]
            if self.hop_timer < 0.25:
                return hop[0]
            return self.anims["walk"][int(self.anim_time * 6) % 4]
        return super().frame()


class Champion(Enemy):
    """Zombie violet : le tuer est dur, mais mourir face à lui fait renaître Finn plus fort."""
    variant = "champion"
    score_kind = "champion"
    scale = 2.7
    w, h = 36, 60
    max_hp = 5
    speed = 50
    chase_speed = 112
    sight = 9 * TILE
    cause = DeathCause.CHAMPION
    knockback = 0.3
    stomp_kills = False
    TONGUE_DAMAGE = 2

    def reset_extra(self):
        self.state = "patrol"
        self.state_time = 0.0

    def think(self, dt, level, player, events):
        b = self.body
        self.state_time -= dt
        dx = player.body.center_x - b.center_x
        dy = player.body.y - b.y
        if self.state == "windup":
            b.vx = 0
            if self.state_time <= 0:
                self.state, self.state_time = "lash", 0.34
                events.append(("sound", "spit", 0.8))
            return
        if self.state == "lash":
            b.vx = 0
            if self.state_time <= 0:
                self.state, self.state_time = "cooldown", 0.8
            return
        if self.state == "cooldown":
            b.vx = 0
            if self.state_time <= 0:
                self.state = "patrol"
            return
        if self.hurt_timer > 0.2:
            return
        near_home = abs(b.center_x - self.home[0]) < 10 * TILE
        chasing = not player.dead and abs(dx) < self.sight and abs(dy) < 3 * TILE and near_home
        if chasing:
            self.facing = 1 if dx > 0 else -1
            if abs(dx) < 96 and abs(dy) < 60:
                self.state, self.state_time = "windup", 0.42
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
        if self.state != "lash" or self.dead:
            return []
        b = self.body
        y0, y1 = b.y + b.h * 0.3, b.y + b.h * 0.72
        if self.facing > 0:
            return [((b.right - 6, y0, b.right + 84, y1), self.TONGUE_DAMAGE)]
        return [((b.x - 84, y0, b.x + 6, y1), self.TONGUE_DAMAGE)]

    def death_duration(self):
        return 0.9

    def frame(self):
        a = self.anims
        if self.dead:
            seq = a["die"] + a["burst"]
            return seq[min(len(seq) - 1, int(self.dying / self.death_duration() * len(seq)))]
        if self.state == "windup":
            return a["attack"][min(1, int((0.42 - self.state_time) / 0.21))]
        if self.state == "lash":
            return a["attack"][2 + min(2, int((0.34 - self.state_time) / 0.12))]
        if self.state == "cooldown":
            return a["attack"][4] if self.state_time > 0.5 else a["walk"][0]
        return super().frame()


class Boss(Enemy):
    """Le Roi Zombie Bonbon : bonds + ondes de choc, crachats de gomme, coups de langue."""
    variant = "boss"
    score_kind = "boss"
    scale = 4.6
    w, h = 96, 132
    speed = 90
    cause = DeathCause.BOSS
    knockback = 0.0
    stomp_kills = False
    TONGUE_DAMAGE = 2

    def __init__(self, x, bottom, hp):
        self.max_hp = hp
        super().__init__(x, bottom)

    def reset_extra(self):
        self.active = False
        self.state = "sleep"
        self.state_time = 0.0
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
            self._set("intro", 1.6)
            events.append(("sound", "boss_roar", 1.0))
            events.append(("shake", 10, 0.8))

    def _set(self, state, duration):
        self.state = state
        self.state_time = duration

    def _next_attack(self, dx):
        if abs(dx) < 190 and random.random() < 0.6:
            self._set("tongue_windup", 0.5 if not self.enraged else 0.36)
            return
        order = ["walk", "crouch", "spit", "walk", "crouch", "spit"]
        choice = order[self.pattern % len(order)]
        self.pattern += 1
        if choice == "walk":
            self._set("walk", random.uniform(1.4, 2.2))
        elif choice == "crouch":
            self._set("crouch", 0.55 if not self.enraged else 0.4)
        else:
            self._set("spit_windup", 0.55 if not self.enraged else 0.4)

    def think(self, dt, level, player, events):
        b = self.body
        self.flash = max(0.0, self.flash - dt)
        if self.state == "sleep":
            b.vx = 0
            return
        dx = player.body.center_x - b.center_x
        mult = 1.4 if self.enraged else 1.0
        self.state_time -= dt
        if self.state in ("walk", "crouch", "spit_windup", "tongue_windup", "intro") and abs(dx) > 10:
            self.facing = 1 if dx > 0 else -1

        if self.phase == 1 and self.hp <= self.max_hp / 2:
            self.phase = 2
            self._set("intro", 1.3)
            events.append(("sound", "boss_roar", 1.0))
            events.append(("shake", 12, 0.8))
            for side in (-1, 1):
                events.append(("summon", b.center_x + side * 260, b.y + 200))
            return

        if self.state == "intro":
            b.vx = 0
            if self.state_time <= 0:
                self._next_attack(dx)
        elif self.state == "walk":
            b.vx = self.facing * self.speed * mult
            if wall_ahead(b, level.grid, self.facing):
                b.vx = 0
            if self.state_time <= 0 or abs(dx) < 60:
                self._next_attack(dx)
        elif self.state == "crouch":
            b.vx = 0
            if self.state_time <= 0:
                b.vy = 980
                flight = 2 * 980 / GRAVITY
                b.vx = max(-460.0, min(460.0, dx / flight))
                self.airborne = True
                self._set("air", 3.0)
                events.append(("sound", "jump", 0.8))
        elif self.state == "air":
            if self.airborne and b.on_ground and b.vy <= 0:
                self.airborne = False
                b.vx = 0
                events.append(("sound", "boss_slam", 1.0))
                events.append(("shake", 14, 0.45))
                for side in (-1, 1):
                    events.append(("shockwave", b.center_x + side * (b.w / 2), b.y, side, 360 * mult))
                self._set("recover", 0.75 if not self.enraged else 0.45)
        elif self.state == "spit_windup":
            b.vx = 0
            if self.state_time <= 0:
                count = 3 if not self.enraged else 5
                mouth_x = b.center_x + self.facing * b.w * 0.4
                for i in range(count):
                    spread = (i - (count - 1) / 2) * 70
                    vx = (dx + spread) / 1.1
                    events.append(("spit", mouth_x, b.y + b.h * 0.6, max(-520, min(520, vx)),
                                   random.uniform(520, 640)))
                events.append(("sound", "spit", 1.0))
                self._set("recover", 0.8 if not self.enraged else 0.5)
        elif self.state == "tongue_windup":
            b.vx = 0
            if self.state_time <= 0:
                self._set("tongue", 0.42)
                events.append(("sound", "spit", 0.9))
        elif self.state == "tongue":
            b.vx = 0
            if self.state_time <= 0:
                self._set("recover", 0.6 if not self.enraged else 0.4)
        elif self.state == "recover":
            b.vx = 0
            if self.state_time <= 0:
                self._next_attack(dx)

    def attack_boxes(self):
        if self.state != "tongue" or self.dead:
            return []
        b = self.body
        y0, y1 = b.y + b.h * 0.25, b.y + b.h * 0.6
        if self.facing > 0:
            return [((b.right - 10, y0, b.right + 170, y1), self.TONGUE_DAMAGE)]
        return [((b.x - 170, y0, b.x + 10, y1), self.TONGUE_DAMAGE)]

    def contact_box(self):
        b = self.body
        return (b.x + 10, b.y, b.right - 10, b.top - 16)

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
        if self.dead:
            seq = a["die"] + a["burst"]
            return seq[min(len(seq) - 1, int(self.dying / self.death_duration() * len(seq)))]
        s = self.state
        if s == "sleep":
            return a["stun"][int(self.anim_time * 3) % len(a["stun"])]
        if s == "intro":
            return a["attack"][1 + int(self.anim_time * 8) % 2]
        if s == "crouch":
            return a["hop"][0]
        if s == "air":
            return a["hop"][1] if self.body.vy > 0 else a["hop"][2]
        if s in ("spit_windup", "tongue_windup"):
            return a["attack"][int(self.anim_time * 6) % 2]
        if s == "tongue":
            return a["attack"][2 + min(2, int((0.42 - self.state_time) / 0.14))]
        if s == "recover":
            return a["walk"][0]
        return super().frame()

    def update_sprite(self):
        super().update_sprite()
        if self.flash > 0:
            self.sprite.color = (255, 120, 120)
        elif self.enraged and not self.dead:
            self.sprite.color = (255, 205, 205)


class GooBall:
    """Boule de gomme crachée par le boss (arc balistique)."""
    damage = 1
    cause = DeathCause.BOSS

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.sprite = arcade.Sprite(assets.texture("goo_ball.png"), scale=3, center_x=x, center_y=y)
        self.life = 4.0
        self.removed = False

    def box(self):
        return (self.x - 12, self.y - 12, self.x + 12, self.y + 12)

    def update(self, dt, level, events):
        self.vy = max(-MAX_FALL_SPEED, self.vy - GRAVITY * 0.6 * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.sprite.center_x, self.sprite.center_y = self.x, self.y
        self.sprite.angle += 400 * dt
        if level.grid.blocking(math.floor(self.x / TILE), math.floor((self.y - 10) / TILE)) or self.life <= 0:
            self.removed = True
            events.append(("splat", self.x, self.y))


class Shockwave:
    """Onde de choc qui court au sol après le bond du boss."""
    damage = 1
    cause = DeathCause.BOSS

    def __init__(self, x, y, direction, speed):
        self.x, self.y, self.dir, self.speed = x, y, direction, speed
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
