# J2 — Enchères combinatoires et Winner Determination

Implémentation et comparaison de deux approches (CP-SAT et PLNE) pour résoudre
le **Winner Determination Problem** (WDP) en enchères combinatoires, étendue
au mécanisme **Vickrey-Clarke-Groves** (VCG) pour le calcul des paiements.

Projet académique de groupe — ING2 Programmation par Contraintes, EPITA S8.

**Équipe (3 personnes)** :
- Lucas Majerczyk ([Sosolalt](https://github.com/Sosolalt)) — tech lead :
  solveurs (CP-SAT, PLNE), VCG, intégration, ops dépôt.
- Nabil Chartouni ([NCH04](https://github.com/NCH04)) — benchmarks :
  générateur synthétique, parser et datasets CATS officiels.
- Wilfrid Wangon-Zekou ([56Nights](https://github.com/56Nights)) —
  analyse / documentation : heuristique greedy, notes de recherche,
  notebook, README.

Découpage en 4 sprints (S0 bootstrap, S1 cœur WDP, S2 benchmarks + VCG,
S3 livrables). Pour chaque tâche : un *issue* dans
[`.github/ISSUES.md`](.github/ISSUES.md) (owner, reviewer, deadline,
critères d'acceptation), une *feature branch*, une *PR* relue par un
autre membre, un *merge* `--no-ff` portant un `Reviewed-by:` trailer.
Cf. section *Méthode de travail* plus bas.

---

## Synthèse pour le jury

**Livrables du sujet** : 5/5 couverts.
**Extensions ajoutées** : 4 (heuristique LOS, audit programmatique VCG
en deux régimes, intégration CATS officielle, suite de tests pytest).
**Tests automatisés** : **44/44 passants** en ~1.3s (revenus pédagogiques,
cohérence CP-SAT≡PLNE, propriétés VCG, parsing CATS, propriétés sortie).
**Notebook** : 55 cellules exécutées end-to-end, 4 figures générées.
**Documentation** : 4 notes de recherche, README, docstrings extensifs
(~90% couverture), tracker projet
([`PROJECT_TRACKER.md`](PROJECT_TRACKER.md)) et ledger
d'issues ([`.github/ISSUES.md`](.github/ISSUES.md)).
**Audits** : revues par pairs systématiques sur chaque PR ; audits
théoriques croisés sur les modules critiques (VCG, greedy, parser CATS).

### Apports théoriques marquants

1. **Décomposition du régime VCG** en deux cas : *canonique* (DSIC + IR
   + efficacité) vs *avec budget* (DSIC perdue car F dépend des prix
   déclarés). Démonstration **algébrique** + **contre-exemple numérique**
   (2 items, 3 bidders, cap=11 ; shading r₁=3 vs vrai v₁=8 → surplus 7
   vs 0) dans [`research/04_*`](research/04_vcg_budget_non_truthful.md).
   API `run_vcg_canonical(instance)` expose le régime DSIC et refuse les
   instances budgétées (garde-fou).
2. **Encadrement honnête de la borne LOS** $\sqrt{m}$ : valable pour
   bidders single-minded sans XOR/budget ; explicitement **non opérante**
   sur nos benchmarks (qui ont des XOR par bidder). Ratio rapporté
   uniquement comme empirique.
3. **Hypothèse free-disposal** côté vendeur explicitée et citée
   (Cramton-Shoham-Steinberg 2006).
4. **Langage d'offres nommé** : XOR par bidder (Nisan 2000 §3 + Thm 1).
5. **Audit `verify_properties()`** distingue rigoureusement les
   propriétés *théoriques* du mécanisme (IR, losers pay 0, no-deficit /
   weak budget balance) des *vérifications de consistance solveur*
   (welfare monotonicity, sous-WDP OPTIMAL).

---

## Objectif du projet

Étant donné un ensemble d'items à vendre et un ensemble d'offres combinatoires
(chaque offre = un paquet d'items + un prix), trouver l'**ensemble d'offres
gagnantes qui maximise le revenu du vendeur**, sous contraintes :

- un item peut être attribué à **au plus une** offre gagnante (hypothèse de
  *free disposal* côté vendeur — un item peut rester non vendu, cf. Cramton-
  Shoham-Steinberg 2006, ch. 1) ;
- éventuels plafonds de budget (global ou par soumissionnaire) ;
- éventuels groupes XOR (un soumissionnaire ne gagne qu'une seule de ses
  offres alternatives).

**Langage d'offres : XOR par bidder** (Nisan 2000, *Bidding and Allocation
in Combinatorial Auctions*, §3). Chaque bidder déclare une clause XOR
(au plus une de ses offres gagne) ; les bidders sont indépendants
(agrégation OR implicite, pas un opérateur du langage). Les instances
CATS importées peuvent en revanche encoder l'**OR-of-XOR** via les
*dummy goods* (cf. parser).

### Mapping livrables ↔ code

| # | Livrable du sujet | Code | Test |
|---|---|---|---|
| 1 | Modèle CP-SAT du WDP (Set Packing) | [solver_cpsat.py:45-160](wdp/solver_cpsat.py) | `test_cpsat_pedagogical` |
| 2 | Contraintes budget (global + per_bidder) | [solver_cpsat.py:94-111](wdp/solver_cpsat.py) | `test_cpsat_pedagogical[with_budget]` |
| 3 | Contraintes XOR par soumissionnaire | [solver_cpsat.py:114-118](wdp/solver_cpsat.py) | `test_cpsat_pedagogical[with_xor]` |
| 4 | CP-SAT vs PLNE sur benchmarks | [solver_milp.py](wdp/solver_milp.py), notebook §4 | `test_cpsat_and_milp_agree`, `test_cats_cpsat_milp_agree` |
| 5 | Mécanisme VCG | [vcg.py](wdp/vcg.py), notebook §5 | `test_vcg_properties`, `test_vcg_toy_payment_david` |

### Extensions ajoutées

| Extension | Code | Pourquoi |
|---|---|---|
| Heuristique gloutonne LOS | [solver_greedy.py](wdp/solver_greedy.py) | Borne inférieure rapide ; baseline empirique sur stress |
| Audit programmatique VCG (2 régimes) | [vcg.py:133-262](wdp/vcg.py), [research/04](research/04_vcg_budget_non_truthful.md) | Distingue DSIC canonique vs perte sous budget (avec preuve) |
| Parser CATS officiel | [cats_parser.py](wdp/cats_parser.py), `data/cats/` | Benchmarks Leyton-Brown 2000 réels (au-delà des CATS-like synthétiques) |
| Suite de tests pytest | [tests/](tests/) | 44 tests (13 pédagogiques + 31 CATS) |

---

## Installation

```bash
# 1. Cloner le repo et entrer dedans
git clone <repo_url> && cd auction-winner-determination

# 2. Créer un environnement virtuel Python
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 3. Installer les dépendances
pip install -r requirements.txt
```

**Dépendances** : `ortools` (CP-SAT), `pulp` (PLNE/CBC), `numpy`, `pandas`,
`matplotlib`, `jupyter`, `pytest`. Python 3.11+ requis.

---

## Utilisation rapide

### Lancer le notebook (rendu principal)

```bash
source venv/bin/activate
jupyter notebook J2-CombinatorialAuctions.ipynb
```

Le notebook contient les 5 livrables + extensions, avec narration,
visualisations et benchmarks.

### Résoudre une instance en ligne de commande

```python
from wdp.instance import Instance
from wdp.solver_cpsat import solve_wdp_cpsat
from wdp.vcg import run_vcg, run_vcg_canonical

inst = Instance.from_json("data/toy_example.json")

# WDP exact via CP-SAT
alloc = solve_wdp_cpsat(inst)
print(f"Revenu : {alloc.revenue}  Gagnants : {alloc.winning_bid_ids}")

# VCG canonique (refuse les instances avec budget actif)
vcg_result = run_vcg_canonical(inst)
print(vcg_result.summary())

# Audit des propriétés
print(vcg_result.verify_properties())
```

### Charger une instance CATS officielle

```python
from wdp.cats_parser import parse_cats_file
from wdp.solver_cpsat import solve_wdp_cpsat

inst = parse_cats_file("data/cats/regions_g30_b100_s10000.txt")
print(inst.summary())  # 30 items, 104 bids (réels+dummies), 19 XOR groups
alloc = solve_wdp_cpsat(inst)
print(f"Revenu : {alloc.revenue:.2f}  Statut : {alloc.status}")
```

### Lancer les tests

```bash
python -m pytest tests/ -v
# 44 passed in ~1.3s
```

### Régénérer les datasets de benchmark synthétiques

```bash
python scripts/build_benchmarks.py
```

### Régénérer le notebook depuis le script Python

```bash
python scripts/build_notebook.py
jupyter nbconvert --to notebook --execute J2-CombinatorialAuctions.ipynb --output J2-CombinatorialAuctions.ipynb
```

### Régénérer les benchmarks CATS officiels

Le générateur C++ CATS doit être compilé séparément (cf.
[`research/03_cats_benchmarks_status.md`](research/03_cats_benchmarks_status.md)
pour la procédure macOS/Linux avec lp_solve 4.0). Une fois compilé :

```bash
/path/to/cats -d regions -goods 30 -bids 100 -seed 1 \
              -filename data/cats/regions_g30_b100_s1 -int_prices
```

Le parser ([wdp/cats_parser.py](wdp/cats_parser.py)) convertit le format
texte CATS en `Instance`, en reconstruisant les `xor_groups` à partir
des dummy goods.

---

## Architecture du projet

```
auction-winner-determination/
├── J2-CombinatorialAuctions.ipynb   ← Rendu principal (55 cellules exécutées)
├── README.md                          ← Ce document
├── PROJECT_TRACKER.md                 ← Plan projet (équipe, sprints, issues, deadlines)
├── requirements.txt
├── .gitignore
├── .gitmessage                        ← Template Conventional Commits
│
├── .github/
│   ├── ISSUES.md                      ← Ledger d'issues (in-repo, lifecycle complet)
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/task.yml
│
├── docs/
│   └── CONTRIBUTING.md                ← Conventions commit / branching / review
│
├── slides/                            ← Slides soutenance (PDF ajouté à la finalisation)
│
├── wdp/                              ← Package Python (le "moteur")
│   ├── __init__.py
│   ├── instance.py                   ← Bid / Budget / Instance / Allocation, I/O JSON
│   ├── generator.py                  ← Génération CATS-like (random, regions)
│   ├── solver_cpsat.py               ← Solveur CP-SAT (livrables 1-2-3)
│   ├── solver_milp.py                ← Solveur PLNE PuLP/CBC + LP relaxation (livrable 4)
│   ├── solver_greedy.py              ← Heuristique LOS (extension)
│   ├── cats_parser.py                ← Parser format CATS officiel (extension)
│   └── vcg.py                        ← Mécanisme VCG + run_vcg_canonical (livrable 5)
│
├── scripts/
│   ├── build_benchmarks.py           ← Génère data/synthetic/ (20 instances)
│   └── build_notebook.py             ← Génère J2-CombinatorialAuctions.ipynb
│
├── tests/                            ← Suite pytest (44 tests, ~1.3s)
│   ├── conftest.py                   ← PYTHONPATH setup
│   ├── test_pedagogical.py           ← 15 tests : revenus, CP-SAT≡PLNE, VCG canonique,
│   │                                   manipulation sous budget, garde-fou
│   └── test_cats_parser.py           ← 31 tests : parsing CATS, XOR depuis dummy goods,
│                                       cohérence solveurs, propriétés sortie
│
├── research/                         ← Notes techniques (traçabilité décisions)
│   ├── README.md                     ← Index
│   ├── 01_vcg_ir_monotonicity_equivalence.md
│   ├── 02_greedy_los_approximation.md
│   ├── 03_cats_benchmarks_status.md  ← Procédure compilation + intégration CATS
│   └── 04_vcg_budget_non_truthful.md ← Algèbre IR/no-deficit + contre-exemple
│
├── data/
│   ├── toy_example.json              ← Cas Paris/Lyon/Marseille (validation)
│   ├── with_budget.json              ← Test des contraintes de budget
│   ├── with_xor.json                 ← Test des contraintes XOR
│   ├── synthetic/                    ← 20 instances "CATS-like" (générateur custom)
│   │   ├── random_{small,med,large,stress}_seed*.json
│   │   └── regions_{small,med,large,stress}_seed*.json
│   └── cats/                         ← 18 instances CATS officielles (Leyton-Brown 2000)
│       ├── arbitrary_*.txt
│       ├── matching_*.txt
│       ├── paths_*.txt
│       ├── regions_*.txt
│       └── scheduling_*.txt
│
└── results/
    └── figures/                      ← Graphes générés par le notebook
        ├── time_comparison.png       ← CP-SAT vs PLNE log-log
        ├── integrality_gap.png       ← Gap LP par instance
        ├── greedy_ratio.png          ← Ratio greedy/exact
        └── vcg_payments.png          ← Welfare social vs revenu vendeur
```

---

## Description des modules

### `wdp/instance.py` — Structures de données

- **`Bid`** (frozen dataclass) : `id`, `bidder`, `items` (frozenset), `price`.
- **`Budget`** : plafond global + plafonds par bidder (toutes optionnelles).
- **`Instance`** : items + bidders + bids + budget + xor_groups.
  Validation automatique au chargement (ids uniques, références cohérentes,
  prix positifs, pas d'orphans XOR). Module docstring nomme le langage
  d'offres (XOR par bidder, Nisan 2000).
- **`Allocation`** : résultat = bids gagnants + revenu + statut (`OPTIMAL` /
  `FEASIBLE` / `INFEASIBLE` / `UNKNOWN`) + temps + nom du solveur.

I/O JSON via `Instance.from_json(path)` et `inst.to_json(path)`.

### `wdp/generator.py` — Génération CATS-like

Deux distributions inspirées de **CATS** :

- **`generate_random_instance(...)`** : bundles aléatoires (Poisson),
  prix avec **synergie multiplicative** sur la taille du bundle.
- **`generate_regions_instance(...)`** : items disposés sur une **grille 2D**,
  bundles = rectangles connexes (modélise les enchères de spectre).

Convention XOR : toutes les offres d'un même bidder forment automatiquement
un groupe XOR. Seeds reproductibles.

### `wdp/solver_cpsat.py` — Solveur CP-SAT (livrables 1-2-3)

Modèle Set Packing en **CP-SAT** (OR-Tools) :

```
Variables   : x[j] ∈ {0,1} pour chaque offre j
Objectif    : max Σ price[j] * x[j]
Contraintes : (1) Σ_{j : i ∈ S_j} x[j] ≤ 1   pour chaque item i
                                              (free disposal côté vendeur)
              (2) Σ price[j]*x[j] ≤ B         (budget global, optionnel)
              (3) Σ_{j : bidder=k} price[j]*x[j] ≤ B_k
                                              (budget per bidder, optionnel)
              (4) Σ_{j ∈ G} x[j] ≤ 1          (XOR par groupe, optionnel)
```

Fonction principale : `solve_wdp_cpsat(instance, enforce_budget, enforce_xor,
time_limit_s, excluded_bidders, log)` → renvoie une `Allocation`.

Les flags permettent d'activer pédagogiquement les livrables 1, 2, 3
indépendamment. `excluded_bidders` est utilisé par VCG pour calculer
$W_{-k}^*$.

**Échelle des prix** : `PRICE_SCALE = 1000` (3 décimales). Aligné sur
CATS `bid_alpha=1000` pour garantir la précision bit-exacte des prix
CATS dans CP-SAT.

### `wdp/solver_milp.py` — Solveur PLNE (livrable 4)

Modèle **identique** à CP-SAT, résolu par **PuLP + CBC** (Coin-OR
Branch and Cut). Permet la comparaison directe.

Trois fonctions :

- **`solve_wdp_milp(...)`** : PLNE classique, retourne `OPTIMAL`,
  `FEASIBLE` (incumbent valide récupéré sous time-out), `INFEASIBLE`
  ou `UNKNOWN`. Re-vérification indépendante de la faisabilité de
  l'incumbent en Python (helper `_check_feasibility`) avant retour —
  garde-fou contre les bugs CBC.
- **`solve_wdp_lp_relaxation(...)`** : relaxation linéaire (variables
  continues dans [0,1]). Utilisée pour mesurer le **gap d'intégralité**
  $(LP^* - IP^*) / IP^*$.

### `wdp/solver_greedy.py` — Heuristique LOS (extension)

Heuristique gloutonne **Lehmann-O'Callaghan-Shoham** (2002, JACM 49(5)) :
tri des offres par `price / sqrt(|items|)` décroissant, puis sélection
séquentielle si compatible avec items + budget + XOR.

**Borne théorique** : $\sqrt{m}$ ($m$ = nombre d'items) — *uniquement
sous l'hypothèse single-minded* (un seul bundle désiré par bidder, pas
de XOR, pas de budget).

**Cadre opérationnel ici** : nos benchmarks ont systématiquement des
XOR par bidder. La borne $\sqrt{m}$ ne s'applique donc **pas**. Le
greedy est utilisé comme heuristique empirique pure.

**Pas de revendication d'incitation** : nous n'implémentons pas les
paiements de valeurs critiques de Lehmann et al. → aucune propriété
strategy-proof revendiquée.

### `wdp/cats_parser.py` — Parser CATS officiel (extension)

Parser pour le format texte du **générateur CATS officiel** (Leyton-Brown,
Pearson, Shoham 2000, https://github.com/kevinlb1/CATS).

Format CATS :

```
goods <n_real>
bids <n_total>
dummy <n_dummy>

<bid_id> <price> <good_id_1> <good_id_2> ... #
```

Les **dummy goods** (IDs ≥ `n_real`) encodent l'XOR : deux bids
partageant un dummy good deviennent mutuellement exclusifs via la
contrainte d'exclusivité d'item. Le parser **reconstruit explicitement**
les `xor_groups` Python à partir des dummy goods → exploitable comme
`AddAtMostOne` dans CP-SAT/PLNE.

Fonction principale : `parse_cats_file(path, bidder_grouping=...)`.
Deux stratégies bidder :

- `BidderGrouping.PER_BID` (défaut) : 1 bidder par bid.
- `BidderGrouping.PER_DUMMY` : clustering transitif via union-find
  sur les dummy goods partagés.

18 instances pré-générées dans `data/cats/` (5 distributions × seeds
variées). Toutes résolues à `OPTIMAL` par CP-SAT en < 60ms.

### `wdp/vcg.py` — Mécanisme VCG (livrable 5)

Implémente les paiements de **Vickrey-Clarke-Groves** :

$$p_k^{VCG} = W_{-k}^* - (W^* - v_k(x^*))$$

- $W^*$ : welfare social optimal avec tous les bidders.
- $W_{-k}^*$ : welfare optimal **sans** les bids de $k$.
- $v_k(x^*)$ : valeur totale gagnée par $k$ dans l'allocation globale.

Algorithme : résout le WDP global, puis re-résout **une fois par bidder
gagnant** en excluant ses bids. Coût : $1 + |\text{gagnants}|$
résolutions du WDP.

**Deux régimes** (cf. docstring du module +
[`research/04_*`](research/04_vcg_budget_non_truthful.md)) :

- **Canonique** (`enforce_budget=False`, ou `run_vcg_canonical(inst)` qui
  refuse explicitement les instances budgétées) : F indépendant des prix
  déclarés ⇒ théorème Vickrey/Clarke/Groves applicable → **DSIC + IR +
  efficacité**.
- **Avec budget** (`enforce_budget=True`, défaut) : la contrainte
  `Σ price·x ≤ cap` rend F **dépendant des rapports** ⇒ DSIC perdue
  (cf. Borgs et al. 2005, Dobzinski-Lavi-Nisan 2008). **IR mécanique** et
  **no-deficit** restent vrais par construction (slack-monotonie) —
  preuve algébrique + contre-exemple numérique de manipulation
  (shading r₁=3 → surplus 7 vs 0 en honnête) dans
  [`research/04_vcg_budget_non_truthful.md`](research/04_vcg_budget_non_truthful.md).

**Troisième condition (Nisan-Ronen 2007)** : si un sous-WDP renvoie
`FEASIBLE` ou `UNKNOWN` (time-out), même la mécanique du régime canonique
perd ses garanties. Tracé via `VCGResult.non_optimal_solves` et la
propriété `optimal_solves` de `verify_properties()`.

`VCGResult.verify_properties()` retourne un dict structuré avec :

- *Propriétés théoriques VCG* : `individual_rationality`, `losers_pay_zero`,
  `no_deficit` (alias *weak budget balance*).
- *Vérifications de consistance* : `welfare_monotone`, `optimal_solves`.

Le `welfare_monotone` est documenté comme **incapable** de détecter une
sous-estimation de $W_{-k}^*$ (la relation reste alors trivialement
vraie) — `optimal_solves` est le vrai garde-fou contre les time-outs.

### `tests/` — Suite pytest (44 tests)

Cible la rubrique "qualité du code". Voir tableau plus bas.

### `research/` — Notes techniques

Décisions de design archivées pour traçabilité :

- [01_vcg_ir_monotonicity_equivalence.md](research/01_vcg_ir_monotonicity_equivalence.md)
  — démonstration algébrique : `IR ⇔ welfare_monotone` étant donné la
  formule de paiement.
- [02_greedy_los_approximation.md](research/02_greedy_los_approximation.md)
  — choix de LOS √|S| (vs densité plate), portée de la borne √m.
- [03_cats_benchmarks_status.md](research/03_cats_benchmarks_status.md)
  — procédure compilation CATS officiel sur macOS, scope (5 distributions
  économiques vs L1–L8 hors scope volontaire).
- [04_vcg_budget_non_truthful.md](research/04_vcg_budget_non_truthful.md)
  — algèbre IR + no-deficit sous budget, contre-exemple numérique de
  manipulation.

### `scripts/build_notebook.py`

Construit `J2-CombinatorialAuctions.ipynb` cellule par cellule. Plus
maintenable qu'éditer le JSON. Réexécutable.

### `J2-CombinatorialAuctions.ipynb` — Le rendu narratif

55 cellules organisées en sections suivant l'ordre des livrables :

| Section | Contenu |
|---------|---------|
| 0 | Introduction, contexte historique (Rothkopf 1998, Sandholm 2002, CATS), langage d'offres XOR-par-bidder, modèle mathématique avec free-disposal |
| 1 | Livrable 1 — WDP CP-SAT de base sur `toy_example` (revenu attendu 40, validé) |
| 2 | Livrable 2 — Ajout du budget sur `with_budget` (chute de 80→50) |
| 3 | Livrable 3 — Contraintes XOR sur `with_xor` (revenu 57) |
| 4 | Livrable 4 — Benchmarks 20 instances synthétiques + CP-SAT vs PLNE + gap LP |
| 4a | Caractérisation du gap d'intégralité par distribution |
| 4b | Extension — Benchmarks CATS officiels (5 distributions, 18 instances) |
| 4c | Extension — Heuristique gloutonne LOS, ratio empirique vs exact |
| 5 | Livrable 5 — VCG sur 3 instances pédagogiques |
| 5a | VCG sous contrainte de budget : pourquoi la truthfulness est perdue (contre-exemple numérique) |
| 5b | Audit programmatique des propriétés VCG (5 propriétés, 2 catégories) |
| 6 | Conclusion — Trade-offs, limites VCG, pistes |

Le notebook **importe** les modules `wdp/` sans dupliquer de code.

### `data/*.json` — Format d'une instance

```json
{
  "name": "toy_example",
  "items": ["P", "L", "M"],
  "bidders": ["Alice", "Bob", "Carol", "David", "Eve"],
  "bids": [
    {"id": 0, "bidder": "Alice", "items": ["P", "L"], "price": 25},
    {"id": 3, "bidder": "David", "items": ["P", "L", "M"], "price": 40}
  ],
  "budget": {"global": null, "per_bidder": {}},
  "xor_groups": [[0, 1, 2]]
}
```

---

## Résultats principaux

### Validation pédagogique

| Instance | n_items | n_bids | Revenu optimal | Solveur | Temps |
|---|---|---|---|---|---|
| `toy_example` | 3 | 5 | **40** (David) | CP-SAT, PLNE | < 5ms |
| `with_budget` | 6 | 7 | **50** (Alice1+Bob3) | CP-SAT, PLNE | < 10ms |
| `with_xor` | 5 | 7 | **57** (Alice2+Bob4) | CP-SAT, PLNE | < 10ms |

Toutes les valeurs sont **dérivées analytiquement à la main**, encodées
dans pytest, et confirmées par CP-SAT et PLNE (test `test_cpsat_pedagogical`
+ `test_cpsat_and_milp_agree`).

### Comparaison CP-SAT vs PLNE — benchmarks synthétiques

Synthèse par classe d'instances (moyenne sur seeds, mesurée par le
notebook) :

| distrib | size | items | bids | rev_CP | rev_MILP | gap_LP % | time_CP | time_MILP |
|---|---|---|---|---|---|---|---|---|
| random | small | 10 | 20 | 753.87 | 753.87 | 9.03 | 0.00 s | 0.02 s |
| random | med | 30 | 100 | 2313.21 | 2313.21 | 8.63 | 0.04 s | 0.71 s |
| random | large | 100 | 500 | 8531.18 | 8500.02 | 9.70 | 30.12 s (FEASIBLE) | 30.06 s |
| random | stress | 200 | 1000 | 15839.74 | 15357.88 | 11.58 | 30.09 s (FEASIBLE) | 30.04 s |
| regions | small | 16 | 30 | 2417.44 | 2417.44 | ~0 | 0.00 s | 0.02 s |
| regions | med | 36 | 100 | 5764.14 | 5764.14 | 0.00 | 0.01 s | 0.03 s |
| regions | large | 100 | 500 | 17469.39 | 17469.39 | 0.27 | 0.03 s | 0.14 s |
| regions | stress | 196 | 1000 | 34418.22 | 34418.22 | 0.00 | 0.05 s | 0.10 s |

**Observations** :

- **Cohérence des modèles** : sur toutes les instances résolues à
  l'optimum, CP-SAT et PLNE donnent la **même valeur d'objectif** —
  formulation équivalente validée empiriquement.
- **CP-SAT plus rapide sur `random`** (gap LP lâche, 8–11%) — la
  propagation de contraintes exploite efficacement la structure pure.
- **PLNE compétitif sur `regions`** (gap LP ~0%, structure géométrique
  ⇒ branch-and-cut converge en quelques nœuds).
- **Stress** : CP-SAT atteint le time-out mais retourne une **borne
  inférieure** (FEASIBLE) ; PLNE résout `random_stress` à l'OPTIMAL en
  30s (à la limite), `regions_stress` en 100ms.

### Benchmarks CATS officiels

5 distributions générées par le binaire CATS (Leyton-Brown 2000),
parsées par `wdp/cats_parser.py`. Synthèse :

| distrib | n_inst | bids_avg | xor_groups_avg | rev_CP_avg | time_CP_ms | time_MILP_ms |
|---|---|---|---|---|---|---|
| arbitrary | 3 | 100.3 | 19.0 | 1786.46 | 10.86 | 360.50 |
| matching | 3 | 105.7 | 16.3 | 74.84 | 4.94 | 28.25 |
| paths | 4 | 125.5 | 29.8 | 15.56 | 6.10 | 35.50 |
| regions | 4 | 126.8 | 23.8 | 2175.53 | 20.92 | 226.20 |
| scheduling | 4 | 130.3 | 5.0 | 39.76 | 6.64 | 40.21 |

Toutes les 18 instances résolues à `OPTIMAL`. Tests cross-solveurs +
propriétés sortie : `test_cats_cpsat_milp_agree` + `test_cats_solver_output_respects_constraints`
(parametrisés une instance par distribution).

### Paiements VCG (sur `toy_example`)

David paie **37** (= ce que les autres auraient gagné sans lui : Bob+Eve
= 22+15) et garde **3 € de surplus**. Analogue combinatoire de l'enchère
au second prix : le gagnant paie l'externalité qu'il impose aux autres.

| bidder | v_k | W_{-k}* | p_k | surplus |
|---|---|---|---|---|
| David | 40.00 | 37.00 | 37.00 | 3.00 |

### Audit programmatique VCG

Toutes les propriétés passent (`VCGResult.verify_properties()`) sur
les 3 instances pédagogiques **dans leur régime approprié** :

- **régime canonique** (`run_vcg_canonical`) sur `toy_example` et
  `with_xor` : DSIC + IR + losers pay 0 + no-deficit + optimal_solves.
- **régime avec budget** (`run_vcg(enforce_budget=True)`) sur
  `with_budget` : IR + losers pay 0 + no-deficit + optimal_solves
  (DSIC explicitement **non** asserté).

### Contre-exemple numérique : manipulation sous VCG-avec-budget

Construction détaillée dans
[`research/04_vcg_budget_non_truthful.md`](research/04_vcg_budget_non_truthful.md) :

```
Items A, B ; bidders b1, b2, b3 ; budget global C=11
v_1=8 pour {A}, v_2=8 pour {B}, v_3=9 pour {A,B}

Truthful (r_i = v_i)         : F admet seulement {b3}, b1 perd → surplus = 0
Shading (r_1=3, autres=v)    : F admet {b1,b2}, b1 gagne A, p_1 = 1
                                 → vrai surplus = 8 − 1 = 7
```

**7 > 0 strictement** ⇒ déclarer la vérité n'est pas une stratégie
dominante quand `enforce_budget=True`. L'algèbre complète
(slack-monotonie, IR mécanique, no-deficit mécanique) et la
construction pas-à-pas du contre-exemple figurent dans la note de
recherche.

### Heuristique gloutonne LOS

Sur les **3 instances pédagogiques**, le greedy LOS atteint 82–96% de
l'optimum exact en < 1ms.

Sur les **20 benchmarks synthétiques** (avec XOR), le ratio empirique
est variable selon la distribution — voir le tableau détaillé dans le
notebook (section "Extension — Heuristique gloutonne") et
`results/figures/greedy_ratio.png`.

Comme les benchmarks sortent du cadre single-minded de Lehmann et al.,
**aucune borne théorique d'approximation ne s'applique** : ces ratios
sont **purement empiriques**.

---

## Tests automatisés

```bash
python -m pytest tests/ -v
# 44 passed in ~1.3s
```

Couverture par fichier :

| Fichier | Cas | Quoi |
|---|---|---|
| [test_pedagogical.py](tests/test_pedagogical.py) | 13 | Revenus pédagogiques exacts (toy=40, budget=50, xor=57). CP-SAT ≡ PLNE. Greedy ≤ exact. Paiement VCG de David = 37 (toy). Propriétés VCG (IR + losers pay 0 + no-deficit + optimal_solves) sur les 3 instances. |
| [test_cats_parser.py](tests/test_cats_parser.py) | 31 | Parsing header CATS minimal. Reconstruction XOR depuis dummy goods. `BidderGrouping` PER_BID vs PER_DUMMY. Parse + solve sur **18 fichiers CATS** (parametrisé). Cohérence CP-SAT ≡ PLNE (1 par distribution). Propriétés sortie (item-disjoint + XOR ≤1 + revenu cohérent, 1 par distribution). |

Revue par pairs sur chaque PR (cf.
[`.github/ISSUES.md`](.github/ISSUES.md) — chaque issue clôturée porte le
nom du reviewer). Les modules critiques (VCG, greedy, parser CATS) ont
fait l'objet d'audits théoriques croisés tracés dans les notes
[`research/`](research/).

---

## Décisions de design (extraits)

| Décision | Pourquoi |
|---|---|
| `enforce_budget=True` reste le défaut de `run_vcg` | Le budget est une caractéristique intrinsèque de l'instance, pas un toggle de mécanisme. La validation DSIC se fait via `run_vcg_canonical` qui refuse explicitement les instances budgétées. |
| `welfare_monotone` gardé malgré redondance algébrique avec IR | Sert de canary pour la pathologie symétrique de sur-estimation de $W_{-k}^*$ ; le docstring précise que `optimal_solves` est le vrai garde-fou contre les time-outs. |
| `PRICE_SCALE = 1000` (et non 100) dans CP-SAT | Aligne sur CATS `bid_alpha=1000` (3 décimales). Garantit la précision bit-exacte des prix CATS dans CP-SAT ; les pédagogiques (2 décimales) restent exacts par construction. |
| Pas d'instances CATS L1–L8 / `-npv` / `-upv` | Hors scope volontaire. Les 5 distributions économiquement motivées (Leyton-Brown 2000) sont la contribution principale ; les variantes alternatives sont accessibles mais n'ajoutent pas de structure pédagogique. |
| Greedy LOS sans paiements de valeurs critiques | Solveur d'allocation pur, pas un mécanisme. Aucune revendication d'incitation, donc pas de complications inutiles. |
| Tests sur instances pédagogiques + manipulation in-memory | Couvre toutes les configurations de contraintes (item exclusivity, budget global+per-bidder, XOR) sans coût CI. Plus 18 instances CATS pour les tests d'intégration. |

---

## Méthode de travail

Cette section regroupe les éléments d'organisation et de qualité
technique en regard des deux critères de notation correspondants.

### Composition de l'équipe et rôles

| Membre | GitHub | Rôle principal | Scope |
|---|---|---|---|
| Lucas Majerczyk | [Sosolalt](https://github.com/Sosolalt) | tech lead / mainteneur | Modèles CP-SAT + PLNE, VCG (paiements, audits, régimes), intégration, ops dépôt |
| Nabil Chartouni | [NCH04](https://github.com/NCH04) | benchmarks engineer | Générateur synthétique, parser CATS, datasets CATS officiels, note 03 |
| Wilfrid Wangon-Zekou | [56Nights](https://github.com/56Nights) | analyse / documentation | Heuristique greedy LOS, notes de recherche 01/02, notebook, README |

Le partage de charge a été affiché en amont dans
[`PROJECT_TRACKER.md`](PROJECT_TRACKER.md) et matérialisé sur le dépôt
par le ratio de commits par membre (consultable via `git shortlog -sne`).
Chaque membre a été à la fois *owner* sur une partie du périmètre et
*reviewer* sur celui des deux autres — la matrice de rotation des
reviewers est visible dans le tableau d'issues ci-dessous et dans
[`PROJECT_TRACKER.md`](PROJECT_TRACKER.md) §3.

### Planning (4 sprints)

| Sprint | Période | Thème | Critère de sortie |
|---|---|---|---|
| **S0 — Bootstrap** | semaine 1 | structure dépôt, conventions, scaffolding | `.gitignore`, `requirements.txt`, package `wdp/`, CONTRIBUTING, tracker + ledger |
| **S1 — Cœur WDP** | semaine 2 | data model, générateur, CP-SAT, PLNE, budget, XOR | les deux solveurs résolvent `toy_example`, `with_budget`, `with_xor` à valeurs égales |
| **S2 — Benchmarks & VCG** | semaine 3 | greedy LOS, parser + datasets CATS officiels, VCG (canonique + budget), audits | CATS end-to-end ; paiements VCG calculés + audit IR / monotonie / OPTIMAL passe |
| **S3 — Livrables** | semaine 4 | notebook, README, notes de recherche, figures, slides | notebook reproductible, 4 notes, README, slides, PR de soumission |

Standups Lundi / Mercredi / Vendredi en groupe privé ; *sprint review*
de fin de sprint matérialisée par un commit `chore(sprint-N): review …`
sur `main`.

### Conventions Git et workflow d'issue

- **Commits** : *Conventional Commits* (`feat`, `fix`, `docs`, `test`,
  `refactor`, `perf`, `chore`, `build`, `ci`, `style`, `revert`).
  Sujet ≤ 60 caractères, impératif. Scopes dédiés pour la
  planification : `docs(plan): …` (création / clôture d'issue dans le
  ledger) et `chore(sprint-N): …` (cérémonies de sprint). Template à
  [`.gitmessage`](.gitmessage), règles complètes dans
  [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).
- **Branches** : `feat/<sprint>-<slug>`, `fix/<slug>`, `docs/<slug>`.
  Une *feature branch* par issue non triviale ; les changements
  ponctuels de docs/chore peuvent atterrir directement sur `main`.
- **Cycle d'une issue** :
  1. *Define* : commit `docs(plan): open issue #N — …` qui ajoute
     l'entrée correspondante à [`.github/ISSUES.md`](.github/ISSUES.md)
     (owner, reviewer, deadline, critères d'acceptation, branche
     cible).
  2. *Work* : commits atomiques sur la *feature branch* dédiée.
  3. *Review* : ouverture de PR, revue par le reviewer désigné. La
     PR est mergée par le **reviewer** lui-même avec `git merge --no-ff`
     — le merge commit porte donc *author = owner*, *committer =
     reviewer* et un trailer `Reviewed-by: <Name> <email>`. Cette
     dissociation est volontaire : elle reproduit la sémantique d'une
     PR squashée par le reviewer et trace la responsabilité d'approbation.
  4. *Close* : commit `docs(plan): close issue #N` qui passe le statut
     à *closed* dans le ledger en référençant la PR et le reviewer.

### Suivi des décisions techniques

Les décisions de design non triviales sont archivées dans le dossier
[`research/`](research/) (4 notes), chacune référencée depuis le code,
les tests et le notebook. Le rôle d'une note de recherche : capturer le
*pourquoi* d'un choix (alternative écartée, contre-exemple, hypothèse)
plutôt que le *quoi* (déjà dans le code).

### Processus de communication

La coordination tactique se fait par messagerie privée du groupe
(planification, déblocages, points de design rapides). Les décisions et
incidents qui méritent une trace sont formalisés en *issues* dans
[`.github/ISSUES.md`](.github/ISSUES.md) **avant** d'ouvrir la *feature
branch* correspondante. Le choix d'un *ledger* in-repo plutôt que des
GitHub Issues externes est délibéré : il garde l'historique de
planification attaché à l'arbre source (visible dans tous les `git
checkout` et `git diff` de PR), et facilite la consultation hors
ligne. Les PRs référencent les numéros du ledger ; les *merge
commits* portent un `Reviewed-by:` trailer pour matérialiser
l'approbation.

### Carte rapide pour la lecture du dépôt

| Question | Où regarder |
|---|---|
| Qui a fait quoi ? | `git shortlog -sne` + [`PROJECT_TRACKER.md`](PROJECT_TRACKER.md) §3 |
| Pourquoi telle décision ? | [`research/`](research/) (4 notes) + commit message correspondant |
| Comment ça se relit ? | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) + [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) |
| Quelle issue ferme quoi ? | [`.github/ISSUES.md`](.github/ISSUES.md) (status + PR + reviewer par entrée) |
| Topologie réelle des PRs ? | `git log --graph --oneline` (`--no-ff` partout, *committer ≠ author* sur les merges) |

---

## Pistes d'extension

- Étendre la couverture CATS : générer L1–L8 (distributions artificielles
  Leyton-Brown 2000) et pousser jusqu'à `g200_b1000`. Cf. `research/03_*`.
- **Warm-start CP-SAT** avec la solution LOS via `model.AddHint()` ;
  mesurer l'impact sur le time-to-optimal des instances `large`/`stress`.
- **Mécanismes alternatifs** au VCG : core-selecting auctions
  (Day-Milgrom 2008) ou Combinatorial Clock Auction — visent à augmenter
  le revenu vendeur sans sacrifier complètement la truthfulness, et
  répondent directement à la pathologie "lonely Vickrey"
  (Ausubel-Milgrom 2006) citée dans la conclusion.
- **Paralléliser** les $n+1$ résolutions du VCG (chaque $W_{-k}^*$ est
  indépendant) — speedup linéaire trivial.
- Démonstration interactive (Streamlit / Gradio) pour la soutenance.
- Preuve formelle dans le notebook de la NP-difficulté du WDP par
  réduction depuis Weighted Set Packing (cf. Sandholm 2002).

---

## Références

- **WDP / NP-hardness** : Rothkopf, Pekeč, Harstad. *Computationally
  Manageable Combinational Auctions*. Management Science 44(8), 1998.
  Sandholm. *Algorithm for Optimal Winner Determination in Combinatorial
  Auctions*. AIJ 135(1-2), 2002.
- **CATS** : Leyton-Brown, Pearson, Shoham. *Towards a Universal Test Suite
  for Combinatorial Auction Algorithms*. EC 2000. Source :
  https://github.com/kevinlb1/CATS.
- **VCG** : Vickrey (1961, JoF), Clarke (1971, Public Choice), Groves
  (1973, Econometrica).
- **Greedy LOS** : Lehmann, O'Callaghan, Shoham. *Truth Revelation in
  Approximately Efficient Combinatorial Auctions*. JACM 49(5), 2002.
- **Bidding languages** : Nisan. *Bidding and Allocation in Combinatorial
  Auctions*. EC 2000.
- **Free disposal** : Cramton, Shoham, Steinberg (eds.). *Combinatorial
  Auctions*. MIT Press, 2006, ch. 1.
- **VCG sous contraintes / DSIC** : Lavi. *Computationally Efficient
  Approximation Mechanisms*, ch. 12 dans Nisan, Roughgarden, Tardos,
  Vazirani (eds.) *Algorithmic Game Theory*, Cambridge, 2007. Nisan,
  Ronen. *Computationally Feasible VCG Mechanisms*. JAIR 29, 2007.
- **VCG avec budget non-truthful** : Borgs, Chayes, Immorlica, Mahdian,
  Saberi. *Multi-unit Auctions with Budget-Constrained Bidders*. EC 2005.
  Dobzinski, Lavi, Nisan. *Multi-unit Auctions with Budget Limits*.
  FOCS 2008 (étendu en GEB 2012).
- **Limites de VCG** : Ausubel, Milgrom. *The Lovely but Lonely Vickrey
  Auction*, in Cramton-Shoham-Steinberg (eds.) *Combinatorial Auctions*,
  MIT Press, 2006.
- **Auctions / weak budget balance** : Krishna. *Auction Theory*. Academic
  Press, 2002. Milgrom. *Putting Auction Theory to Work*. Cambridge, 2004.
- **OR-Tools CP-SAT** : https://developers.google.com/optimization/cp
- **PuLP + CBC** : https://coin-or.github.io/pulp/
