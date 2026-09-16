"""Chargement d'une map ASCII (assets/maps/*.txt) et construction des tuiles.

Format : la map est découpée en sections ; chaque section commence par une ligne
« ; » et contient le même nombre de lignes. Les sections sont collées de gauche
à droite. Une case = une tuile de 32 px.

Légende
  .  vide                         #  herbe/terre (auto-tuilée)
  R  roche                        M  maçonnerie du château
  B  brique   G  gomme   C  chocolat (blocs solides)
  I  glace (glissante)            X  bloc fissuré (se casse à l'épée)
  ?  bloc bonus (pièce)           +  bloc bonus (cœur)
  =  plateforme en bois (traversable par dessous)   -  dalle de pierre traversable
  ^  pics   v  pics au plafond   t  ronces   ~  gomme toxique (mortelle)
  o  pièce   h  cœur   S  ressort   H  échelle
  P  départ de Finn   J  Jake (conseil)   !  panneau (conseil)
  z  zombie (monstre niveau 1)   j  zombie qui bondit (niveau 1)
  Z  sorcier squelette (monstre niveau 2, champion : tue = renaissance plus fort)
  K  Roi des Glaces (boss final)   w  scie horizontale   y  scie verticale
  |  grille de l'arène (se ferme derrière Finn)   r  réapparition devant l'arène
  D  porte de sortie (apparaît quand le boss est vaincu)   F  drapeau
  T  arbre   f fleur   m champignon   n gros champignon   c cristal
  g  tombe   b  os   *  torche   ,  touffe d'herbe
"""
import json
from dataclasses import dataclass, field

import arcade

from settings import ASSETS, SPRITES, TILE
from systems.physics import BREAKABLE, EMPTY, ICE, ONEWAY, QBLOCK, SOLID, TileGrid

TERRAIN = {"#", "R", "M"}
BLOCKS = {
    "B": ("blk_brick", SOLID), "G": ("blk_gum", SOLID), "C": ("blk_choco", SOLID),
    "I": ("blk_ice", ICE), "X": ("blk_cracked", BREAKABLE),
    "?": ("qblock", QBLOCK), "+": ("qblock", QBLOCK),
}
PLATFORMS = {"=", "-"}
HAZARDS = {"^": "spikes_up", "v": "spikes_down", "t": "thorns", "~": "goo"}
DECO = {"f": "flower", "m": "mushroom_sm", "n": "mushroom_lg", "c": "crystal", "g": "grave",
        "b": "bones", "*": "torch", ",": "grass_tuft"}
ENTITIES = {"P": "player", "J": "jake", "!": "sign", "z": "zombie", "j": "jumper", "Z": "champion",
            "K": "boss", "o": "coin", "h": "heart", "S": "spring", "w": "saw_h", "y": "saw_v",
            "r": "boss_respawn", "D": "door", "F": "flag"}

# Zones dangereuses dans une tuile (gauche, bas, droite, haut) en pixels relatifs
HAZARD_BOXES = {
    "spikes_up": (4, 0, 28, 14),
    "spikes_down": (4, 18, 28, 32),
    "thorns": (3, 0, 29, 18),
    "goo": (0, 0, 32, 22),
    "goo_body": (0, 0, 32, 32),
}

# Dégâts infligés par chaque piège de la map (le goo tue directement)
HAZARD_DAMAGE = {
    "spikes_up": 25,
    "spikes_down": 25,
    "thorns": 15,
}


@dataclass
class Spawn:
    kind: str
    tx: int
    ty: int
    data: object = None

    @property
    def x(self):
        return self.tx * TILE + TILE / 2

    @property
    def bottom(self):
        return self.ty * TILE


@dataclass
class LevelData:
    width: int
    height: int
    grid: TileGrid
    tiles: list = field(default_factory=list)          # (nom, tx, ty) décor solide/plateformes
    dynamic: dict = field(default_factory=dict)        # (tx, ty) -> {"name", "reward"}
    hazards: dict = field(default_factory=dict)        # (tx, ty) -> type de danger
    ladders: set = field(default_factory=set)
    deco: list = field(default_factory=list)           # (nom, tx, ty)
    spawns: list = field(default_factory=list)
    gate_cells: list = field(default_factory=list)

    @property
    def pixel_width(self):
        return self.width * TILE

    @property
    def pixel_height(self):
        return self.height * TILE

    def spawns_of(self, kind):
        return [s for s in self.spawns if s.kind == kind]

    def spawn(self, kind):
        found = self.spawns_of(kind)
        return found[0] if found else None

    @property
    def gate_x(self):
        return min(tx for tx, _ in self.gate_cells) * TILE if self.gate_cells else None


