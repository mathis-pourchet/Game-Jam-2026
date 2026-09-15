"""Sons et musiques. Un fichier manquant est ignoré silencieusement."""
import time

import arcade

from settings import SOUNDS


class AudioManager:
    SFX_VOLUME = 0.6
    MUSIC_VOLUME = 0.35

    def __init__(self):
        self._cache = {}
        self._last_played = {}
        self._music_player = None
        self.current_music = None
        self.muted = False

    def _load(self, name):
        if name not in self._cache:
            path = SOUNDS / f"{name}.wav"
            try:
                self._cache[name] = arcade.load_sound(path) if path.exists() else None
            except Exception as exc:  # fichier illisible : on joue sans ce son
                print(f"[audio] {name} ignoré : {exc}")
                self._cache[name] = None
        return self._cache[name]

    def play(self, name, volume=1.0, speed=1.0, min_interval=0.04):
        if self.muted:
            return
        now = time.monotonic()
        if now - self._last_played.get(name, 0) < min_interval:
            return
        self._last_played[name] = now
        sound = self._load(name)
        if sound:
            arcade.play_sound(sound, volume=self.SFX_VOLUME * volume, speed=speed)

    def play_music(self, name, volume=1.0):
        if self.current_music == name and self._music_player:
            return
        self.stop_music()
        self.current_music = name
        if self.muted:
            return
        sound = self._load(name)
        if sound:
            self._music_player = arcade.play_sound(sound, volume=self.MUSIC_VOLUME * volume, loop=True)

    def stop_music(self):
        if self._music_player:
            arcade.stop_sound(self._music_player)
        self._music_player = None
        self.current_music = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            music = self.current_music
            self.stop_music()
            self.current_music = music
        elif self.current_music:
            name, self.current_music = self.current_music, None
            self.play_music(name)
        return self.muted
