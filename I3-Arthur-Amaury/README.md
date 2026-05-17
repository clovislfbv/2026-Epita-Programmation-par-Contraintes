# CP-LLM : Modélisation CP-SAT assistée par LLM

Projet I3 — Pipeline qui transforme une description en langage naturel d'un problème
d'optimisation en un modèle CP-SAT (`ortools.sat.python`) exécutable, vérifie sa
correction, et le compare à une modélisation manuelle de référence.

L'objectif : étudier dans quelle mesure un LLM généraliste peut prendre en charge
les étapes de modélisation (choix des variables, formalisation des contraintes,
génération de code solver), et où il échoue. Le pipeline est découpé en étages
isolés pour que chaque échec soit attribuable à un étage précis.

## Ce que fait le projet

- **Décompose** une description NL d'un problème en analyse structurée → variables
  → contraintes → code Python CP-SAT, chaque étage piloté par un appel LLM dédié.
- **Vérifie** le code généré sur trois niveaux : parse, faisabilité (le solver
  retourne `OPTIMAL`/`FEASIBLE`), sémantique (la solution respecte les contraintes
  extraites à l'étage 3).
- **Réessaie automatiquement** la génération de code (boucle de réparation
  jusqu'à 3 tentatives) en injectant le message d'erreur précédent dans le prompt
  de retry, avec montée en température pour diversifier les réponses.
- **Benchmarke** le pipeline sur 10 problèmes classiques (N-queens, knapsack,
  graph coloring, sudoku, magic square, bin packing, diet, job shop, TSP, VRP)
  contre des références manuelles, et produit un rapport JSON détaillé.
- **Met en cache** sur disque les appels LLM (sha256 du prompt) pour rendre les
  exécutions reproductibles et économiser des tokens entre runs.
- **Expose un dashboard Streamlit** (live run + repair, dashboard de benchmark,
  templates de prompts) pour explorer les résultats interactivement.

## Architecture

Pipeline en 4 étages, chacun isolément testable :

| # | Étage         | Rôle                                                             | LLM ? |
|---|---------------|------------------------------------------------------------------|-------|
| 1 | `analyzer`    | NL → structure (type, objectif, entités, paramètres)             | oui   |
| 2 | `variables`   | Structure → liste de variables de décision typées avec bornes    | oui   |
| 3 | `constraints` | Structure + variables → liste de contraintes formalisées         | oui   |
| 4 | `codegen`     | Variables + contraintes → script Python `ortools.sat.python`     | oui   |

Chaque étage produit un artefact validable (schéma Pydantic). Si un benchmark
échoue, on sait à quel étage la chaîne casse — c'est ce qui permet l'analyse de
modes d'échec.

## Layout

```
I3-Arthur-Amaury/
├── cp_llm/
│   ├── schemas.py        # Pydantic : ProblemAnalysis, VariableSpec, ConstraintSpec, PipelineResult
│   ├── prompts.py        # Templates de prompts par étage + runner d'execution
│   ├── llm_client.py     # Wrapper Mistral (interface LLMClient)
│   ├── cache.py          # Cache disque sha256 des appels LLM
│   ├── pipeline.py       # Étages 1-3 (analyse, variables, contraintes)
│   ├── codegen.py        # Étage 4 (génération Python)
│   ├── verification.py   # Vérif syntaxique + faisabilité + sémantique
│   ├── visualizers.py    # Rendu des solutions (Streamlit)
│   └── runner.py         # Orchestre les 4 étages + retry + vérif
├── benchmark/
│   ├── problems/         # 10 descriptions NL (.txt)
│   └── references/       # 10 modèles CP-SAT manuels (.py)
├── scripts/
│   ├── run_pipeline.py   # Pipeline sur un problème unique
│   ├── run_benchmark.py  # Benchmark complet + rapport JSON
│   ├── app.py            # Dashboard Streamlit
│   └── import_expert_models.py
└── tests/
    └── test_references.py  # Vérifie que les modèles manuels tournent
```

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis remplir MISTRAL_API_KEY
```

Clé Mistral : créer un compte sur https://console.mistral.ai puis copier la clé
dans `.env` (variable `MISTRAL_API_KEY`).

## Usage

### Pipeline sur un problème unique

```bash
# Par defaut : Mistral, cache disque actif
python scripts/run_pipeline.py benchmark/problems/nqueens.txt

# Choisir un autre modele Mistral
python scripts/run_pipeline.py benchmark/problems/knapsack.txt --model codestral-latest

# Desactiver le cache (chaque etage refait l'appel LLM)
python scripts/run_pipeline.py benchmark/problems/tsp.txt --no-cache

# Sauver le code genere
python scripts/run_pipeline.py benchmark/problems/sudoku.txt --save-code out/sudoku.py
```

Le script affiche les artefacts de chaque étage (analyse, variables, contraintes,
code) puis le résultat de la vérification, et exit non-zéro si le pipeline a
échoué.

### Benchmark complet

```bash
python scripts/run_benchmark.py
```

Produit `benchmark_report.json` avec, pour chaque problème :
- Sortie de chaque étage du pipeline
- Toutes les tentatives de codegen (succès + retries) avec leur erreur
- Statut de la vérification (syntaxique, faisabilité, sémantique)
- Temps d'exécution pipeline vs référence manuelle
- Étage d'échec si applicable

### Dashboard Streamlit

```bash
streamlit run scripts/app.py
```

Trois onglets :
- **Live Run & Repair** : lance le pipeline sur un problème, visualise les
  tentatives successives de la boucle de réparation.
- **Benchmark Dashboard** : explore `benchmark_report.json` (taux de succès,
  étages d'échec, comparaison aux références).
- **Prompts templates** : inspecte les prompts utilisés par chaque étage.

### Tester que les références tournent

```bash
python -m pytest tests/
```

## Méthodologie d'évaluation

Trois niveaux de vérification (cf `cp_llm/verification.py`) :

1. **Syntaxique** : le code généré parse et s'exécute sans exception
2. **Faisabilité** : `solver.Solve()` retourne `OPTIMAL` ou `FEASIBLE` sur petites instances
3. **Sémantique** : la solution trouvée respecte chaque contrainte que l'étage 3 a extraite

Taxonomie d'erreurs visée par le benchmark :

- C1 — Variable manquée
- C2 — Mauvais type de variable (Int au lieu d'Interval, etc)
- C3 — Bornes incorrectes
- C4 — Contrainte explicite manquée
- C5 — Contrainte implicite manquée (les "évidences" non dites)
- C6 — Mauvaise direction d'optimisation
- C7 — Erreur de génération de code (API ortools mal utilisée)

## Boucle de réparation

Quand la vérification échoue à l'étage codegen, le runner relance la génération
jusqu'à `max_retries` fois (3 par défaut), en injectant dans le prompt le
message d'erreur précédent et le code fautif. La température est montée à
chaque essai (0 → 0.5 → 1.0) pour éviter que le LLM ne renvoie exactement le
même code. Le prompt de retry reste générique (aucun indice sur la fix
attendue), pour ne pas biaiser l'évaluation.

## Statut

- [x] Pipeline 4 étages avec schémas Pydantic
- [x] 10 problèmes de référence couverts (N-queens, knapsack, graph coloring,
      sudoku, magic square, bin packing, diet, job shop, TSP, VRP)
- [x] Vérification syntaxique + faisabilité + sémantique
- [x] Boucle de réparation avec montée en température
- [x] Cache disque des appels LLM
- [x] Dashboard Streamlit (live run, benchmark, prompts)
- [ ] Comparaison expert/pipeline structurée (gap d'objectif systématique)
