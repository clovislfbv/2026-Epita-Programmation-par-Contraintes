"""Modele de reference manuel : N-queens (N=8)."""

from ortools.sat.python import cp_model


def solve(n: int = 8) -> dict:
    model = cp_model.CpModel()

    queens = [model.NewIntVar(0, n - 1, f"q{i}") for i in range(n)]

    model.AddAllDifferent(queens)
    model.AddAllDifferent([queens[i] + i for i in range(n)])
    model.AddAllDifferent([queens[i] - i for i in range(n)])

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "assignment": None}

    return {
        "status": solver.StatusName(status),
        "assignment": [solver.Value(q) for q in queens],
    }


if __name__ == "__main__":
    result = solve(8)
    print(result)
