"""Modele de reference manuel : Capacitated VRP avec 3 vehicules.

Formulation : un circuit (AddCircuit) par vehicule sur le graphe complet
{depot, clients}. Pour chaque vehicule, un noeud non-visite est realise par
un self-loop. Le self-loop du depot est force a true ssi le vehicule n'a
aucun client a livrer ; sinon le depot doit etre dans la tournee.
"""

from ortools.sat.python import cp_model

DEMANDS = [10, 20, 15, 30, 10]  # C1..C5
CAPACITY = 50
N_VEHICLES = 3

# Distances symetriques, index 0 = depot, 1..5 = C1..C5
DIST = [
    [0, 10, 12, 20, 25, 18],
    [10, 0, 8, 15, 20, 12],
    [12, 8, 0, 10, 18, 15],
    [20, 15, 10, 0, 12, 10],
    [25, 20, 18, 12, 0, 8],
    [18, 12, 15, 10, 8, 0],
]


def solve() -> dict:
    model = cp_model.CpModel()
    n_nodes = len(DIST)

    # served[k][i] : le client i (i in 1..n_nodes-1) est servi par le vehicule k.
    served = {
        (k, i): model.NewBoolVar(f"served_{k}_{i}")
        for k in range(N_VEHICLES)
        for i in range(1, n_nodes)
    }

    # Chaque client est servi par exactement un vehicule.
    for i in range(1, n_nodes):
        model.AddExactlyOne([served[k, i] for k in range(N_VEHICLES)])

    # Contrainte de capacite par vehicule.
    for k in range(N_VEHICLES):
        model.Add(
            sum(DEMANDS[i - 1] * served[k, i] for i in range(1, n_nodes)) <= CAPACITY
        )

    cost_terms = []
    arcs_by_vehicle: dict[int, list[tuple[int, int, cp_model.IntVar]]] = {}

    for k in range(N_VEHICLES):
        arcs: list = []

        # Arcs orientes entre noeuds distincts (cout DIST[i][j]).
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i == j:
                    continue
                lit = model.NewBoolVar(f"arc_{k}_{i}_{j}")
                arcs.append((i, j, lit))
                cost_terms.append(DIST[i][j] * lit)

        # Self-loops : si active, le noeud n'est pas visite par k.
        # Client : skip ssi non servi.
        depot_skip = model.NewBoolVar(f"depot_skip_{k}")
        arcs.append((0, 0, depot_skip))
        for i in range(1, n_nodes):
            skip = model.NewBoolVar(f"skip_{k}_{i}")
            arcs.append((i, i, skip))
            model.Add(skip + served[k, i] == 1)
            # Si un client est servi par k, le depot doit etre dans la tournee.
            model.AddImplication(served[k, i], depot_skip.Not())

        model.AddCircuit(arcs)
        arcs_by_vehicle[k] = arcs

    model.Minimize(sum(cost_terms))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "objective": None}

    # Reconstruction des tournees.
    routes = []
    for k in range(N_VEHICLES):
        next_node: dict[int, int] = {}
        for i, j, lit in arcs_by_vehicle[k]:
            if i == j:
                continue
            if solver.Value(lit) == 1:
                next_node[i] = j
        if 0 not in next_node:
            routes.append([0])
            continue
        route = [0]
        while next_node[route[-1]] != 0:
            route.append(next_node[route[-1]])
        route.append(0)
        routes.append(route)

    return {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "routes": routes,
    }


if __name__ == "__main__":
    print(solve())
