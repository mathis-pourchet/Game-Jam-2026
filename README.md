# The Finning

Jeu de plateforme 2D réalisé pour la Game Jam 2026 : le parcours de Mario, la progression par la mort de Sifu, dans l'univers d'Adventure Time.
Deux niveaux au choix, d'environ 5 et 3 minutes.

## Lancer le jeu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Le jeu se lance en plein écran : l'image est agrandie en gardant ses proportions (bandes noires si l'écran n'est pas en 16:9). Le curseur est caché pendant l'action et réapparaît en pause et dans les menus.

Options pour tester : `--fenetre` joue dans une fenêtre, `--boss` démarre devant l'arène du boss, `--col 120` démarre à la colonne 120 de la map, `--level 2` choisit le niveau visé par ces deux options.

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

Au début du niveau 1, un chien (Jake) affiche les commandes dans une bulle : des touches dessinées et un seul mot par action (bouger, sauter, épée). C'est le seul PNJ du jeu : il n'y a ni autre chien ni pancarte.

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
- **Renaissance** : Finn renaît quelques cases avant l'endroit de sa mort (au moins 3), sur un sol sûr et loin de son tueur. La map n'est **pas** réinitialisée : les ennemis tués le restent. Dans l'arène du boss, il réapparaît devant la grille et le boss repart à zéro.
- **Mort spéciale** : si Finn est tué par un champion (sorcier squelette, roi orange) ou par un boss, **ou** si l'un d'eux l'a touché dans les 5 secondes avant sa mort (même si le coup fatal vient d'un zombie, d'un piège ou d'une chute), il renaît plus fort : le joueur choisit une stat à améliorer (Saut, Vitesse, Force, Résistance).
- **Deux morts bien différentes** : une mort normale s'éteint dans le noir (couleurs qui ternissent, iris qui se ferme) ; une mort spéciale fait briller Finn pendant que la scène s'assombrit (ralenti, halo doré, éclair, rayons courts, petites ondes, étincelles qui montent, son dédié), sans envahir l'écran. L'écran qui suit n'affiche que « + 6 ans », en gris sur noir, ou en or pâle dans une pénombre chaude (halo doré qui respire, quelques braises) pour la mort spéciale.
- **Muscles** : chaque amélioration fait grossir Finn (jusqu'à environ 1,7 fois sa taille, sa boîte de collision ne change pas) et renforce son aura. Chaque stat a son effet : onde verte au saut, images rémanentes en courant (vitesse), gerbe de feu à l'épée (force), éclats roses quand il encaisse (résistance).
- **Vieillissement** : chaque mort ajoute 6 ans à Finn. Après 6 morts il devient vieux et perd une stat à chaque nouvelle mort ; il grisonne, se tasse, tremble, perd de la poussière et transpire en courant.
- **Limite** : à 10 morts, c'est le game over. Le nombre de morts et la limite ne sont **pas** affichés en jeu : seul l'âge de Finn trahit le temps qui passe.
- **Score** : moins de morts donne un meilleur score et un meilleur rang (S, A, B, C). Le record de chaque niveau est enregistré dans `saves/highscores.json`.

## Interface

Le jeu est volontairement muet pendant l'action : pas de message, pas de dégâts flottants, pas de nom de boss. Le HUD ne montre que la barre de vie, les stats, l'âge de Finn, les pièces et le chrono. Seule la bulle du chien du début parle. Tout le jeu utilise une seule police, Luckiest Guy (celle de l'écran d'accueil).

## Performances

Mesuré à la résolution réelle d'un MacBook (3456 × 2234 pixels), dans la vraie boucle du jeu :

- **Physique** : le jeu fait le même nombre de pas de physique à chaque image (2 à 60 images/s). Avant, le léger retard du minuteur système ajoutait un 3e pas à ~10 % des images, et Finn « sautait » plusieurs fois par seconde (voir `GameView.on_update`).
- **OpenGL** : `pyglet.options.debug_gl = False` dans `main.py`, avant l'import d'arcade, supprime une vérification d'erreur après chaque appel.
- **Dessin groupé** (`views/batch.py`) : réservé aux petites formes plutôt fixes (HUD, bulle du chien). Pour le décor et les barres de vie des monstres, les appels directs se sont révélés plus rapides.
- **Particules** recyclées au lieu d'être créées puis détruites (`systems/effects.py`).

Pour vérifier une optimisation, comparer à une copie du code d'avant en alternant plusieurs essais : un essai isolé trompe. Le nombre d'images lentes varie du simple au triple d'un essai à l'autre.

## Modifier le jeu

| Quoi | Où |
|---|---|
| Les maps (ASCII, sections de 40 colonnes) | `assets/maps/level_1.txt`, `level_2.txt` (légende en haut de `systems/level_manager.py`) |
| Liste des niveaux, boss, morts max, conseils du chien | `config/levels.json` |
| Stats, renaissance, vieillissement, niveaux de muscles | `config/stats_progression.json` |
| Physique, commandes, taille d'écran, plein écran, titre de la fenêtre | `settings.py` |
| Fenêtre des 5 s de la mort spéciale, distance de renaissance | `SPECIAL_DEATH_WINDOW` et `RESPAWN_BACK_TILES` dans `settings.py` |
| PV et dégâts des monstres / des pièges | `entities/enemy.py`, `entities/trap.py`, `HAZARD_DAMAGE` dans `systems/level_manager.py` |
| Découpe des planches (Finn, monstres, boss) | `tools/extract_sprites.py` puis relancer le script |
| Jake, décors en parallaxe, icônes | `tools/generate_sprites.py` |
| Bruitages et musiques | `tools/generate_sounds.py` |

> **Attention en dessinant une map** : au saut de base, Finn franchit environ 4,5 cases à plat, mais seulement 3,6 s'il doit monter de 2 cases. Tenez-vous à 3 cases vides maximum à plat, 2 en montant de 2 cases, et ne combinez jamais une montée de 3 cases avec un écart horizontal.

Les fichiers de `assets/sprites/` et `assets/sounds/` sont générés par ces scripts (le tileset, lui, vient de l'équipe). Pour changer une planche de personnage, remplace l'image dans `assets/finn`, `assets/monstre-niveau-*`, `assets/Boss-final` ou `assets/boos-final-2`, puis relance `tools/extract_sprites.py`. Les sprites y sont détectés automatiquement et rangés en lignes : si la disposition change, il faut adapter les tables `*_ANIMS` en haut du script.

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
- Tileset `ooo32` (`assets/tilesets/`) : fourni par l'équipe.
- Décors en parallaxe (ciel, montagnes, collines, nuages) : générés par `tools/generate_sprites.py`.
- Police : Luckiest Guy (Apache 2.0), licence dans `assets/fonts/`.
- Sons et musiques : générés par `tools/generate_sounds.py`.