def read_map(path):
    """Lit le fichier et colle les sections horizontalement. Renvoie les lignes (haut -> bas)."""
    blocks, current = [], None
    with open(path, encoding="utf-8") as f:
        for raw in f.read().splitlines():
            if raw.startswith(";"):
                if current is None or current:
                    current = []
                    blocks.append(current)
                continue
            if raw.strip():
                current.append(raw)
    blocks = [b for b in blocks if b]
    height = max(len(b) for b in blocks)
    rows = []
    for y in range(height):
        parts = []
        for b in blocks:
            width = max(len(line) for line in b)
            line = b[y] if y < len(b) else ""
            parts.append(line.ljust(width, "."))
        rows.append("".join(parts).replace(" ", "."))
    return rows


def _variant(r, c, options):
    return options[(r * 7 + c * 13) % len(options)]


def terrain_tile(rows, r, c):
    ch = rows[r][c]
    height, width = len(rows), len(rows[0])

    def same(rr, cc):
        if rr < 0 or rr >= height or cc < 0 or cc >= width:
            return True
        return rows[rr][cc] in TERRAIN if ch in "#R" else rows[rr][cc] == ch

    top_open = not same(r - 1, c)
    bottom_open = not same(r + 1, c)
    left, right = same(r, c - 1), same(r, c + 1)
    edge = "mid" if left and right else "left" if right else "right" if left else "single"
    if ch == "#":
        if top_open:
            return "grass_" + edge if edge != "mid" else _variant(r, c, ["grass_mid", "grass_mid", "grass_mid_b"])
        if bottom_open:
            return "dirt_bottom"
        return {"left": "dirt_left", "right": "dirt_right"}.get(edge, "dirt_mid")
    if ch == "R":
        if top_open:
            if edge == "mid":
                return _variant(r, c, ["grassrock_mid", "grassrock_mid_b", "grassrock_mid_c"])
            return "grassrock_" + edge
        if bottom_open:
            return _variant(r, c, ["rock_bottom", "rock_bottom_b"])
        if edge in ("left", "right"):
            return "rock_" + edge
        return _variant(r, c, ["rock_mid", "rock_mid_b", "rock_mid_c"])
    # maçonnerie : dessus en dalles, corps en briques de pierre
    if top_open:
        if edge == "mid":
            return _variant(r, c, ["path_mid", "path_mid_b", "path_mid_c"])
        return "path_" + edge
    return {"left": "masonry_left", "right": "masonry_right"}.get(edge, "masonry_mid")


