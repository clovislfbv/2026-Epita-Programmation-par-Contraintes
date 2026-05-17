"""Modele de reference manuel : diet problem (minimisation du cout)."""

from ortools.sat.python import cp_model

FOODS = [
    {"name": "pomme",   "cost": 1, "kcal": 80,  "prot": 0,  "fat": 0},
    {"name": "pain",    "cost": 2, "kcal": 250, "prot": 8,  "fat": 2},
    {"name": "viande",  "cost": 5, "kcal": 400, "prot": 30, "fat": 20},
    {"name": "lait",    "cost": 1, "kcal": 150, "prot": 8,  "fat": 5},
    {"name": "oeufs",   "cost": 2, "kcal": 150, "prot": 12, "fat": 10},
    {"name": "poisson", "cost": 4, "kcal": 300, "prot": 25, "fat": 15},
]
MIN_KCAL = 2000
MIN_PROT = 50
MAX_FAT = 70
MAX_PORTIONS = 10


def solve() -> dict:
    model = cp_model.CpModel()
    n = len(FOODS)

    x = [model.NewIntVar(0, MAX_PORTIONS, FOODS[i]["name"]) for i in range(n)]

    model.Add(sum(FOODS[i]["kcal"] * x[i] for i in range(n)) >= MIN_KCAL)
    model.Add(sum(FOODS[i]["prot"] * x[i] for i in range(n)) >= MIN_PROT)
    model.Add(sum(FOODS[i]["fat"] * x[i] for i in range(n)) <= MAX_FAT)

    model.Minimize(sum(FOODS[i]["cost"] * x[i] for i in range(n)))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "objective": None}

    return {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "portions": {FOODS[i]["name"]: solver.Value(x[i]) for i in range(n)},
    }


if __name__ == "__main__":
    print(solve())
