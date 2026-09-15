"""Physique de plateforme sur grille de tuiles (collisions AABB, plateformes traversables)."""
import math

from settings import TILE

EMPTY, SOLID, ONEWAY, ICE, BREAKABLE, QBLOCK, USED, GATE = range(8)
BLOCKING = {SOLID, ICE, BREAKABLE, QBLOCK, USED, GATE}


class Body:
    """Boîte de collision : (x, y) = coin bas-gauche, en pixels monde (y vers le haut)."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.on_ice = False
        self.hit_wall = 0
        self.hit_ceiling = None
        self.drop_through = 0.0

    @property
    def center_x(self):
        return self.x + self.w / 2

    @property
    def center_y(self):
        return self.y + self.h / 2

    @property
    def top(self):
        return self.y + self.h

    @property
    def right(self):
        return self.x + self.w

    def place_center_bottom(self, cx, bottom):
        self.x = cx - self.w / 2
        self.y = bottom

    def overlaps(self, l, b, r, t):
        return self.x < r and self.right > l and self.y < t and self.top > b


def rects_overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


class TileGrid:
    """Grille de collision. Les bords gauche/droit de la map sont des murs ; le bas est un vide mortel."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cells = [[EMPTY] * width for _ in range(height)]

    def get(self, tx, ty):
        if tx < 0 or tx >= self.width:
            return SOLID
        if ty < 0 or ty >= self.height:
            return EMPTY
        return self.cells[ty][tx]

    def set(self, tx, ty, value):
        if 0 <= tx < self.width and 0 <= ty < self.height:
            self.cells[ty][tx] = value

    def blocking(self, tx, ty):
        return self.get(tx, ty) in BLOCKING

    def standable(self, tx, ty):
        return self.get(tx, ty) in BLOCKING or self.get(tx, ty) == ONEWAY


def tile_range(a, b):
    return range(math.floor(a / TILE), math.floor(b / TILE) + 1)


def move_body(body, grid, dt, oneway=True):
    """Déplace un corps et résout les collisions (d'abord X, puis Y)."""
    # --- axe X ---
    body.x += body.vx * dt
    body.hit_wall = 0
    rows = tile_range(body.y + 1, body.top - 1)
    if body.vx > 0:
        tx = math.floor((body.right - 0.001) / TILE)
        if any(grid.blocking(tx, ty) for ty in rows):
            body.x = tx * TILE - body.w
            body.vx = 0
            body.hit_wall = 1
    elif body.vx < 0:
        tx = math.floor(body.x / TILE)
        if any(grid.blocking(tx, ty) for ty in rows):
            body.x = (tx + 1) * TILE
            body.vx = 0
            body.hit_wall = -1

    # --- axe Y ---
    prev_bottom = body.y
    body.y += body.vy * dt
    body.on_ground = False
    body.on_ice = False
    body.hit_ceiling = None
    cols = list(tile_range(body.x + 1, body.right - 1))
    if body.vy <= 0:
        ty = math.floor(body.y / TILE)
        tile_top = (ty + 1) * TILE
        for tx in cols:
            cell = grid.get(tx, ty)
            landing = cell in BLOCKING or (
                cell == ONEWAY and oneway and body.drop_through <= 0 and prev_bottom >= tile_top - 0.5)
            if landing:
                body.y = tile_top
                body.vy = 0
                body.on_ground = True
                if cell == ICE:
                    body.on_ice = True
        if body.on_ground and not body.on_ice:
            body.on_ice = all(grid.get(tx, ty) in (ICE, EMPTY) for tx in cols) and any(
                grid.get(tx, ty) == ICE for tx in cols)
    else:
        ty = math.floor((body.top - 0.001) / TILE)
        hits = [tx for tx in cols if grid.blocking(tx, ty)]
        if hits:
            body.y = ty * TILE - body.h
            body.vy = 0
            best = min(hits, key=lambda tx: abs((tx + 0.5) * TILE - body.center_x))
            body.hit_ceiling = (best, ty)
    if body.drop_through > 0:
        body.drop_through -= dt


def ground_ahead(body, grid, direction):
    """Y a-t-il du sol devant les pieds (pour que les zombies ne tombent pas) ?"""
    x = body.right + 2 if direction > 0 else body.x - 2
    return grid.standable(math.floor(x / TILE), math.floor((body.y - 2) / TILE))


def wall_ahead(body, grid, direction):
    x = body.right + 2 if direction > 0 else body.x - 2
    return any(grid.blocking(math.floor(x / TILE), ty) for ty in tile_range(body.y + 1, body.top - 1))
