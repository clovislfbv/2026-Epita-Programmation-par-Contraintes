"""Modele de reference manuel : coloration de graphe avec minimisation du nombre de couleurs."""

from ortools.sat.python import cp_model

EDGES = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]
N_NODES = 6


def solve() -> dict:
    model = cp_model.CpModel()

    color = [model.NewIntVar(0, N_NODES - 1, f"c_{v}") for v in range(N_NODES)]
    n_colors = model.NewIntVar(0, N_NODES - 1, "n_colors")

    for u, v in EDGES:
        model.Add(color[u] != color[v])

    model.AddMaxEquality(n_colors, color)
    model.Minimize(n_colors)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "coloring": None, "n_colors": None}

    return {
        "status": solver.StatusName(status),
        "coloring": [solver.Value(c) for c in color],
        "n_colors": int(solver.ObjectiveValue()) + 1,
    }


if __name__ == "__main__":
    result = solve()
    print(result)
