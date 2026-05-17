# M1 - Sparse Markowitz

Portefeuille mean-variance avec contrainte de cardinalite exacte K parmi N
actifs. Sujet M1 du cours EPITA SCIA - Programmation
par Contraintes (2026).

## Probleme

Etant donne N actifs decrits par leur rendement espere `mu in R^N` et leur
matrice de covariance `Sigma in R^{NxN}`, on cherche un portefeuille `w in R^N`
qui detient strictement K positions actives et minimise un compromis
risque-rendement parametre par `lambda > 0`.

## Formulation mathematique

Variables : `w_i in [0, w_max]` (poids), `z_i in {0, 1}` (actif retenu).

```
min   lambda * w^T Sigma w  -  mu^T w
s.c.  sum_i w_i = 1
      sum_i z_i = K
      w_min * z_i <= w_i <= w_max * z_i        (buy-in / cap)
      z_i in {0, 1}
```

Le probleme est un MIQP non convexe (la quadratique `w^T Sigma w` cumulee a la
contrainte de cardinalite le rend NP-difficile en general).

Extensions implementees :

- `sector_cap` : `sum_{i in S} w_i <= c_S` par secteur.
- `turnover_cap` : `|| w - w_prev ||_1 <= 2 * tau`, linearise via
  `d^+_i, d^-_i >= 0` et `w_i - w_prev_i = d^+_i - d^-_i`.
- `integer_lots` : `w_i * budget = n_lots_i * lot_size * price_i`, avec
  `n_lots_i in N` (MILP).

## Installation

```bash
pip install -r requirements.txt
# pour pytest et tooling :
pip install -r requirements-dev.txt
```

## Reproduction des resultats

```bash
make bench        # results/reference_n50_k10.csv + results/bench.csv + scalability.png
make pareto       # results/pareto.csv + results/pareto.png
make backtest     # results/backtest.csv + results/backtest.png
make figures      # bench + pareto + backtest en une commande
make test         # suite pytest (11 tests)
make slides       # slides/soutenance.pdf via Marp si dispo, sinon pandoc
```

Seed par defaut `42`, time-limit solveurs `10s` (`30s` pour le tableau de
reference). Tout est parametrable :

```bash
SEED=7 TIME_LIMIT=20 make bench
```

## Structure

```
M1-Sparse-Markowitz/
|-- pyproject.toml
|-- Makefile
|-- requirements.txt, requirements-dev.txt
|-- src/
|   |-- data.py            donnees (synthetique + yfinance)
|   |-- cpsat_model.py     CP-SAT + Cholesky + AddMultiplicationEquality
|   |-- milp_model.py      SCIP (MIQP via contrainte quadratique auxiliaire)
|   |-- heuristics.py      Greedy Sharpe + Genetic Algorithm (DEAP)
|   |-- benchmark.py       runner scalabilite + Pareto front
|   `-- backtest.py        rolling out-of-sample avec commissions
|-- scripts/
|   |-- run_benchmark.py   regenere bench.csv + reference_n50_k10.csv + scalability.png
|   |-- run_pareto.py      regenere pareto.csv + pareto.png
|   `-- run_backtest.py    regenere backtest.csv + backtest.png
|-- notebook/
|   `-- M1-Sparse-Markowitz.ipynb   demo complete
|-- tests/
|   |-- test_solvers.py    suite pytest (11 tests)
|   `-- smoke.py           demo console rapide
|-- results/               CSV + PNG generes par les scripts
`-- slides/
    |-- soutenance.md
    `-- soutenance.pdf     (genere par make slides)
```

## Solveurs

### MILP-SCIP (`src/milp_model.py`)

MIQP exact via pyscipopt. La quadratique `w^T Sigma w` est encapsulee dans une
variable auxiliaire `risk_var` et la contrainte `risk_var >= w^T Sigma w`, puis
SCIP minimise l'objectif lineaire `lambda * risk_var - mu^T w`. Reference de
qualite jusqu'a N <= 300.

### CP-SAT (`src/cpsat_model.py`)

Toutes les variables sont entieres : poids en basis points (scale=1000),
covariance scalee via Cholesky `Sigma = U^T U` puis `U_int = round(U *
precision)`. Pour chaque ligne k de U, on pose `y_k = sum_i U_int[k,i] * W_i`
puis `y_sq_k = y_k^2` via `AddMultiplicationEquality`. Le facteur
`g = precision^2 / 100` aligne les echelles entre `total_risk` et
`total_ret`. Limite a N <= 100 en pratique (les n produits quadratiques
explosent au-dela).

### Greedy Sharpe (`src/heuristics.py`)

Initialisation par les K meilleurs ratios `mu / sigma`, puis local search par
echange 1-vs-1. A chaque candidat, les poids continus sont resolus en ferme par
un QP avec ridge (clip + renormalisation pour respecter `w_min, w_max`).

### Genetic Algorithm (DEAP, `src/heuristics.py`)

Individu = sous-ensemble de K indices. Croisement par intersection puis
completement aleatoire, mutation par swap. Fitness = objectif MV apres QP ferme
sur le sous-ensemble selectionne.

## Resultats (N=50, K=10, lambda=5.0, seed=42)

Tableau genere par `make bench`, source `results/reference_n50_k10.csv` :

