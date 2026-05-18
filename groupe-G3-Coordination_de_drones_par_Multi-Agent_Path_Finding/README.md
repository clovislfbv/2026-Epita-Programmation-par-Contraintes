# EPITA 2026 — Programmation par Contraintes
> Groupe de Matteo Atkinson et Paul Witkowski

## G3 - Coordination de drones par Multi-Agent Path Finding

Le Multi-Agent Path Finding (MAPF) consiste a calculer les trajectoires optimales d'un ensemble d'agents (drones, robots) partageant un espace commun, de maniere a ce qu'aucune collision ne se produise et que chaque agent atteigne son objectif. C'est un probleme combinatoire extremement difficile (NP-hard) qui se modelise naturellement en CP-SAT avec des contraintes de non-collision (pas deux agents au meme noeud au meme instant), de mouvement (deplacement vers les voisins uniquement), et d'objectif (chaque agent doit atteindre sa cible). **Note** : contrairement au Multi-robot Warehouse Task Assignment (annexe #12, EPITA 2025) qui modelise l'affectation de taches dans un entrepot sur grille 2D avec aisles predefinis, ce sujet se concentre sur la coordination de drones en espace aerien ouvert 3D avec contraintes de zones NOTAM, separation ATC (distance minimale en vol libre), conditions meteorologiques dynamiques, et obstacles tridimensionnels (batiments, lignes haute tension). L'espace de recherche est continu (pas de grille) et les contraintes de collision sont tridimensionnelles avec marges de securite.

### Objectifs
- Modeliser le MAPF comme un probleme CP-SAT avec contraintes de non-collision temporelles
- Implementer les contraintes de mouvement (grille 2D/3D), d'objectif et de non-collision (sommet et arete)
- Ajouter des contraintes de capacite (zones a trafic limite) et d'optimisation (minimiser le makespan ou le flowtime)
- Evaluer sur les benchmarks MAPF de la litterature (Moving AI Lab, grid-based)
- Comparer avec les algorithmes specialises MAPF (CBS, A* with OD, ECBS)

---

## Structure du projet

```
.
├── solver/               # Algorithmes MAPF
│   ├── grid.py           # Grille 2D/3D, voisins, obstacles
│   ├── mapf.py           # CP-SAT (MAPFSolver)
│   ├── cbs.py            # CBS + ECBS (space-time A*)
│   ├── astar.py          # A* + BFS distances
│   └── od_astar.py       # OD-A* (Operator Decomposition)
├── api/                  # Backend Flask
│   ├── server.py         # Endpoints /scenarios et /solve  →  port 5050
│   └── scenario_loader.py
├── frontend/             # Interface web 3D
│   ├── index.html
│   ├── scene.js          # Rendu 3D (Three.js)
│   ├── drones.js         # Animation drones
│   ├── ui.js             # Contrôles utilisateur
│   ├── api.js            # Appels REST
│   └── serve.py          # Serveur de dev  →  port 8080
├── notebooks/            # Analyses Jupyter
│   ├── 01_model_2d.ipynb # MAPF 2D : CP-SAT, CBS, ECBS, OD-A*
│   └── 02_model_3d.ipynb # Extension 3D avec bâtiments
├── scenarios/            # 11 scénarios JSON pré-définis
├── tests/                # Tests pytest
│   ├── test_grid.py
│   ├── test_mapf.py
│   ├── test_cbs.py
│   ├── test_od_astar.py
│   └── test_api.py
└── requirements.txt
```

---

## Lancement

### Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Backend (API Flask)

```bash
python api/server.py
# → http://localhost:5050
```

Endpoints disponibles :
- `GET  /scenarios` — liste des scénarios pré-définis
- `POST /solve`     — résout une instance MAPF (méthodes : `cpsat`, `cbs`, `ecbs`, `od_astar`)

### Frontend (interface web 3D)

Dans un second terminal (le backend doit tourner en parallèle) :

```bash
python frontend/serve.py
# → http://localhost:8080
```

Ouvrir `http://localhost:8080` dans le navigateur.

### Tests

```bash
pytest
# ou en mode verbeux
pytest -v
```

### Notebooks

```bash
jupyter lab
# ouvrir notebooks/01_model_2d.ipynb  (MAPF 2D)
# ouvrir notebooks/02_model_3d.ipynb  (extension 3D)
```

---

### Notebooks CoursIA pertinents

| Notebook | Chemin | Pertinence |
|----------|--------|------------|
| Search-3 A* | [Search/Part1-Foundations/Search-3-Informed.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part1-Foundations/Search-3-Informed.ipynb) | A*, heuristiques |
| CSP-4 Scheduling | [Search/Part2-CSP/CSP-4-Scheduling.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part2-CSP/CSP-4-Scheduling.ipynb) | IntervalVar, conflits |
| CSP-9 Distributed CSP | [Search/Part2-CSP/CSP-9-Distributed.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part2-CSP/CSP-9-Distributed.ipynb) | Multi-agent, coordination |
| Search-1 StateSpace | [Search/Part1-Foundations/Search-1-StateSpace.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part1-Foundations/Search-1-StateSpace.ipynb) | Espaces d'etats |

