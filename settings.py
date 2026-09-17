"""Constantes globales du jeu « The Finning »."""
from pathlib import Path

import arcade

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SPRITES = ASSETS / "sprites"
SOUNDS = ASSETS / "sounds"
FONTS = ASSETS / "fonts"
CONFIG = ROOT / "config"
SAVES = ROOT / "saves"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "The Finning"
FULLSCREEN = False       # image logique 1280x720 agrandie et centrée (voir views/screen.py)

TILE = 32

# --- Physique (pixels, secondes) ---
FIXED_DT = 1 / 120
GRAVITY = 2100
MAX_FALL_SPEED = 950
GROUND_ACCEL = 2600
AIR_ACCEL = 1600
GROUND_FRICTION = 2800
ICE_ACCEL = 650
ICE_FRICTION = 220
COYOTE_TIME = 0.1
JUMP_BUFFER = 0.13
JUMP_CUT = 0.45
LADDER_SPEED = 160
SPRING_VELOCITY = 1180
STOMP_BOUNCE = 560

# --- Joueur ---
PLAYER_W = 22
PLAYER_H = 46
INVULN_TIME = 1.3
KNOCKBACK_X = 260
KNOCKBACK_Y = 420
ATTACK_TIME = 0.26
ATTACK_COOLDOWN = 0.34
ATTACK_REACH = 34
ATTACK_REACH_PER_FORCE = 7
HEART_HEAL = 35          # PV rendus par un cœur ramassé

# --- Mort et renaissance ---
SPECIAL_DEATH_WINDOW = 5.0   # s : un champion ou le boss qui a touché Finn juste avant sa mort compte comme tueur
RESPAWN_BACK_TILES = 3       # Finn renaît au moins à 3 cases du lieu de sa mort

# --- Police : une seule pour tout le jeu (celle de l'écran d'accueil) ---
FONT_TITLE = "Luckiest Guy"

# --- Couleurs ---
COLOR_TEXT = (255, 255, 255)
COLOR_OUTLINE = (27, 20, 38)
COLOR_GOLD = (255, 214, 60)
COLOR_PINK = (255, 120, 190)
COLOR_PURPLE = (150, 90, 220)
COLOR_SKY_TOP = (96, 180, 255)
COLOR_PANEL = (30, 22, 48, 225)

# --- Commandes (QWERTY + AZERTY) ---
KEYS_LEFT = {arcade.key.LEFT, arcade.key.A, arcade.key.Q}
KEYS_RIGHT = {arcade.key.RIGHT, arcade.key.D}
KEYS_UP = {arcade.key.UP, arcade.key.W, arcade.key.Z}
KEYS_DOWN = {arcade.key.DOWN, arcade.key.S}
KEYS_JUMP = {arcade.key.SPACE, arcade.key.UP, arcade.key.W, arcade.key.Z}
KEYS_ATTACK = {arcade.key.J, arcade.key.X, arcade.key.K}
KEYS_CONFIRM = {arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE}
KEYS_PAUSE = {arcade.key.ESCAPE, arcade.key.P}
