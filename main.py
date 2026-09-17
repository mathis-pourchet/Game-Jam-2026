"""The Finning - jeu de plateforme (Game Jam 2026).

Lancer : .venv/bin/python main.py
Options de test : --col N (démarrer à la colonne N de la map), --boss (devant l'arène),
--level 2 (niveau visé par --col / --boss), --fenetre (sans plein écran)
"""
import argparse

import pyglet

# Avant tout import d'arcade : sinon pyglet vérifie les erreurs OpenGL après CHAQUE appel
# (plus d'un million de vérifications en 15 s de jeu, ~1 ms perdue par image).
pyglet.options.debug_gl = False

import arcade  # noqa: E402

from settings import FONTS, FULLSCREEN, SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from systems.audio_manager import AudioManager


def main():
    parser = argparse.ArgumentParser(description=SCREEN_TITLE)
    parser.add_argument("--col", type=int, default=None, help="démarrer à cette colonne de la map (test)")
    parser.add_argument("--boss", action="store_true", help="démarrer devant l'arène du boss (test)")
    parser.add_argument("--level", type=int, default=1, help="niveau à lancer avec --col / --boss (1 ou 2)")
    parser.add_argument("--fenetre", action="store_true", help="jouer dans une fenêtre plutôt qu'en plein écran")
    args = parser.parse_args()

    arcade.load_font(FONTS / "LuckiestGuy-Regular.ttf")     # la seule police du jeu
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=FULLSCREEN and not args.fenetre,
                           vsync=True)
    window.audio = AudioManager()

    if args.col is not None or args.boss:
        from views.game_view import GameView
        index = max(0, args.level - 1)
        boss_col = {0: 268, 1: 186}.get(index, 268)
        window.show_view(GameView(level_index=index, start_col=boss_col if args.boss else args.col))
    else:
        from views.menu_view import MenuView
        window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()
