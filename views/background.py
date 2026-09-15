"""Décor en parallaxe : ciel, montagnes et château lointains, nuages, collines."""
import random

import arcade

from entities import assets
from settings import SCREEN_HEIGHT, SCREEN_WIDTH


def _lerp_color(a, b, t):
    return arcade.types.Color(*(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))


class Background:
    def __init__(self):
        self.sky_day = assets.texture("sky_day.png")
        self.sky_dusk = assets.texture("sky_dusk.png")
        self.far = assets.texture("bg_far.png")
        self.near = assets.texture("bg_near.png")
        self.cloud = assets.texture("cloud.png")
        rng = random.Random(3)
        self.clouds = [(rng.uniform(0, SCREEN_WIDTH + 300), rng.uniform(430, 660), rng.uniform(6, 16),
                        rng.uniform(2.0, 3.4)) for _ in range(7)]

    def draw(self, cam_x, cam_y, t, dusk=0.0, cave=0.0):
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        full = arcade.LBWH(0, 0, w, h)
        arcade.draw_texture_rect(self.sky_day, full)
        if dusk > 0:
            arcade.draw_texture_rect(self.sky_dusk, full, alpha=int(255 * dusk))
        dy = cam_y - h / 2

        far_tint = _lerp_color((255, 255, 255), (150, 110, 170), dusk)
        fw, fh = self.far.width * 2, self.far.height * 2
        x = -((cam_x * 0.12) % fw)
        while x < w:
            arcade.draw_texture_rect(self.far, arcade.LBWH(x, 150 - dy * 0.08, fw, fh), color=far_tint, pixelated=True)
            x += fw

        cloud_tint = _lerp_color((255, 255, 255), (255, 180, 200), dusk)
        span = w + 300
        for cx, cy, speed, scale in self.clouds:
            px = (cx + t * speed - cam_x * 0.2) % span - 150
            cw, ch = self.cloud.width * scale, self.cloud.height * scale
            arcade.draw_texture_rect(self.cloud, arcade.LBWH(px, cy - dy * 0.1, cw, ch), color=cloud_tint,
                                     pixelated=True)

        near_tint = _lerp_color((255, 255, 255), (120, 95, 140), dusk)
        nw, nh = self.near.width * 2, self.near.height * 2
        x = -((cam_x * 0.32) % nw)
        while x < w:
            arcade.draw_texture_rect(self.near, arcade.LBWH(x, -20 - dy * 0.22, nw, nh), color=near_tint,
                                     pixelated=True)
            x += nw

        if cave > 0:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (28, 14, 40, int(205 * cave)))