def parse_level(rows):
    height, width = len(rows), len(rows[0])
    level = LevelData(width, height, TileGrid(width, height))
    tips = 0
    for r in range(height):
        ty = height - 1 - r
        for c in range(width):
            ch = rows[r][c]
            above = rows[r - 1][c] if r > 0 else "."
            if ch in TERRAIN:
                level.grid.set(c, ty, SOLID)
                level.tiles.append((terrain_tile(rows, r, c), c, ty))
            elif ch in BLOCKS:
                name, kind = BLOCKS[ch]
                level.grid.set(c, ty, kind)
                if kind in (BREAKABLE, QBLOCK):
                    level.dynamic[(c, ty)] = {"name": name, "reward": "heart" if ch == "+" else "coin"}
                else:
                    level.tiles.append((name, c, ty))
            elif ch in PLATFORMS:
                level.grid.set(c, ty, ONEWAY)
                if ch == "-":
                    level.tiles.append(("path_slab", c, ty))
                else:
                    left = c > 0 and rows[r][c - 1] == "="
                    right = c < width - 1 and rows[r][c + 1] == "="
                    level.tiles.append(("plat_mid" if left and right else "plat_right" if left else
                                        "plat_left" if right else "plat_mid", c, ty))
            elif ch in HAZARDS:
                kind = HAZARDS[ch]
                if kind == "goo" and above == "~":
                    kind = "goo_body"
                level.hazards[(c, ty)] = kind
                level.tiles.append(({"goo": "goo_top", "goo_body": "goo_body"}.get(kind, kind), c, ty))
            elif ch == "H":
                level.ladders.add((c, ty))
                level.tiles.append(("ladder", c, ty))
                if above != "H":
                    level.grid.set(c, ty, ONEWAY)   # on peut se tenir en haut de l'échelle
            elif ch == "|":
                level.gate_cells.append((c, ty))
            elif ch in DECO:
                level.deco.append((DECO[ch], c, ty))
            elif ch == "T":
                level.deco.append(("trunk", c, ty))
                level.deco.append(("canopy", c, ty + 1))
            elif ch in ENTITIES:
                kind = ENTITIES[ch]
                data = None
                if kind in ("jake", "sign"):
                    data = None  # numéroté plus bas, de gauche à droite
                level.spawns.append(Spawn(kind, c, ty, data))
                if kind == "flag":
                    level.deco += [("checkpoint_base", c, ty), ("checkpoint_pole", c, ty + 1),
                                   ("checkpoint_top", c, ty + 2)]
    for spawn in sorted((s for s in level.spawns if s.kind in ("jake", "sign")), key=lambda s: s.tx):
        spawn.data = tips
        tips += 1
    return level


def load_level(path):
    return parse_level(read_map(path))


# --------------------------------------------------------------------------
# Construction des sprites
# --------------------------------------------------------------------------
_TILESET = None


def tileset_textures():
    """Dictionnaire nom -> texture pour le tileset ooo32."""
    global _TILESET
    if _TILESET is None:
        with open(ASSETS / "tilesets" / "tileset32_map.json", encoding="utf-8") as f:
            meta = json.load(f)
        sheet = arcade.SpriteSheet(ASSETS / "tilesets" / "tileset_32x32.png")
        textures = sheet.get_texture_grid(size=(TILE, TILE), columns=meta["columns"],
                                          count=meta["columns"] * meta["rows"],
                                          hit_box_algorithm=arcade.hitbox.algo_bounding_box)
        _TILESET = {t["name"]: textures[t["id"]] for t in meta["tiles"]}
    return _TILESET


def tile_sprite(name, tx, ty):
    return arcade.Sprite(tileset_textures()[name], center_x=tx * TILE + TILE / 2, center_y=ty * TILE + TILE / 2)


class LevelSprites:
    """Sprites statiques et dynamiques d'un niveau (reconstruits à chaque réinitialisation)."""

    def __init__(self, level):
        self.terrain = arcade.SpriteList(use_spatial_hash=False)
        self.deco = arcade.SpriteList()
        self.dynamic = arcade.SpriteList()
        self.gate = arcade.SpriteList()
        self.dynamic_by_cell = {}
        for name, tx, ty in level.tiles:
            self.terrain.append(tile_sprite(name, tx, ty))
        for name, tx, ty in level.deco:
            self.deco.append(tile_sprite(name, tx, ty))
        gate_tex = arcade.load_texture(SPRITES / "gate.png")
        for tx, ty in level.gate_cells:
            self.gate.append(arcade.Sprite(gate_tex, scale=2, center_x=tx * TILE + TILE / 2,
                                           center_y=ty * TILE + TILE / 2))
        self.gate.visible = False
        self.reset_dynamic(level)

    def reset_dynamic(self, level):
        self.dynamic.clear()
        self.dynamic_by_cell = {}
        for (tx, ty), info in level.dynamic.items():
            sprite = tile_sprite(info["name"], tx, ty)
            self.dynamic.append(sprite)
            self.dynamic_by_cell[(tx, ty)] = sprite
            level.grid.set(tx, ty, BREAKABLE if info["name"] == "blk_cracked" else QBLOCK)

    def remove_block(self, level, cell):
        sprite = self.dynamic_by_cell.pop(cell, None)
        if sprite:
            sprite.remove_from_sprite_lists()
        level.grid.set(*cell, EMPTY)

    def use_qblock(self, cell):
        sprite = self.dynamic_by_cell.get(cell)
        if sprite:
            sprite.color = (150, 120, 110)
