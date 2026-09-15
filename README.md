# Finn sans Fin

Jeu de plateforme 2D réalisé pour la Game Jam 2026 : le parcours de Mario, la progression par la mort de Sifu, dans l'univers d'Adventure Time.
Un seul niveau (les Plaines Bonbons puis le château du Roi des Glaces) d'environ 5 minutes.

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

## Les ennemis

- **Monstre niveau 1 (zombie)** : il patrouille, court vers Finn et lui bondit dessus (10 PV, 20 dégâts). Certains avancent par grands bonds (20 PV, 25 dégâts). On le tue à l'épée ou en lui sautant sur la tête.
- **Monstre niveau 2 (sorcier squelette, champion)** : il griffe de près (35 dégâts) et lance des boules de feu en forme de crâne de loin (25 dégâts). Il a 50 PV et on peut couper ses boules de feu à l'épée.
- **Boss final (Roi des Glaces)** : il s'envole puis retombe en créant des ondes de glace, tire des éclats de glace en éventail et fait tomber une pluie de stalactites. Les stalactites clignotent avant de tomber. À mi-vie, il enrage et appelle des zombies.

## Règles

- **Vie** : Finn a une barre de vie (100 PV au départ, +25 par niveau de Résistance). Chaque source fait des dégâts différents : épines 15, pics 25, scies 30, ondes/éclats/stalactites du boss 20 à 30. Un cœur ramassé rend 35 PV. Les monstres ont une barre de vie au-dessus de la tête.

- **But** : aller au bout de la map et vaincre le Roi des Glaces, puis entrer dans la porte de sortie.
- **Mort normale** (zombie, piège, chute) : Finn revient au début de la map, qui est réinitialisée.
- **Mort face à un sorcier squelette** : Finn renaît sur place, plus fort, et le joueur choisit une stat à améliorer (Saut, Vitesse, Force, Résistance).
- **Mort dans l'arène du boss** : Finn réapparaît devant la grille de l'arène, et mourir face au boss offre aussi une amélioration.
- **Muscles** : chaque amélioration change l'apparence de Finn, sur 4 niveaux (planches `assets/finn/finn-muscle-niveau-*`). Il gagne aussi une aura dorée.
- **Vieillissement** : chaque mort ajoute des années à Finn. Après 6 morts il devient vieux (sprite grisonnant et barbu) et perd une stat à chaque nouvelle mort.
- **Limite** : à 10 morts, c'est le game over, et stats, niveau et score sont réinitialisés.
- **Score** : moins de morts donne un meilleur score et un meilleur rang (S, A, B, C). Les pièces, les ennemis vaincus et le temps comptent aussi. Le record est enregistré dans `saves/highscores.json`.

## Modifier le jeu

| Quoi | Où |
|---|---|
| La map (ASCII, 8 sections de 40 colonnes) | `assets/maps/level_1.txt` (légende en haut de `systems/level_manager.py`) |
| Morts max, nom du boss, PV, conseils de Jake | `config/levels.json` |
| Stats, renaissance, vieillissement, seuils des 4 niveaux de muscles (`power_tiers`) | `config/stats_progression.json` |
| Physique, commandes, taille d'écran, soin des cœurs | `settings.py` |
| PV et dégâts des monstres / dégâts des pièges | `entities/enemy.py`, `entities/trap.py`, `HAZARD_DAMAGE` dans `systems/level_manager.py` |
| Découpe des planches (Finn niveaux 1 à 4, monstres, boss) | `tools/extract_sprites.py` puis relancer le script |
| Jake, décors, icônes (dessinés par code) | `tools/generate_sprites.py` |
| Bruitages, son de mort, musiques | `tools/generate_sounds.py` |

Les fichiers de `assets/sprites/` et `assets/sounds/` sont générés par ces scripts. Pour changer une planche de personnage, remplace l'image dans `assets/finn`, `assets/monstre-niveau-1`, `assets/monstre-niveau-2` ou `assets/Boss-final`, puis relance `tools/extract_sprites.py`. Les sprites y sont détectés automatiquement et rangés en lignes : si la disposition change, il faut adapter les tables `*_ANIMS` en haut du script.

## Structure du code

```
main.py                   point d'entrée (fenêtre, polices, menu)
settings.py               constantes
entities/                 Finn (player), monstres et boss (enemy), pièges et objets (trap)
systems/                  physique, chargement de la map, progression, morts, score, audio, effets
views/                    menu, jeu, écran de mort, renaissance, game over, victoire, HUD, décor
tools/                    scripts de génération des assets
```

## Crédits

- Tileset `ooo32` et planches de Finn, des monstres et du boss (`assets/finn`, `assets/monstre-niveau-1`, `assets/monstre-niveau-2`, `assets/Boss-final`) : fournis par l'équipe. Fan art Adventure Time (Cartoon Network), pour un usage non commercial de game jam.
- Polices : Luckiest Guy (Apache 2.0) et Press Start 2P (OFL). Les licences sont dans `assets/fonts/`.
- Sons et musiques : générés par `tools/generate_sounds.py`.