### References externes
- Stern, R., et al. (2019). "Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks." *Symposium on Combinatorial Search (SoCS)*. [arXiv](https://arxiv.org/abs/1906.08291)
- Sharon, G., et al. (2015). "Conflict-Based Search for Optimal Multi-Agent Pathfinding." *Artificial Intelligence*, 219, 40-66. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0004370214001386)
- Moving AI Lab: MAPF Benchmarks. [movingai.com](https://movingai.com/benchmarks/mapf/)
- Felner, A., et al. (2017). "Adding Heuristics to Conflict-Based Search for Multi-Agent Path Finding." *ICAPS*. [AAAI](https://ojs.aaai.org/index.php/ICAPS/article/view/13826)

---

## Livrables attendus

- **Code source** documente dans un sous-dossier dedie (`groupe-XX-nom-sujet/`)
- **Notebook Jupyter** explicatif avec analyse et visualisations **OU** **UI/demo fonctionnelle** (au choix — un notebook tres complet peut tenir lieu de demo, et inversement)
- **Slides de soutenance** (PDF ou lien)
- **Pull Request** soumise au plus tard **2 jours avant la soutenance**
---

## Ressources communes a tous les sujets

### Solveurs et outils
- **Google OR-Tools CP-SAT** : le solveur de reference pour ce cours. [Documentation officielle](https://developers.google.com/optimization/cp/cp_solver), [Guide Python](https://developers.google.com/optimization/cp/introduction), [Exemples par probleme](https://github.com/google/or-tools/tree/stable/examples/python)
- **Z3 SMT Solver** : pour les problemes de verification et de raisonnement symbolique. [Documentation](https://z3prover.github.io/api/html/namespacez3py.html), [Tutoriel Python](https://ericpony.github.io/z3py-tutorial/guide-examples.htm)
- **MiniZinc** : langage de modelisation CP de haut niveau. [Tutoriel](https://www.minizinc.org/doc-2.5.5/en/), [Benchmarks](https://www.minizinc.org/challenge.html)
- **CPMpy** : interface Python pour CP avec backends multiples. [Documentation](https://cpmpy.readthedocs.io/), [Exemples](https://github.com/CPMpy/cpmpy/tree/master/examples)

### Benchmarks et instances
- **CSPLib** : bibliotheque de problemes CP de reference. [En ligne](https://www.csplib.org/)
- **OR-Library** : instances pour problemes d'OR. [Beasley OR-Library](http://people.brunel.ac.uk/~mastjjb/jeb/info.html)
- **MiniZinc Challenge Benchmarks** : instances de competition. [GitHub](https://github.com/minizinc/minizinc-benchmarks)

### Notebooks du cours CoursIA
Les notebooks suivants sont disponibles dans le depot CoursIA ([jsboige/CoursIA](https://github.com/jsboige/CoursIA)) et constituent des prerequis ou des points de depart pour les projets :
- **Search/Part1-Foundations/** : Search-1 (StateSpace), Search-3 (A*, heuristiques), Search-4 (Local Search), Search-9 (Programmation lineaire), Search-11 (Metaheuristiques)
- **Search/Part2-CSP/** : CSP-1 (Fondamentaux), CSP-4 (Scheduling, IntervalVar, NoOverlap, Cumulative), CSP-5 (Optimization, Bin Packing, Knapsack), CSP-6 (Hybridation CP+SAT, LLM+CSP), CSP-7 (Soft Constraints), CSP-9 (Distributed CSP)
- **Search/Applications/CSP/** : App-4 (Job-Shop Scheduling), App-8 (MiniZinc), App-11 (Picross)
- **Search/Applications/Hybrid/** : App-10 (Portfolio Optimization), App-13 (TSP Metaheuristics), App-17 (VRP avec SA, GA, ACO, CP-SAT)
- **SymbolicAI/SmartContracts/** : Serie de 27 notebooks (SC-0 a SC-26) couvrant blockchain, Solidity, verification formelle (SC-14), fuzz testing (SC-13), cryptographie ZKP/HE (SC-15/16)
- **SymbolicAI/Planners/** : Planners-1 a Planners-12 couvrant PDDL, Fast Downward, planification temporelle, HTN, LLM Planning
- **SymbolicAI/Linq2Z3.ipynb** : Z3 SMT Solver en C#
- **SymbolicAI/OR-tools-Stiegler.ipynb** : OR-Tools CP en C#
- **Sudoku/** : 18 notebooks couvrant Sudoku avec multiples solveurs (Z3, CP-SAT, backtracking)
- **GameTheory/** : 17+ notebooks couvrant Nash Equilibrium, Cooperative Games, Shapley Value, Mechanism Design
- **Integration LLM** : function calling avec OpenAI/MCP pour assister la modelisation CP. Voir [Function Calling - OpenAI](https://platform.openai.com/docs/guides/function-calling) et [MCP Specification](https://modelcontextprotocol.io/)
