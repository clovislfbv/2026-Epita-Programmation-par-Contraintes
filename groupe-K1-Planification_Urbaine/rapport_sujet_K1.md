# Rapport de Compréhension du Sujet : K1

## 1. Description du Projet
Le projet porte sur la **planification urbaine optimisée**. L'objectif est de déterminer les emplacements idéaux pour diverses infrastructures (hôpitaux, écoles, centres commerciaux, parcs, stations de recharge) au sein d'une zone urbaine.

Il s'agit d'un problème classique de **Théorie de la Localisation**, où l'on cherche à maximiser la couverture de la population tout en respectant des contraintes physiques, budgétaires et sociales.

## 2. Objectifs à Réaliser
Le travail se décline en plusieurs étapes clés :
- **Modélisation** : Traduire le problème de placement en modèles mathématiques de type *p-median* (minimiser la distance totale) ou *MCLP* (Maximal Covering Location Problem - maximiser la population couverte).
- **Implémentation des Contraintes** :
    - Budget total limité.
    - Superficie disponible par site.
    - Distance maximale acceptable pour les résidents.
    - Compatibilité entre infrastructures (ex: ne pas mettre une zone industrielle à côté d'une école).
- **Équité Sociale** : Intégrer des contraintes de couverture équitable pour minimiser la variance d'accessibilité entre les différents quartiers.
- **Évaluation** : Tester le modèle sur des données synthétiques et des données réelles (OpenStreetMap, INSEE).
- **Visualisation** : Produire des cartes interactives pour analyser les solutions.

## 3. Méthodes et Algorithmes
Le projet s'appuie sur la **Programmation par Contraintes (CP)** et l'**Optimisation Linéaire** :
- **CP-SAT (Google OR-Tools)** : Utilisation de variables binaires de localisation et de contraintes globales pour résoudre le problème d'optimisation combinatoire.
- **Modèles de Localisation** :
    - *p-median* : Placement de $p$ centres pour minimiser la distance moyenne.
    - *MCLP* : Maximisation de la population située à moins d'un rayon $R$ d'une infrastructure.
- **Soft Constraints (Contraintes Souples)** : Utilisation de pénalités ou de fonctions de satisfaction (Fuzzy/Weighted CSP) pour gérer les préférences et l'équité, comme vu dans le notebook CSP-7.
- **Programmation Linéaire en Nombres Entiers (PLNE)** : Approche alternative pour la localisation simple.

## 4. Ressources et Outils
### Bibliothèques Python :
- **Optimisation** : `ortools` (module `cp_model`), `pulp` (pour la programmation linéaire).
- **Géographie & Cartographie** : `geopandas` (manipulation de données spatiales), `folium` (cartes interactives), `osmnx` (extraction de données OpenStreetMap).
- **Analyse de données** : `pandas`, `numpy`, `matplotlib`.

### Sources de Données :
- **OpenStreetMap (OSM)** : Pour le réseau routier et les infrastructures existantes.
- **INSEE** : Pour les données de population par quartier/carreau.

## 5. Lien avec les Notebooks du Cours
Les notebooks fournis servent de base méthodologique :
- **CSP-1 (Fondamentaux)** : Apprentissage de la modélisation sous forme de variables, domaines et contraintes.
- **CSP-5 (Optimisation)** : Techniques pour le Bin Packing et le Knapsack, directement transposables au choix de sites sous contraintes de capacité.
- **CSP-7 (Soft Constraints)** : Crucial pour l'aspect "équité" et gestion des préférences de planification.
- **Search-9 (Linear Programming)** : Fondements de la PLNE utiles pour comprendre les solveurs de localisation.

---
