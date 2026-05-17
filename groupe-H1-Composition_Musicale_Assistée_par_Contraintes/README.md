Louis Parmentier, Marianne Proux, Ethan Girard

# H1 - Composition Musicale Assistée par Contraintes

> Générer des partitions musicales (mélodies, harmonies) satisfaisant un ensemble de règles musicales encodées comme contraintes CP-SAT.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Modélisation musicale](#2-modélisation-musicale)
3. [Architecture du projet](#3-architecture-du-projet)
4. [Installation et utilisation](#4-installation-et-utilisation)
5. [Contraintes implémentées](#5-contraintes-implémentées)
6. [Évaluation](#6-évaluation)

---

## 1. Vue d'ensemble

### Problématique

La composition musicale est ici traitée comme un **problème de satisfaction de contraintes**. Une pièce musicale est une séquence de notes et d'accords respectant les règles de la théorie musicale classique et moderne :

- **Hauteur** : intervalles permis, résolutions obligatoires.
- **Harmonie** : accords autorisés, progressions tonales (ex: ii-V-I).
- **Contrepoint** : indépendance des voix, interdiction des quintes parallèles.
- **Rythme** : structure métrique, accents sur les temps forts.
- **Style** : Baroque, Jazz, Contemporain.

L'objectif est d'utiliser le solveur **OR-Tools CP-SAT** pour explorer l'immense espace des possibles et garantir une sortie mathématiquement et musicalement correcte.

---

## 2. Modélisation musicale

### 2.1 Représentation des notes

Le temps est discrétisé en **ticks** (1 tick = 1 croche). Chaque tick contient des variables pour les 4 voix (Soprano, Alto, Ténor, Basse) :

| Variable | Domaine | Description |
|----------|---------|-------------|
| `pitch[v, t]` | {0} ∪ [40, 74] | Hauteur MIDI (0 = silence) |

### 2.2 Représentation harmonique

L'harmonie est définie à chaque tick pour assurer la cohérence verticale :

| Variable | Domaine | Description |
|----------|---------|-------------|
| `root[t]` | 0–11 | Fondamentale de l'accord (0 = Do) |
| `quality[t]` | 0–5 | Qualité (MAJ, MIN, DOM7, DIM, MAJ7, MIN7) |
| `degree[t]` | 1–7 | Degré dans la gamme (I, II, ..., VII) |

---

## 3. Architecture du projet

```
H1/
├── main.py                 # Point d'entrée CLI
├── requirements.txt        # Dépendances du projet
├── core/
│   ├── model.py            # Moteur central CP-SAT
│   ├── variables.py        # Définition des variables
│   ├── constants.py        # Lexique et constantes musicales
│   ├── constraints/
│       ├── harmony.py      # Règles d'harmonie tonale
│       ├── counterpoint.py # Règles de conduite des voix
│       └── rhythm.py       # Structure métrique et activité
│   └── soft_constraints/
│       ├── baroque.py          # Style Bach (3 temps)
│       ├── jazz.py             # Style Quartet (7ème)
│       └── contemporary.py     # Style Moderne (dissonant et hasardeux)
├── export/
│   └── midi_export.py      # Export multi-pistes standard
└── evaluation/
    └── rule_checker.py     # Audit quantitatif post-génération
```

---

## 4. Installation et utilisation

### 4.1 Installation

Le projet nécessite Python 3.8+ et les dépendances listées dans `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4.2 Utilisation du CLI

Le script `main.py` accepte plusieurs arguments pour personnaliser la génération :

| Argument | Description | Défaut |
|----------|-------------|--------|
| `--measures` | Nombre de mesures | 8 |
| `--style` | `jazz`, `baroque` ou `contemporary` | `jazz` |
| `--key` | Tonalité (C, Eb, G#...) | `C` |
| `--eval` | Active le rapport d'évaluation | Désactivé |

**Exemples :**
```bash
# Générer un quartet de Jazz en Do majeur
python main.py --measures 8 --style jazz

# Générer une pièce Baroque avec audit complet
python main.py --style baroque --measures 4 --eval
```

---

## 5. Contraintes implémentées

### 5.1 Contraintes Dures (Hard)
- **Gamme** : Les notes doivent appartenir à la tonalité choisie.
- **Contrepoint** : Interdiction stricte des quintes et octaves parallèles.
- **Conduite des voix** : Soprano > Alto > Ténor > Basse (pas de croisement).
- **Résolution** : La sensible (7e degré) doit obligatoirement monter à la tonique.
- **Activité** : Chaque voix doit participer à au moins 60% de la pièce.

### 5.2 Préférences (Soft)
- **Baroque** : Favorise le mouvement contraire et les triades pures.
- **Jazz** : Favorise les accords de 7e, les syncopes et les approches chromatiques à la basse.
- **Contemporain** : Favorise les grands sauts mélodiques et évite la tonique en mélodie.

---

## 6. Évaluation

Le module `rule_checker.py` effectue une analyse mathématique de la partition générée pour garantir sa qualité :
- **Taux de consonance** : Vérification des intervalles verticaux.
- **Taux de résolution** : Vérification des règles de tension/détente.
- **Diversité mélodique** : Mesure de la richesse du vocabulaire utilisé.
