# results/

Sorties generees par les scripts `scripts/run_*.py`. Reproduisibles via la cible
`make bench` puis `make figures` du Makefile a la racine.

## Tableau de reference

| Fichier | Contenu |
|---------|---------|
| `reference_n50_k10.csv` | Table canonique citee dans le README et les slides : 4 solveurs sur N=50, K=10, seed=42, lam=5.0. |

## Scalabilite

| Fichier | Contenu |
|---------|---------|
| `bench.csv` | Bench scalabilite sur N in {50, 100, 200} (CP-SAT limite a N<=100, MILP a N<=300). Colonnes : N, K, solver, status, ret, risk, obj, runtime. |
| `scalability.png` | Histogramme des temps de resolution par N. |

## Front de Pareto

| Fichier | Contenu |
|---------|---------|
| `pareto.csv` | Points (lambda, ret, vol) pour GreedySharpe, GA et MILP-SCIP, N=50, K=10. |
| `pareto.png` | Front de Pareto risk-return. |

## Backtest OOS

| Fichier | Contenu |
|---------|---------|
| `backtest.csv` | Resume par periode (1..3) et par solveur : ann_return, ann_vol, sharpe, max_drawdown, total_return. |
| `backtest_cum.csv` | Series journalieres des rendements et valeur cumulee par periode/solveur. |
| `backtest.png` | Courbes de valeur cumulee sur la derniere periode. |

## Reproduction

```bash
make bench       # regenere reference_n50_k10.csv, bench.csv, scalability.png
make figures     # regenere pareto et backtest (CSV + PNG)
```

Les scripts acceptent `--seed`, `--time-limit`, `--output`. Voir `scripts/run_*.py`.
