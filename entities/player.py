"""Finn : déplacements, saut, échelles, épée, dégâts et apparence (muscles / vieillesse)."""
import math

import arcade

from entities import assets
from settings import (AIR_ACCEL, ATTACK_COOLDOWN, ATTACK_TIME, COYOTE_TIME, GRAVITY, GROUND_ACCEL,
                      GROUND_FRICTION, ICE_ACCEL, ICE_FRICTION, INVULN_TIME, JUMP_BUFFER, JUMP_CUT,
                      KNOCKBACK_X, KNOCKBACK_Y, LADDER_SPEED, MAX_FALL_SPEED, PLAYER_H, PLAYER_W, TILE)
from systems.physics import ONEWAY, Body, move_body

# Teinte du sprite selon l'âge : Finn grisonne franchement en vieillissant
AGING_TINT = {0: (255, 255, 255), 1: (205, 200, 205), 2: (165, 160, 170)}


def approach(value, target, step):
    if value < target:
        return min(target, value + step)
    return max(target, value - step)


class InputState:
    def __init__(self):
        self.left = self.right = self.up = self.down = False
        self.jump_held = False
        self.jump_pressed = False
        self.attack_pressed = False

    def consume(self):
        self.jump_pressed = False
        self.attack_pressed = False


class Player:
    def __init__(self, progression):
        self.progression = progression
        self.body = Body(0, 0, PLAYER_W, PLAYER_H)
        meta = assets.meta("finn.json")
        cw, ch = meta["cell"]
        self.cell_h = ch
        self.foot = ch - meta["anchor"][1]
        # une planche par apparence : muscle1..4 (progression) et old1..2 (vieillissement)
        self.variant_anims = {v: info["anims"] for v, info in meta["variants"].items()}
        self.textures = {v: assets.frames(f"finn_{v}.png", cw, ch, info["count"])
                         for v, info in meta["variants"].items()}
        self.sprite = arcade.Sprite(self.textures["muscle1"][0][0])
        self.reset()

    def reset(self, x=0.0, bottom=0.0):
        b = self.body
        b.place_center_bottom(x, bottom)
        b.vx = b.vy = 0
        b.drop_through = 0
        b.on_ground = False
        self.hp = self.progression.max_hp
        self.facing = 1
        self.dead = False
        self.death_cause = None
        self.death_time = 0.0
        self.attack_timer = 0.0
        self.attack_cd = 0.0
        self.invuln = 0.0
        self.stun = 0.0
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.jumping = False
        self.on_ladder = False
        self.anim_time = 0.0
        self.land_timer = 0.0
        self.hit_ids = set()
        self.update_sprite()

    # ------------------------------------------------------------------
    @property
    def attacking(self):
        return self.attack_timer > 0

    def jump_velocity(self):
        return math.sqrt(2 * GRAVITY * self.progression.jump_height)

    def attack_box(self):
        """Zone touchée par l'épée pendant la partie active du coup (ou None)."""
        if not 0.05 < self.attack_timer < ATTACK_TIME - 0.03:
            return None
        b = self.body
        reach = self.progression.attack_reach
        if self.facing > 0:
            return (b.center_x, b.y + 2, b.right + reach, b.top + 14)
        return (b.x - reach, b.y + 2, b.center_x, b.top + 14)

    def _standing_on_oneway(self, level):
        ty = math.floor((self.body.y - 1) / TILE)
        cells = {math.floor((self.body.x + 2) / TILE), math.floor((self.body.right - 2) / TILE)}
        kinds = [level.grid.get(tx, ty) for tx in cells]
        return all(k in (ONEWAY, 0) for k in kinds) and ONEWAY in kinds

    # ------------------------------------------------------------------
    def update(self, dt, inp, level):
        events = []
        b = self.body
        if self.dead:
            # le corps tombe et reste allongé au sol (pas de bond ni de traversée du sol)
            self.death_time += dt
            b.vx = approach(b.vx, 0, 900 * dt)
            b.vy = max(-MAX_FALL_SPEED, b.vy - GRAVITY * dt)
            move_body(b, level.grid, dt)
            self.anim_time += dt
            self.update_sprite()
            return events

        prog = self.progression
        self.invuln = max(0.0, self.invuln - dt)
        self.stun = max(0.0, self.stun - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.land_timer = max(0.0, self.land_timer - dt)

        move = (1 if inp.right else 0) - (1 if inp.left else 0)
        if self.stun > 0:
            move = 0
        if move:
            self.facing = move

        if inp.attack_pressed and self.attack_cd <= 0 and not self.on_ladder and self.stun <= 0:
            self.attack_timer = ATTACK_TIME
            self.attack_cd = ATTACK_COOLDOWN
            self.hit_ids = set()
            events.append(("attack",))

        self.jump_buffer = JUMP_BUFFER if inp.jump_pressed else max(0.0, self.jump_buffer - dt)

        # --- échelles ---
        tx = math.floor(b.center_x / TILE)
        feet = (tx, math.floor((b.y + 2) / TILE))
        below = (tx, math.floor((b.y - 4) / TILE))
        if not self.on_ladder and self.stun <= 0:
            grab_up = inp.up and (feet in level.ladders or (tx, math.floor(b.center_y / TILE)) in level.ladders)
            grab_down = inp.down and b.on_ground and below in level.ladders
            if grab_up or grab_down:
                self.on_ladder = True
                self.jumping = False
                b.vx = 0
        if self.on_ladder:
            still = feet in level.ladders or (inp.down and below in level.ladders)
            if self.jump_buffer > 0:
                self.on_ladder = False
                b.vy = self.jump_velocity() * 0.8
                self.jump_buffer = 0
                self.jumping = True
                events.append(("jump",))
            elif not still or (move and b.on_ground and not inp.up):
                self.on_ladder = False
                if not still and inp.up and below in level.ladders:
                    b.y = (below[1] + 1) * TILE   # arrivé en haut : on pose les pieds
                b.vy = 0
            else:
                b.x += ((tx + 0.5) * TILE - b.center_x) * min(1.0, dt * 14)
                b.vx = 0
                b.vy = ((1 if inp.up else 0) - (1 if inp.down else 0)) * LADDER_SPEED
                if inp.down:
                    b.drop_through = 0.12
                move_body(b, level.grid, dt)
                if b.vy:
                    self.anim_time += dt
                self.coyote = 0
                self.update_sprite()
                return events

        # --- déplacement horizontal ---
        target = move * prog.run_speed * (0.55 if self.attacking and b.on_ground else 1.0)
        if b.on_ice:
            accel, friction = ICE_ACCEL, ICE_FRICTION
        elif b.on_ground:
            accel, friction = GROUND_ACCEL, GROUND_FRICTION
        else:
            accel, friction = AIR_ACCEL, 520
        if self.stun > 0:
            b.vx = approach(b.vx, 0, 300 * dt)
        elif move:
            rate = accel if b.vx * move >= 0 else accel + friction
            b.vx = approach(b.vx, target, rate * dt)
        else:
            b.vx = approach(b.vx, 0, friction * dt)

        # --- saut ---
        b.vy = max(-MAX_FALL_SPEED, b.vy - GRAVITY * dt)
        self.coyote = COYOTE_TIME if b.on_ground else max(0.0, self.coyote - dt)
        if self.jump_buffer > 0 and self.coyote > 0 and self.stun <= 0:
            self.jump_buffer = 0
            self.coyote = 0
            if inp.down and self._standing_on_oneway(level):
                b.drop_through = 0.22
            else:
                b.vy = self.jump_velocity()
                self.jumping = True
                events.append(("jump",))
        if self.jumping and b.vy > 0 and not inp.jump_held:
            b.vy *= JUMP_CUT
            self.jumping = False
        if b.vy <= 0:
            self.jumping = False

        was_on_ground, vy_before = b.on_ground, b.vy
        move_body(b, level.grid, dt)
        if b.hit_ceiling:
            events.append(("bump", b.hit_ceiling))
            self.jumping = False
        if b.on_ground and not was_on_ground and vy_before < -250:
            self.land_timer = 0.08
            events.append(("land",))
        self.anim_time += dt
        self.update_sprite()
        return events

    # ------------------------------------------------------------------
    def bounce(self, velocity, held):
        self.body.vy = velocity * (1.25 if held else 1.0)
        self.jumping = False

    def hurt(self, damage, source_x, cause):
        """Applique des dégâts. Renvoie True si Finn a été touché."""
        if self.invuln > 0 or self.dead:
            return False
        self.hp -= damage
        self.invuln = INVULN_TIME
        self.stun = 0.28
        self.on_ladder = False
        direction = 1 if self.body.center_x >= source_x else -1
        self.body.vx = KNOCKBACK_X * direction
        self.body.vy = KNOCKBACK_Y
        if self.hp <= 0:
            self.die(cause)
        return True

    def die(self, cause):
        if self.dead:
            return
        self.hp = 0
        self.dead = True
        self.death_cause = cause
        self.death_time = 0.0
        self.body.vx = 0
        self.body.vy = min(self.body.vy, 0.0)
        self.on_ladder = False

    def heal(self, amount):
        self.hp = min(self.progression.max_hp, self.hp + amount)

    # ------------------------------------------------------------------
    def _frame(self, a):
        t = self.anim_time
        b = self.body
        if self.dead:
            return a["hurt"][0] if self.death_time < 0.35 else a["dead"][0]
        if self.on_ladder:
            return a["climb"][int(t * 7) % len(a["climb"])]
        if self.attack_timer > 0:
            seq = a["attack"] if b.on_ground else a["air_attack"]
            progress = 1 - self.attack_timer / ATTACK_TIME
            return seq[min(len(seq) - 1, int(progress * len(seq)))]
        if self.stun > 0:
            return a["hurt"][0]
        if not b.on_ground:
            if b.vy > 0:
                seq = a["jump"]
                return seq[0 if b.vy > self.jump_velocity() * 0.7 else len(seq) - 1]
            return a["fall"][0]
        if self.land_timer > 0:
            return a["land"][0]
        speed = abs(b.vx)
        if speed > 25:
            seq = a["run"] if speed > 170 else a["walk"]
            return seq[int(t * (5 + 9 * speed / 230)) % len(seq)]
        return a["idle"][int(t * 4) % len(a["idle"])]

    def update_sprite(self):
        prog = self.progression
        variant = prog.visual_variant
        right, left = self.textures[variant]
        self.sprite.texture = (right if self.facing > 0 else left)[self._frame(self.variant_anims[variant])]
        sx, sy = prog.visual_scale
        self.sprite.scale = (sx, sy)
        tremble = math.sin(self.anim_time * 55) * 1.2 if prog.aging_stage == 2 and not self.dead else 0.0
        self.sprite.center_x = self.body.center_x + tremble
        self.sprite.center_y = self.body.y + (self.cell_h / 2 - self.foot) * sy
        self.sprite.color = AGING_TINT[prog.aging_stage]
        blink = self.invuln > 0 and not self.dead and int(self.invuln * 14) % 2 == 0
        self.sprite.alpha = 80 if blink else 255
