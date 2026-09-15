"""Particules, textes flottants et tremblement d'écran."""
import math
import random

import arcade

from entities import assets
from settings import COLOR_OUTLINE, FONT_TITLE


class Particle:
    __slots__ = ("sprite", "vx", "vy", "life", "max_life", "gravity", "drag", "base_scale")


class Effects:
    def __init__(self, ctx):
        self.ctx = ctx
        self.normal = arcade.SpriteList()
        self.glow = arcade.SpriteList()
        self.particles = []
        self.texts = []
        self.shake_time = 0.0
        self.shake_amount = 0.0

    def clear(self):
        for p in self.particles:
            p.sprite.remove_from_sprite_lists()
        self.particles = []
        self.texts = []

    def emit(self, x, y, color, count=10, speed=(80, 260), angle=(0, 360), life=(0.3, 0.7),
             gravity=900, size=(2.0, 4.0), glow=False, texture=None, drag=0.0):
        tex = texture or assets.texture("spark.png")
        target = self.glow if glow else self.normal
        for _ in range(count):
            a = math.radians(random.uniform(*angle))
            v = random.uniform(*speed)
            s = arcade.Sprite(tex, scale=random.uniform(*size), center_x=x, center_y=y)
            s.color = color
            p = Particle()
            p.sprite, p.vx, p.vy = s, math.cos(a) * v, math.sin(a) * v
            p.life = p.max_life = random.uniform(*life)
            p.gravity, p.drag, p.base_scale = gravity, drag, s.scale_x
            target.append(s)
            self.particles.append(p)

    def dust(self, x, y):
        self.emit(x, y, (240, 230, 215), 8, speed=(40, 140), angle=(15, 165), life=(0.2, 0.4), gravity=250, size=(2, 3))

    def hit(self, x, y):
        self.emit(x, y, (255, 255, 230), 12, speed=(140, 360), life=(0.1, 0.28), gravity=0, glow=True, size=(2, 4))

    def burst(self, x, y, color, count=24):
        self.emit(x, y, color, count, speed=(120, 420), life=(0.4, 0.9), gravity=700, size=(2.5, 5))

    def pop_coin(self, x, y):
        self.emit(x, y, (255, 255, 255), 1, speed=(420, 420), angle=(90, 90), life=(0.45, 0.45),
                  gravity=1400, size=(0.8, 0.8), texture=assets.tileset("coin"))

    def float_text(self, x, y, text, color=(255, 255, 255), size=16):
        shadow = arcade.Text(text, x + 2, y - 2, COLOR_OUTLINE, size, anchor_x="center", font_name=FONT_TITLE)
        main = arcade.Text(text, x, y, color, size, anchor_x="center", font_name=FONT_TITLE)
        self.texts.append([shadow, main, 1.1, color])

    def shake(self, amount, duration):
        self.shake_amount = max(self.shake_amount, amount)
        self.shake_time = max(self.shake_time, duration)

    def offset(self):
        if self.shake_time <= 0:
            return 0.0, 0.0
        a = self.shake_amount
        return random.uniform(-a, a), random.uniform(-a, a)

    def update(self, dt):
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                p.sprite.remove_from_sprite_lists()
                continue
            p.vy -= p.gravity * dt
            if p.drag:
                p.vx *= 1 - p.drag * dt
                p.vy *= 1 - p.drag * dt
            s = p.sprite
            s.center_x += p.vx * dt
            s.center_y += p.vy * dt
            ratio = p.life / p.max_life
            s.alpha = int(255 * min(1.0, ratio * 1.6))
            alive.append(p)
        self.particles = alive
        for entry in self.texts:
            entry[2] -= dt
            for t in entry[:2]:
                t.y += 45 * dt
            alpha = int(255 * max(0.0, min(1.0, entry[2] / 0.4)))
            entry[0].color = COLOR_OUTLINE + (alpha,)
            entry[1].color = tuple(entry[3][:3]) + (alpha,)
        self.texts = [e for e in self.texts if e[2] > 0]
        if self.shake_time > 0:
            self.shake_time -= dt
            if self.shake_time <= 0:
                self.shake_amount = 0

    def draw(self):
        self.normal.draw(pixelated=True)
        self.glow.draw(blend_function=(self.ctx.SRC_ALPHA, self.ctx.ONE))
        for shadow, main, _, _ in self.texts:
            shadow.draw()
            main.draw()
