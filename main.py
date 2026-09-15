"""Finn sans Fin - jeu de plateforme (Game Jam 2026).

Lancer : .venv/bin/python main.py
Options de test : --col N (démarrer à la colonne N de la map), --boss (devant l'arène)
"""
import argparse

import arcade

from settings import FONTS, SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from systems.audio_manager import AudioManager


def main():
    parser = argparse.ArgumentParser(description=SCREEN_TITLE)
    parser.add_argument("--col", type=int, default=None, help="démarrer à cette colonne de la map (test)")
    parser.add_argument("--boss", action="store_true", help="démarrer devant l'arène du boss (test)")
    args = parser.parse_args()

    arcade.load_font(FONTS / "LuckiestGuy-Regular.ttf")
    arcade.load_font(FONTS / "PressStart2P-Regular.ttf")
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, vsync=True)
    window.audio = AudioManager()

    if args.col is not None or args.boss:
        from views.game_view import GameView
        window.show_view(GameView(start_col=268 if args.boss else args.col))
    else:
        from views.menu_view import MenuView
        window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()
