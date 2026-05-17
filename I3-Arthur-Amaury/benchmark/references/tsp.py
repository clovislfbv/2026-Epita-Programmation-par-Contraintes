"""Modele de reference manuel : TSP 4 villes avec AddCircuit."""

from ortools.sat.python import cp_model

CITIES = ["A", "B", "C", "D"]
DIST = [
    [0, 10, 15, 20],
    [10, 0, 35, 25],
    [15, 35, 0, 30],
    [20, 25, 30, 0],
]


def solve() -> dict:
    model = cp_model.CpModel()
    n = len(CITIES)

    arcs = []
    cost_terms = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            lit = model.NewBoolVar(f"x_{i}_{j}")
            arcs.append((i, j, lit))
            cost_terms.append(DIST[i][j] * lit)

    model.AddCircuit(arcs)
    model.Minimize(sum(cost_terms))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "objective": None}

    next_city = {i: j for (i, j, lit) in arcs if solver.Value(lit) == 1}
    route_idx = [0]
    while next_city[route_idx[-1]] != 0:
        route_idx.append(next_city[route_idx[-1]])
    route_idx.append(0)

    return {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "route": [CITIES[i] for i in route_idx],
    }


if __name__ == "__main__":
    print(solve())
