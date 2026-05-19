from __future__ import annotations
import math
import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from .instance import EVRPInstance, DEPOT, CUSTOMER, STATION

@dataclass
class ALNSSolution:
    routes: List[List[int]]
    instance: EVRPInstance

    def total_dist(self) -> int:
        inst = self.instance
        total = 0
        for route in self.routes:
            if not route:
                continue
            prev = DEPOT
            for node in route:
                total += inst.dist(prev, node)
                prev = node
            total += inst.dist(prev, DEPOT)
        return total

    def is_feasible(self) -> bool:
        inst = self.instance
        visited = []
        for route in self.routes:
            load = 0
            for node in route:
                load += inst.demands[node]
                if load > inst.vehicle_capacity:
                    return False
            visited.extend(route)
        return sorted(visited) == sorted(inst.customer_indices)

    def total_dist_km(self) -> float:
        from .instance import DIST_SCALE
        return self.total_dist() / DIST_SCALE

    def copy(self) -> ALNSSolution:
        return ALNSSolution(routes=deepcopy(self.routes), instance=self.instance)

def greedy_initial(instance: EVRPInstance, seed: int=0) -> ALNSSolution:
    inst = instance
    unvisited = set(inst.customer_indices)
    routes = [[] for _ in range(inst.n_vehicles)]
    loads = [0] * inst.n_vehicles
    rng = random.Random(seed)
    for _ in range(len(inst.customer_indices)):
        if not unvisited:
            break
        best = None
        best_cost = math.inf
        for v in range(inst.n_vehicles):
            cur = routes[v][-1] if routes[v] else DEPOT
            for c in unvisited:
                if loads[v] + inst.demands[c] > inst.vehicle_capacity:
                    continue
                cost = inst.dist(cur, c)
                if cost < best_cost:
                    best_cost = cost
                    best = (v, c)
        if best is None:
            v = min(range(inst.n_vehicles), key=lambda k: loads[k])
            c = rng.choice(list(unvisited))
            best = (v, c)
        v, c = best
        routes[v].append(c)
        loads[v] += inst.demands[c]
        unvisited.remove(c)
    return ALNSSolution(routes=routes, instance=inst)

def random_removal(sol: ALNSSolution, n_remove: int, rng: random.Random) -> Tuple[ALNSSolution, List[int]]:
    s = sol.copy()
    removed = []
    customers = [c for route in s.routes for c in route]
    rng.shuffle(customers)
    to_remove = set(customers[:n_remove])
    for r in range(len(s.routes)):
        s.routes[r] = [c for c in s.routes[r] if c not in to_remove]
    removed = list(to_remove)
    return (s, removed)

def worst_removal(sol: ALNSSolution, n_remove: int, rng: random.Random) -> Tuple[ALNSSolution, List[int]]:
    inst = sol.instance
    savings = []
    for r_idx, route in enumerate(sol.routes):
        for pos, c in enumerate(route):
            prev = route[pos - 1] if pos > 0 else DEPOT
            nxt = route[pos + 1] if pos < len(route) - 1 else DEPOT
            cost_with = inst.dist(prev, c) + inst.dist(c, nxt)
            cost_without = inst.dist(prev, nxt)
            savings.append((cost_with - cost_without, r_idx, c))
    savings.sort(reverse=True)
    to_remove = {c for _, _, c in savings[:n_remove]}
    s = sol.copy()
    for r in range(len(s.routes)):
        s.routes[r] = [c for c in s.routes[r] if c not in to_remove]
    return (s, list(to_remove))

