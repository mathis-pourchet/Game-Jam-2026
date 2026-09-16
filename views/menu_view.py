"""Menu principal : titre, meilleur score, règles et commandes."""
import math

import arcade

from entities import assets
from settings import (COLOR_GOLD, COLOR_PINK, FONT_TITLE, KEYS_CONFIRM, KEYS_DOWN, KEYS_UP, SCREEN_HEIGHT,
                      SCREEN_WIDTH, TILE)
from systems.score_system import ScoreSystem
from views import screen
from views.background import Background
from views.ui import OutlinedText, panel

HELP = (
    "BUT : traverser la Terre de Ooo jusqu'au bout de la route, et terrasser ce qui t'y attend.\n\n"
    "COMMANDES : Flèches / QD / AD pour bouger, ESPACE (ou Haut / Z / W) pour sauter, "
    "J / X / K pour l'épée, Haut / Bas sur une échelle, Bas + Saut pour traverser une plateforme, "
    "Échap pour la pause, M pour le son.\n\n"
    "ET SI TU TOMBES ? Ici, tomber n'est pas la fin. Quelque chose se perd, quelque chose se gagne : "
    "tous les adversaires ne te reprennent pas la même chose, et certains laissent derrière eux "
    "bien plus qu'un cadavre.\n\n"
    "Mais le temps, lui, ne rend jamais ce qu'il prend. Et il finit toujours par présenter l'addition."
)


