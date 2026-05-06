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
- **Status:** open
- **Acceptance:**
  - [x] parser handles arbitrary/matching/paths/regions/scheduling
  - [x] 18 seeds parse and solve OPTIMAL via CP-SAT
- **Discussion:**
  - @NCH04: dummy goods reconstruct xor_groups
  - @Sosolalt (review): parser + dataset land together
