"""Chargement (avec cache) des textures du jeu."""
import json
from functools import lru_cache

import arcade

from settings import SPRITES

BBOX = arcade.hitbox.algo_bounding_box


@lru_cache(maxsize=None)
def texture(name):
    return arcade.load_texture(SPRITES / name, hit_box_algorithm=BBOX)


def tileset(name):
    """Texture d'une tuile du tileset ooo32 (par son nom)."""
    from systems.level_manager import tileset_textures
    return tileset_textures()[name]


@lru_cache(maxsize=None)
def frames(name, cell_w, cell_h, count):
    """Textures d'une bande horizontale : (liste vers la droite, liste vers la gauche)."""
    sheet = arcade.SpriteSheet(SPRITES / name)
    right = sheet.get_texture_grid(size=(cell_w, cell_h), columns=count, count=count, hit_box_algorithm=BBOX)
    return right, [t.flip_left_right() for t in right]


@lru_cache(maxsize=None)
def meta(name):
    with open(SPRITES / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def foot_offset(name, cell_w, cell_h, count):
    """Nombre de pixels transparents sous les pieds (pour poser le sprite au sol)."""
    sheet = arcade.SpriteSheet(SPRITES / name)
    img = sheet.image
    lowest = 0
    for i in range(count):
        bbox = img.crop((i * cell_w, 0, (i + 1) * cell_w, cell_h)).getchannel("A").getbbox()
        if bbox:
            lowest = max(lowest, bbox[3])
    return cell_h - lowest
