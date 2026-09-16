# The Finning

Jeu de plateforme 2D réalisé pour la Game Jam 2026 : le parcours de Mario, la progression par la mort de Sifu, dans l'univers d'Adventure Time.
Deux niveaux au choix, d'environ 5 et 3 minutes.

## Lancer le jeu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Options pour tester : `--boss` démarre devant l'arène du boss, `--col 120` démarre à la colonne 120 de la map, `--level 2` choisit le niveau visé par ces deux options.

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

## Les niveaux

Le menu « Jouer » ouvre un écran de choix du niveau.

1. **Les Plaines Bonbons** — l'aventure complète : prairies, collines, grottes de gomme, glacier, cimetière, remparts puis le château du Roi des Glaces. 320 colonnes.
2. **Les Cimes de Sucre** — plus court mais bien plus technique : sauts précis au-dessus du vide, escalier de plateformes suspendues, verglas, couloir de pics, puis le salon du Majordome. 240 colonnes.

Au début du niveau 1, un chien (Jake) explique les commandes. C'est le seul PNJ du jeu : il n'y a ni autre chien ni pancarte.

## Les ennemis

- **Monstre niveau 1 (zombie)** : il patrouille, court vers Finn et lui bondit dessus (10 PV, 20 dégâts). Certains avancent par grands bonds (20 PV, 25 dégâts). On le tue à l'épée ou en lui sautant sur la tête.
- **Monstre niveau 2 (sorcier squelette, champion)** : il griffe de près (35 dégâts) et lance des boules de feu de loin (25 dégâts). 50 PV. On peut couper ses projectiles à l'épée.
- **Monstre niveau 3 (roi orange, champion lui aussi)** : même rôle que le sorcier mais plus coriace — 80 PV, 40 dégâts au corps à corps, et des boules de feu plus fréquentes (28 dégâts). Il garde le niveau 2.
- **Boss final 1 (Roi des Glaces)** : il s'envole puis retombe en créant des ondes de glace, tire des éclats en éventail et fait tomber une pluie de stalactites. À mi-vie, il enrage et appelle des zombies.
- **Boss final 2 (Majordome Menthe)** : tout se joue au sol — il charge en ligne droite (34 dégâts), bondit pour retomber en onde de choc, et lance des bonbons explosifs (22 dégâts). 260 PV, et lui aussi enrage à mi-vie.

Le boss d'un niveau est choisi par `boss.kind` dans `config/levels.json` (`ice_king` ou `butler`).

## Règles

- **Vie** : Finn a une barre de vie (100 PV au départ, +25 par niveau de Résistance). Épines 15, pics 25, scies 30, attaques des boss 20 à 34. Un cœur ramassé rend 35 PV. La gomme toxique (`~`) tue sur le coup.
- **But** : aller au bout de la map, vaincre le boss, puis entrer dans la porte de sortie.
- **Mort normale** (zombie, piège, chute) : Finn revient au début de la map, qui est réinitialisée.
- **Mort face à un champion** (sorcier squelette ou roi orange) : Finn renaît sur place, plus fort, et le joueur choisit une stat à améliorer (Saut, Vitesse, Force, Résistance).
- **Mort dans l'arène du boss** : Finn réapparaît devant la grille, et mourir face au boss offre aussi une amélioration.
- **Muscles** : chaque amélioration change l'apparence de Finn, sur 4 niveaux, plus une aura dorée.
- **Vieillissement** : chaque mort ajoute des années à Finn. Après 6 morts il devient vieux et perd une stat à chaque nouvelle mort.
- **Limite** : à 10 morts, c'est le game over. Le nombre de morts et la limite ne sont **pas** affichés en jeu : seul l'âge de Finn trahit le temps qui passe.
- **Score** : moins de morts donne un meilleur score et un meilleur rang (S, A, B, C). Le record de chaque niveau est enregistré dans `saves/highscores.json`.

## Interface

Le jeu est volontairement muet pendant l'action : pas de message, pas de dégâts flottants, pas de nom de boss. Le HUD ne montre que la barre de vie, les stats, l'âge de Finn, les pièces et le chrono. Seule la bulle du chien du début parle.

## Modifier le jeu

| Quoi | Où |
|---|---|
| Les maps (ASCII, sections de 40 colonnes) | `assets/maps/level_1.txt`, `level_2.txt` (légende en haut de `systems/level_manager.py`) |
| Liste des niveaux, boss, morts max, conseils du chien | `config/levels.json` |
| Stats, renaissance, vieillissement, niveaux de muscles | `config/stats_progression.json` |
| Physique, commandes, taille d'écran, titre de la fenêtre | `settings.py` |
| PV et dégâts des monstres / des pièges | `entities/enemy.py`, `entities/trap.py`, `HAZARD_DAMAGE` dans `systems/level_manager.py` |
| Découpe des planches (Finn, monstres, boss) | `tools/extract_sprites.py` puis relancer le script |
| Le tileset 32x32 | `tools/generate_tileset.py` |
| Jake, décors en parallaxe, icônes | `tools/generate_sprites.py` |
| Bruitages et musiques | `tools/generate_sounds.py` |

> **Attention en dessinant une map** : au saut de base, Finn franchit environ 4,5 cases à plat, mais seulement 3,6 s'il doit monter de 2 cases. Tenez-vous à 3 cases vides maximum à plat, 2 en montant de 2 cases, et ne combinez jamais une montée de 3 cases avec un écart horizontal.

Les fichiers de `assets/sprites/`, `assets/tilesets/` et `assets/sounds/` sont générés par ces scripts. Pour changer une planche de personnage, remplace l'image dans `assets/finn`, `assets/monstre-niveau-*`, `assets/Boss-final` ou `assets/boos-final-2`, puis relance `tools/extract_sprites.py`. Les sprites y sont détectés automatiquement et rangés en lignes : si la disposition change, il faut adapter les tables `*_ANIMS` en haut du script.

## Structure du code

```
main.py                   point d'entrée (fenêtre, polices, menu)
settings.py               constantes
entities/                 Finn (player), monstres et boss (enemy), pièges et objets (trap)
systems/                  physique, chargement de la map, progression, morts, score, audio, effets
views/                    menu, choix du niveau, jeu, mort, renaissance, game over, victoire, HUD, décor
tools/                    scripts de génération des assets
```

## Crédits

- Planches de Finn, des monstres et des boss (`assets/finn`, `assets/monstre-niveau-1/2/3`, `assets/Boss-final`, `assets/boos-final-2`) : fournies par l'équipe. Fan art Adventure Time (Cartoon Network), pour un usage non commercial de game jam.
- Tileset et décors : générés par `tools/generate_tileset.py` et `tools/generate_sprites.py`.
- Polices : Luckiest Guy (Apache 2.0) et Press Start 2P (OFL). Les licences sont dans `assets/fonts/`.
- Sons et musiques : générés par `tools/generate_sounds.py`.
