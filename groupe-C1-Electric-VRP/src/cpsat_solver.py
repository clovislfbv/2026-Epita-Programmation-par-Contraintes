from __future__ import annotations
from typing import List, Dict
from ortools.sat.python import cp_model
from .instance import EVRPInstance, DEPOT, CUSTOMER, STATION

class EVRPSolution:

    def __init__(self, routes, instance, total_dist, status, wall_time, open_stations=None):
        self.routes = routes
        self.instance = instance
        self.total_dist = total_dist
        self.status = status
        self.wall_time = wall_time
        self.open_stations = open_stations or []

    def total_dist_km(self) -> float:
        from .instance import DIST_SCALE
        return self.total_dist / DIST_SCALE

    def is_feasible(self) -> bool:
        return self.status in ('OPTIMAL', 'FEASIBLE')

    def __repr__(self) -> str:
        lines = [f'Status     : {self.status}', f'Total dist : {self.total_dist_km():.2f} km', f'Wall time  : {self.wall_time:.2f} s']
        if self.open_stations:
            lines.append(f'Stations   : {self.open_stations} ({len(self.open_stations)} open)')
        for k, route in enumerate(self.routes):
            if route:
                names = ['depot'] + [f'n{i}' for i in route] + ['depot']
                lines.append(f'  V{k}: {' → '.join(names)}')
        return '\n'.join(lines)

def solve_evrp(instance: EVRPInstance, time_limit_s: int=60, use_time_windows: bool=True, optimize_stations: bool=False, station_open_cost: int=500) -> EVRPSolution:
    inst = instance
    n = inst.n_nodes
    K = inst.n_vehicles
    B = inst.battery_capacity
    Q = inst.vehicle_capacity
    ls = inst.load_sensitivity
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    arc: List[Dict] = [{} for _ in range(K)]
    for v in range(K):
        for i in range(n):
            for j in range(n):
                arc[v][i, j] = model.new_bool_var(f'x_{v}_{i}_{j}')
    for v in range(K):
        circuit_arcs = [(i, j, arc[v][i, j]) for i in range(n) for j in range(n)]
        model.add_circuit(circuit_arcs)
    for i in inst.customer_indices:
        model.add(sum((arc[v][i, i] for v in range(K))) == K - 1)
    open_station: Dict = {}
    for s in inst.station_indices:
        if optimize_stations:
            open_station[s] = model.new_bool_var(f'open_{s}')
        else:
            v_fixed = model.new_bool_var(f'open_{s}')
            model.add(v_fixed == 1)
            open_station[s] = v_fixed
    if optimize_stations:
        for s in inst.station_indices:
            for v in range(K):
                for i in range(n):
                    if i != s:
                        model.add_implication(arc[v][i, s], open_station[s])
                        model.add_implication(arc[v][s, i], open_station[s])
    load = [[model.new_int_var(0, Q, f'ld_{v}_{i}') for i in range(n)] for v in range(K)]
    for v in range(K):
        model.add(load[v][DEPOT] == 0)
        for i in range(n):
            for j in range(n):
                if i == j or j == DEPOT:
                    continue
                if inst.node_types[j] == CUSTOMER:
                    model.add(load[v][j] == load[v][i] + inst.demands[j]).only_enforce_if(arc[v][i, j])
                else:
                    model.add(load[v][j] == load[v][i]).only_enforce_if(arc[v][i, j])
    bat_arr = [[model.new_int_var(0, B, f'ba_{v}_{i}') for i in range(n)] for v in range(K)]
    bat_dep = [[model.new_int_var(0, B, f'bd_{v}_{i}') for i in range(n)] for v in range(K)]
    for v in range(K):
        model.add(bat_dep[v][DEPOT] == B)
        for i in range(n):
            if inst.node_types[i] == STATION:
                model.add(bat_dep[v][i] == B)
            elif i != DEPOT:
                model.add(bat_dep[v][i] == bat_arr[v][i])
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                base_e = inst._energy[i][j]
                ls_bonus_per_Q = int(round(base_e * ls)) if ls > 0 else 0
                if ls_bonus_per_Q > 0:
                    bonus_var = model.new_int_var(0, ls_bonus_per_Q, f'eb_{v}_{i}_{j}')
                    model.add_division_equality(bonus_var, ls_bonus_per_Q * load[v][i], Q)
                    model.add(bat_arr[v][j] == bat_dep[v][i] - base_e - bonus_var).only_enforce_if(arc[v][i, j])
                else:
                    model.add(bat_arr[v][j] == bat_dep[v][i] - base_e).only_enforce_if(arc[v][i, j])
                model.add(bat_arr[v][j] >= 0).only_enforce_if(arc[v][i, j])
    max_time = max((tw[1] for tw in inst.time_windows)) + 120
    time_arr = [[model.new_int_var(0, max_time, f't_{v}_{i}') for i in range(n)] for v in range(K)]
    for v in range(K):
        model.add(time_arr[v][DEPOT] == 0)
        for i in range(n):
            for j in range(n):
                if i == j or j == DEPOT:
                    continue
                travel = inst.travel_time(i, j)
                service = inst.service_times[i]
                model.add(time_arr[v][j] >= time_arr[v][i] + service + travel).only_enforce_if(arc[v][i, j])
        if use_time_windows:
            for i in range(1, n):
                lo, hi = inst.time_windows[i]
                model.add(time_arr[v][i] >= lo).only_enforce_if(arc[v][i, i].negated())
                model.add(time_arr[v][i] <= hi).only_enforce_if(arc[v][i, i].negated())
    obj_terms = [inst.dist(i, j) * arc[v][i, j] for v in range(K) for i in range(n) for j in range(n) if i != j]
    if optimize_stations:
        station_cost_terms = [station_open_cost * open_station[s] for s in inst.station_indices]
        model.minimize(sum(obj_terms) + sum(station_cost_terms))
    else:
        model.minimize(sum(obj_terms))
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 4
    status_code = solver.solve(model)
    status_map = {cp_model.OPTIMAL: 'OPTIMAL', cp_model.FEASIBLE: 'FEASIBLE', cp_model.INFEASIBLE: 'INFEASIBLE', cp_model.UNKNOWN: 'UNKNOWN'}
    status = status_map.get(status_code, 'UNKNOWN')
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        routes = _extract_routes(solver, arc, inst, K, n)
        dist_val = int(solver.objective_value)
        open_stations = [s for s in inst.station_indices if solver.value(open_station[s]) == 1]
    else:
        routes = [[] for _ in range(K)]
        dist_val = -1
        open_stations = []
    return EVRPSolution(routes=routes, instance=inst, total_dist=dist_val, status=status, wall_time=solver.wall_time, open_stations=open_stations)

def _extract_routes(solver, arc, inst, K, n) -> List[List[int]]:
    routes = []
    for v in range(K):
        succ = {i: j for i in range(n) for j in range(n) if i != j and solver.value(arc[v][i, j]) == 1}
        route = []
        cur = succ.get(DEPOT, DEPOT)
        seen = set()
        while cur != DEPOT and cur not in seen:
            seen.add(cur)
            route.append(cur)
            cur = succ.get(cur, DEPOT)
        routes.append(route)
    return routes