def related_removal(sol: ALNSSolution, n_remove: int, rng: random.Random) -> Tuple[ALNSSolution, List[int]]:
    inst = sol.instance
    customers = [c for route in sol.routes for c in route]
    if not customers:
        return (sol.copy(), [])
    seed_c = rng.choice(customers)
    removed = [seed_c]
    while len(removed) < n_remove:
        last = rng.choice(removed)
        cands = sorted([c for c in customers if c not in removed], key=lambda c: inst.dist(last, c))
        if not cands:
            break
        top = cands[:max(1, len(cands) // 2)]
        removed.append(rng.choice(top))
    to_remove = set(removed)
    s = sol.copy()
    for r in range(len(s.routes)):
        s.routes[r] = [c for c in s.routes[r] if c not in to_remove]
    return (s, list(to_remove))

def greedy_insertion(sol: ALNSSolution, customers: List[int], rng: random.Random) -> ALNSSolution:
    inst = sol.instance
    s = sol.copy()
    order = customers[:]
    rng.shuffle(order)
    for c in order:
        best_cost = math.inf
        best_pos = None
        for r_idx, route in enumerate(s.routes):
            cur_load = sum((inst.demands[x] for x in route))
            if cur_load + inst.demands[c] > inst.vehicle_capacity:
                continue
            for pos in range(len(route) + 1):
                prev = route[pos - 1] if pos > 0 else DEPOT
                nxt = route[pos] if pos < len(route) else DEPOT
                delta = inst.dist(prev, c) + inst.dist(c, nxt) - inst.dist(prev, nxt)
                if delta < best_cost:
                    best_cost = delta
                    best_pos = (r_idx, pos)
        if best_pos is not None:
            r_idx, pos = best_pos
            s.routes[r_idx].insert(pos, c)
        else:
            for r_idx, route in enumerate(s.routes):
                if not route:
                    s.routes[r_idx].append(c)
                    break
    return s

def regret_2_insertion(sol: ALNSSolution, customers: List[int], rng: random.Random) -> ALNSSolution:
    inst = sol.instance
    s = sol.copy()
    remaining = customers[:]
    while remaining:
        best_regret = -math.inf
        best_c = None
        best_insert = None
        for c in remaining:
            costs = []
            for r_idx, route in enumerate(s.routes):
                cur_load = sum((inst.demands[x] for x in route))
                if cur_load + inst.demands[c] > inst.vehicle_capacity:
                    continue
                for pos in range(len(route) + 1):
                    prev = route[pos - 1] if pos > 0 else DEPOT
                    nxt = route[pos] if pos < len(route) else DEPOT
                    delta = inst.dist(prev, c) + inst.dist(c, nxt) - inst.dist(prev, nxt)
                    costs.append((delta, r_idx, pos))
            if not costs:
                continue
            costs.sort()
            regret = costs[1][0] - costs[0][0] if len(costs) > 1 else 0
            if regret > best_regret:
                best_regret = regret
                best_c = c
                best_insert = costs[0][1:]
        if best_c is None:
            break
        r_idx, pos = best_insert
        s.routes[r_idx].insert(pos, best_c)
        remaining.remove(best_c)
    return s

def insert_charging_stops(sol: ALNSSolution) -> ALNSSolution:
    inst = sol.instance
    if not inst.station_indices:
        return sol.copy()
    s = sol.copy()
    for r_idx, route in enumerate(s.routes):
        battery = inst.battery_capacity
        new_route: List[int] = []
        prev = DEPOT
        for node in route:
            e = inst.energy(prev, node, load=0)
            if battery - e < 0:
                best_s = min(inst.station_indices, key=lambda st: inst.dist(prev, st) + inst.dist(st, node))
                e_to_s = inst.energy(prev, best_s, load=0)
                e_s_to = inst.energy(best_s, node, load=0)
                if battery >= e_to_s:
                    new_route.append(best_s)
                    battery = inst.battery_capacity - e_s_to
                else:
                    battery -= e
            else:
                battery -= e
            new_route.append(node)
            prev = node
        s.routes[r_idx] = new_route
    return s

class ALNS:

    def __init__(self, instance: EVRPInstance, segment_size: int=100, initial_temp: float=100.0, cooling: float=0.9995, removal_fraction: float=0.2, seed: int=42):
        self.instance = instance
        self.segment_size = segment_size
        self.initial_temp = initial_temp
        self.cooling = cooling
        self.removal_fraction = removal_fraction
        self.seed = seed

    def solve(self, n_iterations: int) -> Tuple[ALNSSolution, List[int], List[int]]:
        instance = self.instance
        rng = random.Random(self.seed)
        n_remove = max(1, int(len(instance.customer_indices) * self.removal_fraction))
        current = greedy_initial(instance, seed=self.seed)
        current = insert_charging_stops(current)
        best = current.copy()
        destroy_ops = [random_removal, worst_removal, related_removal]
        repair_ops = [greedy_insertion, regret_2_insertion]
        d_weights = [1.0] * len(destroy_ops)
        r_weights = [1.0] * len(repair_ops)
        d_scores = [0.0] * len(destroy_ops)
        r_scores = [0.0] * len(repair_ops)
        d_uses = [0] * len(destroy_ops)
        r_uses = [0] * len(repair_ops)
        temp = self.initial_temp
        history_best: List[int] = []
        history_current: List[int] = []
        for it in range(n_iterations):
            d_idx = _roulette(d_weights, rng)
            r_idx = _roulette(r_weights, rng)
            destroyed, removed = destroy_ops[d_idx](current, n_remove, rng)
            candidate = repair_ops[r_idx](destroyed, removed, rng)
            candidate = insert_charging_stops(candidate)
            delta = candidate.total_dist() - current.total_dist()
            if delta < 0 or rng.random() < math.exp(-delta / max(temp, 1e-06)):
                current = candidate
                score = 1.5 if delta < 0 else 1.0
            else:
                score = 0.5
            if current.total_dist() < best.total_dist() and current.is_feasible():
                best = current.copy()
                score = 3.0
            d_scores[d_idx] += score
            r_scores[r_idx] += score
            d_uses[d_idx] += 1
            r_uses[r_idx] += 1
            if (it + 1) % self.segment_size == 0:
                reaction = 0.5
                for i in range(len(destroy_ops)):
                    if d_uses[i] > 0:
                        d_weights[i] = (1 - reaction) * d_weights[i] + reaction * d_scores[i] / d_uses[i]
                        d_scores[i] = d_uses[i] = 0
                for i in range(len(repair_ops)):
                    if r_uses[i] > 0:
                        r_weights[i] = (1 - reaction) * r_weights[i] + reaction * r_scores[i] / r_uses[i]
                        r_scores[i] = r_uses[i] = 0
            temp *= self.cooling
            history_best.append(best.total_dist())
            history_current.append(current.total_dist())
        return (best, history_best, history_current)

def solve_alns(instance: EVRPInstance, n_iterations: int=1000, segment_size: int=100, initial_temp: float=100.0, cooling: float=0.9995, removal_fraction: float=0.2, seed: int=42) -> Tuple[ALNSSolution, List[int], List[int]]:
    solver = ALNS(
        instance=instance,
        segment_size=segment_size,
        initial_temp=initial_temp,
        cooling=cooling,
        removal_fraction=removal_fraction,
        seed=seed
    )
    return solver.solve(n_iterations)

def _roulette(weights: List[float], rng: random.Random) -> int:
    total = sum(weights)
    r = rng.uniform(0, total)
    cumul = 0.0
    for i, w in enumerate(weights):
        cumul += w
        if r <= cumul:
            return i
    return len(weights) - 1
