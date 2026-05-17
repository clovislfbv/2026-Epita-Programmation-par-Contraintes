"""Modele de reference manuel : sac-a-dos 0/1."""

from ortools.sat.python import cp_model

WEIGHTS = [10, 20, 30, 15, 25, 5, 12]
VALUES = [60, 100, 120, 80, 110, 30, 50]
CAPACITY = 50


def solve() -> dict:
    n = len(WEIGHTS)
    model = cp_model.CpModel()

    take = [model.NewBoolVar(f"take_{i}") for i in range(n)]

    model.Add(sum(WEIGHTS[i] * take[i] for i in range(n)) <= CAPACITY)
    model.Maximize(sum(VALUES[i] * take[i] for i in range(n)))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "selection": None, "value": None}

    return {
        "status": solver.StatusName(status),
        "selection": [i for i in range(n) if solver.Value(take[i])],
        "value": int(solver.ObjectiveValue()),
    }


if __name__ == "__main__":
    result = solve()
    print(result)
