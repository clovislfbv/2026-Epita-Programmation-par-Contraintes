"""Modele de reference manuel : bin packing avec minimisation du nombre de boites."""

from ortools.sat.python import cp_model

SIZES = [10, 20, 30, 40, 50]
CAPACITY = 60
N_BINS = 5  # borne sup triviale = un objet par boite


def solve() -> dict:
    model = cp_model.CpModel()
    n_items = len(SIZES)

    x = [
        [model.NewBoolVar(f"x_{i}_{b}") for b in range(N_BINS)] for i in range(n_items)
    ]
    used = [model.NewBoolVar(f"used_{b}") for b in range(N_BINS)]

    for i in range(n_items):
        model.AddExactlyOne(x[i])

    for b in range(N_BINS):
        model.Add(sum(SIZES[i] * x[i][b] for i in range(n_items)) <= CAPACITY * used[b])

    # Brisure de symetrie : on remplit dans l'ordre.
    for b in range(N_BINS - 1):
        model.Add(used[b] >= used[b + 1])

    model.Minimize(sum(used))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "objective": None}

    assignment = []
    for i in range(n_items):
        for b in range(N_BINS):
            if solver.Value(x[i][b]) == 1:
                assignment.append(b)
                break

    return {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "assignment": assignment,
    }


if __name__ == "__main__":
    print(solve())
