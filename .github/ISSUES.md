# Issues ledger

In-repo issue tracker. Source of truth for the planning trail. Each
entry mirrors either a real PR (with merge commit) or a self-contained
direct commit on `main`.

Lifecycle: planning commit `docs(plan): open issue #N` adds the entry;
closing commit `docs(plan): close issue #N` flips the Status line. PRs
reference issue numbers in their merge messages.

## #1 — Synthetic instance generator (random + regions)
- **Owner:** @NCH04
- **Reviewer:** @Sosolalt
- **Branch:** feat/generator
- **Status:** closed 2026-04-28 by merge of PR #1, reviewed by @Sosolalt
- **Acceptance:**
  - [x] random + regions distributions
  - [x] reproducible by seed
- **Discussion:**
  - @NCH04: small/med/large/stress sizes
  - @Sosolalt (review): outputs reproducible by seed

## #2 — Greedy LOS heuristic
- **Owner:** @56Nights
- **Reviewer:** @Sosolalt
- **Branch:** main (direct)
- **Status:** closed 2026-05-04, reviewed by @Sosolalt
- **Acceptance:**
  - [x] LOS ranking by price / sqrt(|S|)
  - [x] respects exclusivity and budget
- **Discussion:**
  - @56Nights: drafting LOS
  - @Sosolalt (review): heuristic matches expected ranking on toy

## #3 — CATS parser + 18 official seeds
- **Owner:** @NCH04
- **Reviewer:** @Sosolalt
- **Branch:** feat/cats
- **Status:** closed 2026-05-06 by merge of PR #2, reviewed by @Sosolalt
- **Acceptance:**
  - [x] parser handles arbitrary/matching/paths/regions/scheduling
  - [x] 18 seeds parse and solve OPTIMAL via CP-SAT
- **Discussion:**
  - @NCH04: dummy goods reconstruct xor_groups
  - @Sosolalt (review): parser + dataset land together

## #4 — VCG with budget — DSIC analysis
- **Owner:** @Sosolalt
- **Reviewer:** @56Nights
- **Branch:** main (direct)
- **Status:** closed 2026-05-14, reviewed by @56Nights
- **Acceptance:**
  - [x] welfare reoptimization handles budget
  - [x] research note documenting DSIC failure under hard budgets
- **Discussion:**
  - @Sosolalt: budgets break truthfulness — algebra + numeric example
  - @56Nights (review): note clarifies non-truthfulness under budgets

## #5 — CATS benchmarks status note
- **Owner:** @NCH04
- **Reviewer:** @56Nights
- **Branch:** main (direct)
- **Status:** closed 2026-05-11, reviewed by @56Nights
- **Acceptance:**
  - [x] coverage / scaling / gaps documented
- **Discussion:**
  - @NCH04: scope (5 economic distributions vs L1-L8 out-of-scope)
  - @56Nights (review): limitations clearly stated

## #6 — Notebook full rebuild
- **Owner:** @56Nights
- **Reviewer:** @Sosolalt
- **Branch:** feat/notebook
- **Status:** closed 2026-05-14 by merge of PR #3, reviewed by @Sosolalt
- **Acceptance:**
  - [x] theory + WDP modeling sections
  - [x] CP-SAT vs MILP benchmarks + figures
  - [x] CATS, greedy, VCG-budget, audit sections
  - [x] reproducible via build_notebook.py
- **Discussion:**
  - @56Nights: 55 cells, 4 figures
  - @Sosolalt (review): runs end-to-end on fresh venv
