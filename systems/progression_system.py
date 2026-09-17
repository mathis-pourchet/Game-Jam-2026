"""Progression par la mort (façon Sifu) : stats, renaissances et vieillissement.

- Mourir face à un CHAMPION ou au BOSS propose de choisir une stat à améliorer.
- À partir d'un certain nombre de morts, Finn vieillit : il perd des niveaux et
  ses stats de base baissent (vitesse, saut).
"""
import json
import random

from settings import ATTACK_REACH, ATTACK_REACH_PER_FORCE, CONFIG, TILE

STAT_ORDER = ["jump", "speed", "force", "resistance"]

# Taille d'affichage de Finn (la boîte de collision, elle, ne change pas) : il grossit
# nettement avec ses muscles, et se tasse en vieillissant.
VARIANT_SCALE = {
    "muscle1": (1.0, 1.0),
    "muscle2": (1.15, 1.15),
    "muscle3": (1.3, 1.3),
    "muscle4": (1.45, 1.45),
    "old1": (0.96, 0.86),
    "old2": (0.92, 0.74),
}
GROWTH_PER_EXTRA_POWER = 0.015   # continue de grossir après le niveau de muscles 4...
MAX_EXTRA_GROWTH = 1.15          # ... jusqu'à +15 %


class ProgressionSystem:
    def __init__(self, config_path=CONFIG / "stats_progression.json"):
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.stats_cfg = cfg["stats"]
        self.choices_per_rebirth = cfg["choices_per_rebirth"]
        self.age_cfg = cfg["age"]
        self.aging_cfg = cfg["aging"]
        self.power_tiers = cfg["power_tiers"]
        self.levels = {}
        self.deaths = 0
        self.reset()

    def reset(self):
        self.levels = {stat: 0 for stat in STAT_ORDER}
        self.deaths = 0

    # ------------------------------------------------------------------
    # Valeurs effectives
    # ------------------------------------------------------------------
    @property
    def aging_stage(self):
        if self.deaths >= self.aging_cfg["very_old_after_deaths"]:
            return 2
        if self.deaths >= self.aging_cfg["old_after_deaths"]:
            return 1
        return 0

    @property
    def is_aging(self):
        return self.aging_stage > 0

    @property
    def age_years(self):
        return self.age_cfg["start"] + self.deaths * self.age_cfg["years_per_death"]

    def value(self, stat):
        cfg = self.stats_cfg[stat]
        return cfg["base"] + cfg["per_level"] * self.levels[stat]

    @property
    def jump_height(self):
        """Hauteur de saut en pixels."""
        return self.value("jump") * TILE * self.aging_cfg["jump_multiplier"][self.aging_stage]

    @property
    def run_speed(self):
        return self.value("speed") * self.aging_cfg["speed_multiplier"][self.aging_stage]

    @property
    def damage(self):
        return int(self.value("force"))

    @property
    def max_hp(self):
        return int(self.value("resistance"))

    @property
    def attack_reach(self):
        return ATTACK_REACH + ATTACK_REACH_PER_FORCE * self.levels["force"]

    @property
    def power(self):
        return sum(self.levels.values())

    @property
    def muscle_level(self):
        """Niveau de muscles de 1 à 4 (planches assets/finn/finn-muscle-niveau-*)."""
        return sum(1 for threshold in self.power_tiers if self.power >= threshold)

    @property
    def visual_variant(self):
        stage = self.aging_stage
        if stage == 2:
            return "old2"
        if stage == 1:
            return "old1"
        return f"muscle{self.muscle_level}"

    @property
    def visual_scale(self):
        """Échelle (x, y) du sprite de Finn."""
        sx, sy = VARIANT_SCALE[self.visual_variant]
        if self.is_aging:
            return sx, sy
        extra = max(0, self.power - (len(self.power_tiers) - 1))
        grow = min(MAX_EXTRA_GROWTH, 1 + GROWTH_PER_EXTRA_POWER * extra)
        return sx * grow, sy * grow

    @property
    def aura_strength(self):
        """0 = pas d'aura ; 1 = aura maximale. Le vieillissement l'éteint."""
        if self.is_aging or self.power == 0:
            return 0.0
        return min(1.0, 0.3 + 0.12 * self.power)

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------
    def register_death(self):
        self.deaths += 1

    def upgradable(self):
        return [s for s in STAT_ORDER if self.levels[s] < self.stats_cfg[s]["max_level"]]

    def rebirth_choices(self, rng=random):
        options = self.upgradable()
        count = min(self.choices_per_rebirth, len(options))
        picked = rng.sample(options, count)
        return sorted(picked, key=STAT_ORDER.index)

    def upgrade(self, stat):
        cap = self.stats_cfg[stat]["max_level"]
        self.levels[stat] = min(cap, self.levels[stat] + 1)

    def apply_aging(self, rng=random):
        """Retire un niveau à la stat la plus développée. Renvoie la stat perdue (ou None)."""
        lost = None
        for _ in range(self.aging_cfg["levels_lost_per_death"]):
            best = max(self.levels.values())
            if best == 0:
                break
            candidates = [s for s in STAT_ORDER if self.levels[s] == best]
            lost = rng.choice(candidates)
            self.levels[lost] -= 1
        return lost

    def describe(self, stat):
        cfg = self.stats_cfg[stat]
        return {
            "id": stat,
            "label": cfg["label"],
            "level": self.levels[stat],
            "max": cfg["max_level"],
            "effect": cfg["effect"],
            "color": tuple(cfg["color"]),
        }
