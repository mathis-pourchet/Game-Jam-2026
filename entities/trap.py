"""Pièges et objets du décor : scies, ressorts, pièces, cœurs, Jake, panneaux, porte."""
import math
import random

import arcade

from entities import assets
from settings import TILE
from systems.level_manager import tileset_textures


class Saw:
    """Scie circulaire qui fait des allers-retours (horizontal ou vertical)."""
    damage = 1

    def __init__(self, x, y, vertical=False, travel=2.5 * TILE):
        self.origin = (x, y)
        self.vertical = vertical
        self.travel = travel
        self.speed = 85 if vertical else 105
        self.sprite = arcade.Sprite(tileset_textures()["saw"], center_x=x, center_y=y)
        self.reset()

    def reset(self):
        self.offset = random.uniform(-self.travel, self.travel)
        self.direction = 1
        self._place()

    def _place(self):
        ox, oy = self.origin
        if self.vertical:
            self.x, self.y = ox, oy + self.offset
        else:
            self.x, self.y = ox + self.offset, oy
        self.sprite.center_x, self.sprite.center_y = self.x, self.y

    def update(self, dt):
        self.offset += self.direction * self.speed * dt
        if abs(self.offset) > self.travel:
            self.offset = math.copysign(self.travel, self.offset)
            self.direction = -self.direction
        self.sprite.angle += 540 * dt
        self._place()

    def box(self):
        return (self.x - 12, self.y - 12, self.x + 12, self.y + 12)


class Spring:
    def __init__(self, x, bottom):
        self.x, self.bottom = x, bottom
        self.sprite = arcade.Sprite(tileset_textures()["spring"], center_x=x, center_y=bottom + TILE / 2)
        self.squash = 0.0

    def box(self):
        return (self.x - 14, self.bottom, self.x + 14, self.bottom + 20)

    def trigger(self):
        self.squash = 0.18

    def update(self, dt):
        self.squash = max(0.0, self.squash - dt)
        sy = 0.6 if self.squash > 0.08 else 1.0
        self.sprite.scale = (1.0, sy)
        self.sprite.center_y = self.bottom + TILE / 2 * sy


class Coin:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.sprite = arcade.Sprite(tileset_textures()["coin"], center_x=x, center_y=y, scale=0.8)
        self.phase = (x * 0.05) % (2 * math.pi)

    def box(self):
        return (self.x - 10, self.y - 10, self.x + 10, self.y + 10)

    def update(self, t):
        self.sprite.center_y = self.y + math.sin(t * 3 + self.phase) * 3
        self.sprite.scale = (0.8 * max(0.15, abs(math.cos(t * 2.4 + self.phase))), 0.8)


class HeartPickup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.sprite = arcade.Sprite(assets.texture("heart_full.png"), center_x=x, center_y=y, scale=2.4)

    def box(self):
        return (self.x - 12, self.y - 12, self.x + 12, self.y + 12)

    def update(self, t):
        pulse = 2.4 + math.sin(t * 5) * 0.2
        self.sprite.scale = pulse
        self.sprite.center_y = self.y + math.sin(t * 2.5) * 4


class Npc:
    """Jake (ou un panneau) qui donne un conseil quand Finn s'approche."""

    def __init__(self, kind, x, bottom, tip):
        self.kind, self.x, self.bottom, self.tip = kind, x, bottom, tip
        if kind == "jake":
            self.right, self.left = assets.frames("jake.png", 30, 26, 4)
            self.sprite = arcade.Sprite(self.right[0], scale=2)
            self.sprite.center_x, self.sprite.center_y = x, bottom + 26
        else:
            self.sprite = arcade.Sprite(assets.texture("sign.png"), scale=2, center_x=x, center_y=bottom + 16)
        self.talking = False
        self.anim = random.random()

    def update(self, dt, player_x, player_y):
        near = abs(player_x - self.x) < 3.2 * TILE and abs(player_y - self.bottom) < 3 * TILE
        self.talking = near
        self.anim += dt
        if self.kind == "jake":
            frames = self.right if player_x >= self.x else self.left
            if near:
                index = 2 + int(self.anim * 5) % 2
            else:
                index = int(self.anim * 2) % 2
            self.sprite.texture = frames[index]


class Door:
    """Porte de sortie : apparaît quand le Roi Zombie est vaincu."""

    def __init__(self, x, bottom):
        self.x, self.bottom = x, bottom
        self.sprite = arcade.Sprite(tileset_textures()["door"], center_x=x, center_y=bottom + TILE, scale=2)
        self.open = False
        self.sprite.visible = False

    def box(self):
        return (self.x - 20, self.bottom, self.x + 20, self.bottom + 60)

    def set_open(self, value):
        self.open = value
        self.sprite.visible = value
