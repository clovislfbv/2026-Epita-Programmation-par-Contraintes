# CONTEXT — G3: Drone Coordination via Multi-Agent Path Finding

## Project Overview

**Group:** G3 — Matteo Atkinson & Paul Witkowski
**Course:** EPITA 2026 — Programmation par Contraintes
**Directory:** `groupe-G3-Coordination_de_drones_par_Multi-Agent_Path_Finding/`

Multi-Agent Path Finding (MAPF) computes collision-free optimal trajectories for a set of agents (drones) sharing a common space, where each agent must reach its target. It is a combinatorially hard (NP-hard) problem that maps naturally to CP-SAT: agents cannot occupy the same position at the same time, can only move to adjacent positions, and must each reach their goal.

---

## Problem Definition

- **Agents:** a set of drones, each with a start position and a target position
- **Non-collision constraints:** no two agents at the same node at the same time (vertex conflict), and no two agents swapping positions in the same timestep (edge conflict)
- **Movement constraints:** agents can only move to adjacent positions (neighbors) or wait in place each timestep
- **Objective constraint:** every agent must reach its target within the planning horizon
- **Space model:** TBD — options are 2D grid, 3D grid, or continuous 3D airspace (see Open Decisions)
- **Complexity:** NP-hard in the general case; CP-SAT is the chosen approach to model and solve it

---

## Technical Stack (Decided)

| Component | Choice |
|-----------|--------|
| Solver | Google OR-Tools CP-SAT |
| Language | Python |
| Key notebooks | CSP-4 Scheduling (IntervalVar, NoOverlap), CSP-9 Distributed CSP, Search-3 A* |

---

## Open Decisions

These are not yet decided — do not assume defaults.

| Decision | Options | Status |
|----------|---------|--------|
| Space model | 2D grid / 3D grid / continuous 3D airspace | TBD |
| Optimization metric | Makespan (minimize max arrival time) / Flowtime (minimize sum of arrival times) / both | TBD |
| Additional constraints | NOTAM zones, ATC separation (min distance), dynamic weather, 3D obstacles | TBD |
| Benchmark set | Moving AI Lab grid-based benchmarks / custom instances | TBD |

> When an open decision is resolved, update this table and remove the TBD.

---

## Deliverables

- Documented source code in `groupe-G3-Coordination_de_drones_par_Multi-Agent_Path_Finding/`
- Jupyter Notebook with analysis and visualizations **or** a functional UI/demo
- Presentation slides (PDF or link)
- Pull Request submitted at least **2 days before the defense**

---

## Key References

- Stern, R., et al. (2019). "Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks." *SoCS*. [arXiv](https://arxiv.org/abs/1906.08291)
- Sharon, G., et al. (2015). "Conflict-Based Search for Optimal Multi-Agent Pathfinding." *Artificial Intelligence*, 219, 40–66. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0004370214001386)
- Moving AI Lab MAPF Benchmarks. [movingai.com](https://movingai.com/benchmarks/mapf/)
- Felner, A., et al. (2017). "Adding Heuristics to Conflict-Based Search for MAPF." *ICAPS*. [AAAI](https://ojs.aaai.org/index.php/ICAPS/article/view/13826)
- OR-Tools CP-SAT. [Google Documentation](https://developers.google.com/optimization/cp/cp_solver)
