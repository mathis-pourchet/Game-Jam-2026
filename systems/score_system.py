"""Score : pièces, ennemis vaincus, temps et nombre de morts (moins on meurt, mieux c'est)."""
import json

from settings import SAVES

KILL_POINTS = {"zombie": 100, "jumper": 150, "champion": 500, "king": 700, "boss": 3000}
RANKS = [
    (0, "S", "Héros légendaire"),
    (2, "A", "Grand aventurier"),
    (5, "B", "Survivant tenace"),
    (99, "C", "Miraculé de Ooo"),
]


class ScoreSystem:
    def __init__(self, save_file=SAVES / "highscores.json"):
        self.save_file = save_file
        self.coins = 0
        self.kills = 0
        self.kill_points = 0
        self.elapsed = 0.0
        self.boss_defeated = False
        self.reset()

    def reset(self):
        self.coins = 0
        self.kills = 0
        self.kill_points = 0
        self.elapsed = 0.0
        self.boss_defeated = False

    def reset_attempt(self):
        """Une mort « normale » remet la map à zéro : on perd les pièces de la tentative."""
        self.coins = 0

    def tick(self, dt):
        self.elapsed += dt

    def add_coin(self, amount=1):
        self.coins += amount

    def add_kill(self, kind):
        self.kills += 1
        self.kill_points += KILL_POINTS.get(kind, 100)
        if kind == "boss":
            self.boss_defeated = True

    def breakdown(self, deaths):
        time_bonus = max(0, int(2400 - self.elapsed * 4))
        return {
            "Base": 5000,
            "Pièces": self.coins * 20,
            "Ennemis": self.kill_points,
            "Bonus temps": time_bonus,
            "Morts": -deaths * 450,
        }

    def final_score(self, deaths):
        return max(0, sum(self.breakdown(deaths).values()))

    @staticmethod
    def rank(deaths):
        for limit, letter, title in RANKS:
            if deaths <= limit:
                return letter, title
        return RANKS[-1][1], RANKS[-1][2]

    # ------------------------------------------------------------------
    def load_best(self, level_id):
        try:
            with open(self.save_file, encoding="utf-8") as f:
                return json.load(f).get(str(level_id))
        except (OSError, ValueError):
            return None

    def save_if_best(self, level_id, score, deaths):
        """Enregistre le score s'il bat le record. Renvoie True si nouveau record."""
        data = {}
        try:
            with open(self.save_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        best = data.get(str(level_id))
        if best and best["score"] >= score:
            return False
        data[str(level_id)] = {"score": score, "deaths": deaths, "time": round(self.elapsed, 1)}
        try:
            self.save_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            return False
        return True
