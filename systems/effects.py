"""Particules et tremblement d'écran.

Les particules sont recyclées : une particule morte est cachée et remise en réserve au lieu
d'être détruite, puis réutilisée par la prochaine émission. Créer et retirer un sprite à
chaque étincelle (des centaines par seconde quand Finn est très fort) coûtait cher.
"""
import math
import random

import arcade

from entities import assets


class Particle:
    __slots__ = ("sprite", "pool", "x", "y", "vx", "vy", "life", "max_life", "gravity", "drag")


class Effects:
    def __init__(self, ctx):
        self.ctx = ctx
        self.normal = arcade.SpriteList()
        self.glow = arcade.SpriteList()
        self.free_normal = []
        self.free_glow = []
        self.particles = []
        self.shake_time = 0.0
        self.shake_amount = 0.0

    def clear(self):
        for p in self.particles:
            p.sprite.visible = False
            p.pool.append(p)
        self.particles = []

    def emit(self, x, y, color, count=10, speed=(80, 260), angle=(0, 360), life=(0.3, 0.7),
             gravity=900, size=(2.0, 4.0), glow=False, texture=None, drag=0.0):
        tex = texture or assets.texture("spark.png")
        target, pool = (self.glow, self.free_glow) if glow else (self.normal, self.free_normal)
        color = (color[0], color[1], color[2], 255)
        for _ in range(count):
            if pool:
                p = pool.pop()
                s = p.sprite
                if s.texture is not tex:
                    s.texture = tex
                s.visible = True
            else:
                p = Particle()
                s = p.sprite = arcade.Sprite(tex)
                p.pool = pool
                target.append(s)
            a = math.radians(random.uniform(*angle))
            v = random.uniform(*speed)
            s.scale = random.uniform(*size)
            s.color = color
            s.position = (x, y)
            p.x, p.y = x, y
            p.vx, p.vy = math.cos(a) * v, math.sin(a) * v
            p.life = p.max_life = random.uniform(*life)
            p.gravity, p.drag = gravity, drag
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
            s = p.sprite
            if p.life <= 0:
                s.visible = False
                p.pool.append(p)
                continue
            p.vy -= p.gravity * dt
            if p.drag:
                p.vx *= 1 - p.drag * dt
                p.vy *= 1 - p.drag * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            s.position = (p.x, p.y)
            s.alpha = int(255 * min(1.0, p.life / p.max_life * 1.6))
            alive.append(p)
        self.particles = alive
        if self.shake_time > 0:
            self.shake_time -= dt
            if self.shake_time <= 0:
                self.shake_amount = 0

    def draw(self):
        self.normal.draw(pixelated=True)
        self.glow.draw(blend_function=(self.ctx.SRC_ALPHA, self.ctx.ONE))