class MenuView(arcade.View):
    OPTIONS = ["Jouer", "Comment jouer", "Quitter"]

    def __init__(self):
        super().__init__()
        self.time = 0.0
        self.selected = 0
        self.show_help = False
        self.background = Background()
        self.camera = screen.make_camera()
        cx = SCREEN_WIDTH / 2
        self.title = OutlinedText("THE FINNING", cx, SCREEN_HEIGHT - 170, color=COLOR_GOLD, size=96, thickness=7)
        self.subtitle = OutlinedText("Meurs. Renais. Deviens légendaire.", cx, SCREEN_HEIGHT - 222,
                                     color=COLOR_PINK, size=28)
        self.options = [OutlinedText(label, cx, 330 - i * 58, size=36) for i, label in enumerate(self.OPTIONS)]
        best = ScoreSystem().load_best(1)
        best_txt = f"Record : {best['score']} pts  ({best['deaths']} morts)" if best else "Aucun record pour l'instant"
        self.best = OutlinedText(best_txt, cx, 128, size=18, thickness=2)
        self.hint = OutlinedText("Haut / Bas + ENTRÉE", cx, 96, size=15, thickness=2, color=(230, 230, 240))
        self.help_title = OutlinedText("Comment jouer", cx, SCREEN_HEIGHT - 110, color=COLOR_GOLD, size=44)
        self.help_text = arcade.Text(HELP, cx - 430, SCREEN_HEIGHT - 160, (255, 255, 255), 17, width=860,
                                     multiline=True, font_name=FONT_TITLE, anchor_y="top")
        self.help_hint = OutlinedText("ENTRÉE ou ÉCHAP pour revenir", cx, 60, size=16, thickness=2)
        meta = assets.meta("finn.json")
        cw, ch = meta["cell"]
        info = meta["variants"]["muscle1"]
        right, _ = assets.frames("finn_muscle1.png", cw, ch, info["count"])
        self.finn_run = [right[i] for i in info["anims"]["run"]]
        self.finn_size = (cw * 1.5, ch * 1.5)
        self.jake = assets.frames("jake.png", 30, 26, 4)[0]
        zombie = assets.meta("monsters.json")["zombie"]
        self.zombie_size = zombie["cell"]
        _, zleft = assets.frames(zombie["file"], *zombie["cell"], zombie["count"])
        self.zombie = [zleft[i] for i in zombie["anims"]["walk"]]
        self.grass = assets.tileset("grass_mid")
        self.dirt = assets.tileset("dirt_mid")

    def on_show_view(self):
        screen.set_mouse(self.window, True)
        self.window.audio.play_music("music_menu")

    def on_update(self, delta_time):
        self.time += delta_time

    def activate(self):
        choice = self.OPTIONS[self.selected]
        self.window.audio.play("select")
        if choice == "Jouer":
            from views.level_select_view import LevelSelectView
            self.window.show_view(LevelSelectView())
        elif choice == "Comment jouer":
            self.show_help = True
        else:
            arcade.exit()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.M:
            self.window.audio.toggle_mute()
            return
        if self.show_help:
            if key in KEYS_CONFIRM or key == arcade.key.ESCAPE:
                self.show_help = False
            return
        if key in KEYS_UP:
            self.selected = (self.selected - 1) % len(self.OPTIONS)
            self.window.audio.play("menu_move")
        elif key in KEYS_DOWN:
            self.selected = (self.selected + 1) % len(self.OPTIONS)
            self.window.audio.play("menu_move")
        elif key in KEYS_CONFIRM:
            self.activate()
        elif key == arcade.key.ESCAPE:
            arcade.exit()

    def on_mouse_motion(self, x, y, dx, dy):
        x, y = screen.to_logical(self.camera, x, y)
        for i, option in enumerate(self.options):
            if abs(y - option.main.y - 14) < 26 and abs(x - SCREEN_WIDTH / 2) < 180:
                self.selected = i

    def on_mouse_press(self, x, y, button, modifiers):
        if self.show_help:
            self.show_help = False
            return
        x, y = screen.to_logical(self.camera, x, y)
        for i, option in enumerate(self.options):
            if abs(y - option.main.y - 14) < 26 and abs(x - SCREEN_WIDTH / 2) < 180:
                self.selected = i
                self.activate()

    def on_draw(self):
        screen.begin_frame(self, self.camera)
        self.background.draw(self.time * 70, SCREEN_HEIGHT / 2, self.time)
        offset = -(self.time * 70) % TILE
        for i in range(-1, SCREEN_WIDTH // TILE + 2):
            x = i * TILE + offset
            arcade.draw_texture_rect(self.grass, arcade.LBWH(x, 32, TILE, TILE), pixelated=True)
            arcade.draw_texture_rect(self.dirt, arcade.LBWH(x, 0, TILE, TILE), pixelated=True)
        if self.show_help:
            panel(SCREEN_WIDTH / 2 - 460, SCREEN_WIDTH / 2 + 460, 90, SCREEN_HEIGHT - 60, fill=(30, 22, 48, 235))
            self.help_title.draw()
            self.help_text.draw()
            self.help_hint.draw()
            return
        bob = math.sin(self.time * 2) * 6
        self.title.set_position(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 170 + bob)
        self.title.draw()
        self.subtitle.draw()
        for i, option in enumerate(self.options):
            chosen = i == self.selected
            option.set_color(COLOR_GOLD if chosen else (255, 255, 255))
            option.text = f"> {self.OPTIONS[i]} <" if chosen else self.OPTIONS[i]
            option.draw()
        self.best.draw()
        self.hint.draw()
        finn = self.finn_run[int(self.time * 12) % len(self.finn_run)]
        fw, fh = self.finn_size
        arcade.draw_texture_rect(finn, arcade.XYWH(250, 64 + fh / 2 - 3, fw, fh), pixelated=True)
        jake = self.jake[int(self.time * 6) % 2]
        arcade.draw_texture_rect(jake, arcade.XYWH(150, 64 + 26, 60, 52), pixelated=True)
        zx = SCREEN_WIDTH - ((self.time * 60) % (SCREEN_WIDTH + 200)) + 100
        zombie = self.zombie[int(self.time * 10) % len(self.zombie)]
        zw, zh = self.zombie_size
        arcade.draw_texture_rect(zombie, arcade.XYWH(zx, 64 + zh / 2 - 2, zw, zh))
