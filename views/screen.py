"""Plein écran : le jeu est dessiné sur une image logique de 1280x720, agrandie et
centrée dans la fenêtre (bandes noires si l'écran n'est pas en 16:9).

Chaque vue dessine avec une caméra réglée par `fit()` et convertit la souris avec
`to_logical()`. Le curseur est caché pendant l'action, visible en pause et dans les menus.
"""
import arcade
from arcade.types import LRBT

from settings import SCREEN_HEIGHT, SCREEN_WIDTH

ASPECT = SCREEN_WIDTH / SCREEN_HEIGHT


def fit(camera):
    """Cadre la caméra sur la plus grande zone 16:9 centrée de la fenêtre."""
    camera.match_window(viewport=True, projection=False, scissor=False, aspect=ASPECT)
    camera.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)


def make_camera():
    """Caméra d'interface : (0, 0) en bas à gauche de l'image logique."""
    camera = arcade.Camera2D()
    fit(camera)
    camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    return camera


def begin_frame(view, camera):
    """Efface toute la fenêtre (bandes comprises), puis active la caméra 16:9."""
    view.window.default_camera.use()
    view.clear(color=(0, 0, 0))
    fit(camera)
    camera.use()


def to_logical(camera, x, y):
    """Position de la souris dans la fenêtre -> coordonnées de l'image logique 1280x720."""
    vp = camera.viewport
    return (x - vp.left) * SCREEN_WIDTH / vp.width, (y - vp.bottom) * SCREEN_HEIGHT / vp.height


def set_mouse(window, visible):
    """Affiche ou cache le curseur (sans rappeler le système à chaque image)."""
    if getattr(window, "mouse_shown", None) is not visible:
        window.set_mouse_visible(visible)
        window.mouse_shown = visible
