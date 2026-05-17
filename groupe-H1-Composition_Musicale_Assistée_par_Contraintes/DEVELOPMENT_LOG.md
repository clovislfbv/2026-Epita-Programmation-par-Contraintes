# Journal de Développement - Projet H1 Jazz Composition

Ce document retrace l'évolution du solveur de composition musicale par contraintes, les problèmes rencontrés et les solutions apportées.

## Étape 1 : Architecture Initiale (Top-down)
**Objectif :** Poser les bases du modèle CP-SAT et de l'export MIDI.

*   **Implémentation :**
    *   Variables de base : Pitch (hauteur), Duration (durée), Voice (voix).
    *   Variables harmoniques : Root (fondamentale), Quality (qualité d'accord), Degree (degré).
    *   Contraintes dures classiques : Tessitures, intervalles consonants, interdiction des quintes/octaves parallèles.
    *   Style Jazz (v1) : Préférence simple pour les accords de 7ème.

## Étape 2 : Identification du Problème de Répétition
**Observation :** Les fichiers MIDI générés (`test_jazz.mid`, `jazz_composition.mid`) présentaient une stagnation mélodique. La même note était répétée sur de nombreuses mesures.

**Cause technique :**
*   L'absence de contrainte de progression obligeait le solveur à rester sur l'accord le plus simple (Degré I).
*   La préférence pour les "mouvements conjoints" (petits intervalles) rendait l'intervalle 0 (répétition) comme étant le moins coûteux, favorisant l'immobilité.

## Étape 3 : Amélioration de la Variété et de l'Harmonie
**Changements apportés :**

1.  **Harmonie Tonale Avancée :**
    *   Contrainte de changement d'accord : Interdiction de garder le même degré plus de 2 temps consécutifs.
2.  **Dynamique Mélodique (Soft Constraints) :**
    *   Pénalité pour la répétition de la même note (`abs_diff == 0`).
    *   Bonus pour les petits mouvements (1 ou 2 demi-tons) pour encourager une mélodie fluide mais mobile.
    *   Pénalité accrue pour les grands sauts (> 4 demi-tons).

## Étape 4 : Spécialisation des Voix et Variété Rythmique
**Observation :** 
1. Le rythme se répétait à l'identique mesure après mesure.
2. Toutes les voix faisaient la même chose, sans distinction entre mélodie et accompagnement.

**Causes techniques :**
* Le solveur ne faisait aucune distinction entre les voix.
* Les préférences rythmiques étaient appliquées de manière uniforme sur toute la pièce.

**Solutions implémentées :**
* **Attribution de Rôles :**
    * Soprano (Voix 0) : Mélodie (mouvements libres, tessiture haute).
    * Alto/Ténor (Voix 1-2) : "Comping" (accords syncopés, attaques sur les contre-temps favorisées).
    * Basse (Voix 3) : "Walking Bass" (mouvement constant en croches, pas de silences autorisés, intervalles de 1-2 ou 5-7 demi-tons).
* **Entropie Rythmique :** Pénalité de répétition de mesure à mesure, forçant le solveur à varier les motifs.
* **Gestion des Silences :** Introduction du pitch `0` pour permettre des pauses respiratoires dans l'accompagnement.

## Étape 5 : Nettoyage et Stabilisation
**Objectif :** Aligner le code avec la documentation et corriger les tests.

*   **Changements :**
    *   Suppression des variables `durations` inutilisées.
    *   Correction des tests unitaires pour `TICKS_PER_BEAT = 2`.
    *   Optimisation des contraintes d'harmonie.

## Étape 6 : Transformation Quartet Jazz Qualitatif
**Objectif :** Passer d'une génération monotone à un véritable quartet de Jazz.

*   **Changements :** Contraintes de participation, Walking Bass, Shell Voicings, Multi-pistes.

## Étape 7 : Implémentation des Styles Baroque et Contemporain
**Objectif :** Étendre les capacités stylistiques du solveur.

## Étape 8 : Module d'Évaluation Quantitative
**Objectif :** Mesurer mathématiquement la qualité et la conformité des générations.

*   **Changements :**
    *   **Rule Checker** : Création de `evaluation/rule_checker.py`.
    *   **Métriques implémentées** :
        *   *Consonance Rate* : % d'intervalles verticaux consonants.
        *   *Leading Tone Resolution* : % de réussite de la résolution de la sensible (7->1).
        *   *Avg Voice Activity* : Taux d'occupation des voix (évitement du silence).
        *   *Melodic Diversity* : Richesse du vocabulaire de notes utilisé.
    *   **Intégration CLI** : Ajout du flag `--eval` pour afficher le rapport après chaque génération.

---


