# Finn sans Fin

Jeu de plateforme 2D réalisé pour la Game Jam 2026 : le parcours de Mario, la progression par la mort de Sifu, dans l'univers d'Adventure Time.
Un seul niveau (les Plaines Bonbons puis le château du Roi Zombie) d'environ 5 minutes.

## Lancer le jeu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Options pour tester : `--boss` démarre devant l'arène du boss, `--col 120` démarre à la colonne 120 de la map.

## Commandes

| Action | Touches |
|---|---|
| Bouger | Flèches, Q/D (AZERTY) ou A/D (QWERTY) |
| Sauter (maintenir = plus haut) | Espace, Haut, Z, W |
| Épée | J, X ou K |
| Échelle | Haut / Bas |
| Traverser une plateforme | Bas + Saut |
| Pause | Échap ou P |
| Couper le son | M |

## Règles

- **But** : aller au bout de la map et vaincre le Roi Zombie Bonbon, puis entrer dans la porte de sortie.
- **Mort normale** (zombie normal, piège, chute) : Finn revient au début de la map, qui est réinitialisée.
- **Mort face à un champion** (zombie violet) : Finn renaît sur place, plus fort, et le joueur choisit une stat à améliorer (Saut, Vitesse, Force, Résistance). Finn devient visiblement musclé et gagne une aura.
- **Mort dans l'arène du boss** : Finn réapparaît devant la grille de l'arène, et mourir face au boss offre aussi une amélioration.
- **Vieillissement** : chaque mort ajoute des années à Finn. Après 6 morts il devient vieux (sprite grisonnant et barbu) et perd une stat à chaque nouvelle mort.
- **Limite** : à 10 morts, c'est le game over, et stats, niveau et score sont réinitialisés.
- **Score** : moins de morts donne un meilleur score et un meilleur rang (S, A, B, C). Les pièces, les ennemis vaincus et le temps comptent aussi. Le record est enregistré dans `saves/highscores.json`.

## Modifier le jeu

| Quoi | Où |
|---|---|
| La map (ASCII, 8 sections de 40 colonnes) | `assets/maps/level_1.txt` (légende en haut de `systems/level_manager.py`) |
| Morts max, nom du boss, PV, conseils de Jake | `config/levels.json` |
| Stats, renaissance, vieillissement | `config/stats_progression.json` |
| Physique, commandes, taille d'écran | `settings.py` |
| Découpe des planches Finn et zombie et variantes musclé/vieux | `tools/extract_sprites.py` puis relancer le script |
| Jake, décors, icônes (dessinés par code) | `tools/generate_sprites.py` |
| Bruitages, son de mort, musiques | `tools/generate_sounds.py` |

Les fichiers de `assets/sprites/` et `assets/sounds/` sont générés par ces scripts. On peut les remplacer par de vrais dessins ou sons en gardant le même nom et la même taille.

## Structure du code

```
main.py                   point d'entrée (fenêtre, polices, menu)
settings.py               constantes
entities/                 Finn (player), zombies et boss (enemy), pièges et objets (trap)
systems/                  physique, chargement de la map, progression, morts, score, audio, effets
views/                    menu, jeu, écran de mort, renaissance, game over, victoire, HUD, décor
tools/                    scripts de génération des assets
```

## Crédits

- Tileset `ooo32` et planches de Finn (`assets/finn`) et du zombie (`assets/monstre`) : fournis par l'équipe. Fan art Adventure Time (Cartoon Network), pour un usage non commercial de game jam.
- Polices : Luckiest Guy (Apache 2.0) et Press Start 2P (OFL). Les licences sont dans `assets/fonts/`.
- Sons et musiques : générés par `tools/generate_sounds.py`.