| Solveur     | Statut    | Rendement | Volatilite | Sharpe | Temps   |
|-------------|-----------|-----------|------------|--------|---------|
| MILP-SCIP   | optimal   | 0.0643    | 0.1529     | 0.420  | 0.15s   |
| CP-SAT      | feasible  | 0.0668    | 0.1550     | 0.431  | 30.01s  |
| Greedy      | heuristic | 0.0836    | 0.1771     | 0.472  | 0.15s   |
| GA          | heuristic | 0.0616    | 0.1614     | 0.382  | 0.78s   |

MILP-SCIP donne l'optimum sur cette instance. CP-SAT atteint une solution
realisable proche (gap ~3% en rendement) en 30s sur l'instance entiere. Le
Greedy obtient un meilleur Sharpe in-sample en s'autorisant plus de volatilite.

## Benchmark scalabilite

`scripts/run_benchmark.py` couvre par defaut N in {50, 100, 200} (modifiable
via `--sizes`). CP-SAT est skipped au-dela de N=100 (`--skip-cpsat-above`),
MILP au-dela de N=300 (`--skip-milp-above`). Les heuristiques tiennent
jusqu'a N=1000 mais ne sont pas executees par defaut pour garder
`make bench` rapide. Voir `results/bench.csv` et `results/scalability.png`.

## Contraintes realistes

Toutes activables independamment via les kwargs des solveurs :

- `sectors`, `sector_cap` : plafond de poids par secteur.
- `w_prev`, `turnover_cap` : limite L1 sur la deviation au portefeuille
  precedent (rebalancement realiste).
- `integer_lots`, `lot_size`, `budget`, `prices` : MILP uniquement, taille de
  lot en nombre d'actions entieres.
- `lex_symmetry` : ordre lexicographique decroissant des `z` apres tri stable
  sur `mu`. Baseline experimentale qui force la selection top-K mu (voir
  docstrings de `sparse_markowitz_cpsat` et `sparse_markowitz_milp`).

## Backtest OOS

`rolling_backtest` (cf. `src/backtest.py`) : fenetre glissante, rebalance
mensuel, commissions en basis points appliquees sur le turnover. Retourne par
solveur la courbe cumulee, le Sharpe annualise, le max drawdown. Voir
`results/backtest.csv` et `results/backtest.png`.

## Donnees S&P 500 Kaggle

`scripts/run_sp500.py` entraine sur tout l'historique sauf la derniere annee
(train) et evalue le PnL out-of-sample sur la derniere annee (test, 252 jours
de bourse), pour K de 10 a 100. Les donnees viennent du dataset Kaggle
`andrewmvd/sp-500-stocks` via `kagglehub.dataset_download(...)`.

### Cle API Kaggle (a faire une fois)

1. Sur kaggle.com -> *Settings* -> *API* -> **Create New Token** : un fichier
   `kaggle.json` est telecharge, du type `{"username":"...","key":"..."}`.
2. Le placer ici (chemin attendu par kagglehub sous Linux) :

   ```bash
   mkdir -p ~/.kaggle
   mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
   chmod 600 ~/.kaggle/kaggle.json
   ```

   Soit pour cette machine : `/home/aderugy/.kaggle/kaggle.json`.

   Alternative sans fichier : exporter `KAGGLE_USERNAME` et `KAGGLE_KEY` dans
   l'environnement.

### Lancement

Cardinalite exacte (`sum(z) == K`), comme le reste du projet.

```bash
make sp500                              # K-sweep, 150 actions liquides
SP500_MAX_ASSETS=0 make sp500           # univers complet (~500, lent)
python scripts/run_sp500.py --solvers GreedySharpe GA --max-assets 120
```

Sorties dans `results/` :

- `sp500_pnl.csv` : PnL test, Sharpe annualise, max drawdown, `n_active`,
  runtime par (K, solveur).
- `sp500_pnl_curves.csv` : valeur cumulee jour par jour sur le test.
- `sp500_pnl.png` : PnL test final en fonction de K, une courbe par solveur.
- `sp500_pnl_curves.png` : grille des courbes cumulees, un sous-graphe par K.

Le premier appel telecharge et met en cache `_cache_sp500_returns.csv` (les
suivants relisent le cache). Avec ~150 actifs et K eleve, CP-SAT et MILP-SCIP
sont lents ; `--solvers GreedySharpe GA` reste rapide.

## Limites connues

- CP-SAT necessite des entiers : la precision sur la covariance depend de
  `precision` (100 par defaut) ; au-dela de N=100 le nombre de
  `AddMultiplicationEquality` rend le modele lent.
- SCIP via pyscipopt n'expose pas de support natif pour les MIQP ; le contournement
  via contrainte quadratique auxiliaire est correct mais moins performant qu'un
  solveur dedie (Gurobi/Mosek).
- `lex_symmetry` force la selection top-K mu : a comprendre comme un controle
  d'echelle, pas comme un vrai symmetry breaking actif.
- Le backtest sur donnees synthetiques sert a valider le pipeline, pas a
  predire la performance d'un portefeuille reel.

## References

- Markowitz, H. (1952). *Portfolio Selection*. Journal of Finance, 7(1), 77-91.
- Bertsimas, D. & Shioda, R. (2009). *Algorithm for cardinality-constrained
  quadratic optimization*. Computational Optimization and Applications, 43(1),
  1-22.
- Bonami, P., Lodi, A., Tramontani, A. & Wiese, S. (2018). *On mathematical
  programming with indicator constraints*. Mathematical Programming, 151(1),
  191-223.
- Google OR-Tools, *CP-SAT Solver Reference*.
