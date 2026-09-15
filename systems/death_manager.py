"""Gestion des morts : compteur, tombes, point de réapparition.

Règles :
- mort « normale » (zombie normal, piège, chute) hors zone de boss : retour au
  début de la map, qui est réinitialisée ;
- mort face à un champion : Finn renaît sur place, plus fort ;
- mort dans la zone du boss : Finn réapparaît devant la grille de l'arène ;
- au-delà du nombre de morts autorisé : game over, tout est réinitialisé.
"""
from dataclasses import dataclass


class DeathCause:
    NORMAL = "normal"
    CHAMPION = "champion"
    BOSS = "boss"


class Respawn:
    START = "start"
    HERE = "here"
    BOSS_GATE = "boss_gate"


@dataclass
class DeathOutcome:
    cause: str
    deaths: int
    max_deaths: int
    respawn: str
    game_over: bool = False
    offer_upgrade: bool = False
    stat_lost: str | None = None
    aging_stage: int = 0
    became_older: bool = False

    @property
    def special(self):
        return self.cause in (DeathCause.CHAMPION, DeathCause.BOSS)


class DeathManager:
    def __init__(self, progression, max_deaths):
        self.progression = progression
        self.max_deaths = max_deaths
        self.graves = []

    def reset(self):
        self.graves = []

    @property
    def deaths(self):
        return self.progression.deaths

    @property
    def lives_left(self):
        return self.max_deaths - self.deaths

    def handle_death(self, cause, position, in_boss_zone):
        prog = self.progression
        stage_before = prog.aging_stage
        prog.register_death()
        self.graves.append((position[0], position[1], prog.deaths))

        if in_boss_zone:
            respawn = Respawn.BOSS_GATE
        elif cause == DeathCause.CHAMPION:
            respawn = Respawn.HERE
        else:
            respawn = Respawn.START
        outcome = DeathOutcome(cause=cause, deaths=prog.deaths, max_deaths=self.max_deaths,
                               respawn=respawn, aging_stage=prog.aging_stage,
                               became_older=prog.aging_stage > stage_before)
        if prog.deaths >= self.max_deaths:
            outcome.game_over = True
        elif prog.is_aging:
            outcome.stat_lost = prog.apply_aging()
        elif outcome.special and prog.upgradable():
            outcome.offer_upgrade = True
        return outcome
