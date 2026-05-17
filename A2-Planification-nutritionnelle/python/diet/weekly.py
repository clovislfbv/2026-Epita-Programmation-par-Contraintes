from __future__ import annotations

from time import perf_counter
from typing import Any, Callable, Dict, List, Tuple

from .preferences import score_item_penalty

try:
    from ortools.sat.python import cp_model
    from ortools.linear_solver import pywraplp

    HAS_ORTOOLS = True
except Exception:
    cp_model = None
    pywraplp = None
    HAS_ORTOOLS = False

DEFAULT_COST_SCALE = 100

Dish = Dict[str, Any]
Bounds = Dict[str, Dict[str, Any]]
MealMap = Dict[str, List[Dish]]
VarMap = Dict[Tuple[int, str], Any]


def _prepare_inputs(
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
) -> tuple[list[str], list[Dish], MealMap]:
    nutrient_keys = list(bounds.keys())
    seasonal_dishes = [dish for dish in dishes if season in dish.get("seasons", [])]
    meal_map: MealMap = {}
    for dish in seasonal_dishes:
        meal_map.setdefault(dish["meal"], []).append(dish)
    return nutrient_keys, seasonal_dishes, meal_map


def _scaled(value: float, scale: int | None) -> float | int:
    return int(round(value * scale)) if scale is not None else float(value)


def _sum_nutrients(dishes: List[Dish], keys: List[str]) -> Dict[str, int]:
    totals = {key: 0 for key in keys}
    for dish in dishes:
        nutrients = dish.get("nutrients", {})
        for key in keys:
            totals[key] += int(nutrients.get(key, 0))
    return totals


def add_meal_choice_constraints(
    add_exactly_one: Callable[[List[Any]], Any],
    variables: VarMap,
    meal_map: MealMap,
    days: int,
) -> str | None:
    for day in range(days):
        for meal, meal_dishes in meal_map.items():
            vars_for_meal = [variables[(day, dish["id"])] for dish in meal_dishes]
            if not vars_for_meal:
                return f"no_dishes_for_meal_{meal}"
            add_exactly_one(vars_for_meal)
    return None


def add_unique_meal_constraints(
    add_constraint: Callable[[Any], Any],
    variables: VarMap,
    meal_map: MealMap,
    days: int,
) -> None:
    for meal_dishes in meal_map.values():
        for dish in meal_dishes:
            expr = sum(variables[(day, dish["id"])] for day in range(days))
            add_constraint(expr <= 1)


def add_nutritional_constraints(
    add_constraint: Callable[[Any], Any],
    variables: VarMap,
    dishes: List[Dish],
    nutrient_keys: List[str],
    bounds: Bounds,
    days: int,
) -> None:
    for day in range(days):
        for nutrient in nutrient_keys:
            expr = sum(
                variables[(day, dish["id"])]
                * int(dish.get("nutrients", {}).get(nutrient, 0))
                for dish in dishes
            )
            minimum = bounds[nutrient].get("min")
            maximum = bounds[nutrient].get("max")
            if minimum is not None:
                add_constraint(expr >= int(minimum))
            if maximum is not None:
                add_constraint(expr <= int(maximum))


def add_budget_constraint(
    add_constraint: Callable[[Any], Any],
    variables: VarMap,
    dishes: List[Dish],
    days: int,
    budget: float | None,
    cost_scale: int | None,
) -> None:
    if budget is None:
        return

    budget_value = _scaled(float(budget), cost_scale)
    total_cost = sum(
        variables[(day, dish["id"])] * _scaled(float(dish.get("cost", 0.0)), cost_scale)
        for day in range(days)
        for dish in dishes
    )
    add_constraint(total_cost <= budget_value)


def add_preference_constraints(
    dishes: List[Dish],
    preferences: Dict[str, Any],
    cost_scale: int | None,
) -> Dict[str, float | int]:
    return {
        dish["id"]: _scaled(score_item_penalty(dish, preferences), cost_scale)
        for dish in dishes
    }


def build_objective(
    set_objective: Callable[[Any], Any],
    variables: VarMap,
    dishes: List[Dish],
    preferences: Dict[str, Any],
    days: int,
    cost_scale: int | None,
) -> None:
    penalties = add_preference_constraints(dishes, preferences, cost_scale)
    terms = []
    for day in range(days):
        for dish in dishes:
            dish_id = dish["id"]
            cost = _scaled(float(dish.get("cost", 0.0)), cost_scale)
            terms.append((cost + penalties[dish_id]) * variables[(day, dish_id)])
    set_objective(sum(terms))


def build_week_plan(
    value_fn: Callable[[Any], float],
    variables: VarMap,
    meal_map: MealMap,
    days: int,
    nutrient_keys: List[str],
) -> tuple[list[dict[str, Any]], float, dict[str, int]]:
    week_plan: list[dict[str, Any]] = []
    weekly_cost = 0.0
    weekly_totals = {key: 0 for key in nutrient_keys}

    for day in range(days):
        day_dishes: List[Dish] = []
        meals: Dict[str, Any] = {}
        for meal, meal_dishes in meal_map.items():
            selected = next(
                (
                    dish
                    for dish in meal_dishes
                    if value_fn(variables[(day, dish["id"])]) > 0.5
                ),
                None,
            )
            if selected is None:
                continue
            meals[meal] = {
                "id": selected["id"],
                "name": selected.get("name", selected["id"]),
                "cost": float(selected.get("cost", 0.0)),
                "tags": selected.get("tags", []),
            }
            day_dishes.append(selected)

        day_totals = _sum_nutrients(day_dishes, nutrient_keys)
        day_cost = sum(float(dish.get("cost", 0.0)) for dish in day_dishes)
        weekly_cost += day_cost
        for key in nutrient_keys:
            weekly_totals[key] += day_totals.get(key, 0)

        week_plan.append(
            {
                "day": day + 1,
                "meals": meals,
                "totals": day_totals,
                "cost": round(day_cost, 2),
            }
        )

    return week_plan, weekly_cost, weekly_totals


def _solve_weekly_model(
    solver_label: str,
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
    budget: float | None,
    preferences: Dict[str, Any] | None,
    days: int,
    cost_scale: int | None,
    create_var: Callable[[int, str], Any],
    add_exactly_one: Callable[[List[Any]], Any],
    add_constraint: Callable[[Any], Any],
    set_objective: Callable[[Any], Any],
    solve_fn: Callable[[], int],
    value_fn: Callable[[Any], float],
    status_map: Dict[int, str],
    success_statuses: set[int],
) -> Dict[str, Any]:
    preferences = preferences or {}
    nutrient_keys, seasonal_dishes, meal_map = _prepare_inputs(dishes, bounds, season)

    if not meal_map:
        return {
            "status": "infeasible",
            "reason": "no_dishes_for_season",
            "days": [],
        }

    for meal, meal_dishes in meal_map.items():
        if len(meal_dishes) < days:
            return {
                "status": "infeasible",
                "reason": f"not_enough_unique_dishes_{meal}",
                "days": [],
            }

    variables: VarMap = {
        (day, dish["id"]): create_var(day, dish["id"])
        for day in range(days)
        for dish in seasonal_dishes
    }

    reason = add_meal_choice_constraints(add_exactly_one, variables, meal_map, days)
    if reason:
        return {
            "status": "infeasible",
            "reason": reason,
            "days": [],
        }

    add_unique_meal_constraints(add_constraint, variables, meal_map, days)
    add_nutritional_constraints(
        add_constraint, variables, seasonal_dishes, nutrient_keys, bounds, days
    )
    add_budget_constraint(
        add_constraint, variables, seasonal_dishes, days, budget, cost_scale
    )
    build_objective(
        set_objective,
        variables,
        seasonal_dishes,
        preferences,
        days,
        cost_scale,
    )

    status = solve_fn()
    status_label = status_map.get(status, "unknown")

    if status not in success_statuses:
        return {
            "status": status_label,
            "solver": solver_label,
            "days": [],
        }

    week_plan, weekly_cost, weekly_totals = build_week_plan(
        value_fn, variables, meal_map, days, nutrient_keys
    )

    return {
        "status": status_label,
        "solver": solver_label,
        "days": week_plan,
        "weekly_cost": round(weekly_cost, 2),
        "weekly_totals": weekly_totals,
    }


def solve_weekly_cpsat(
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
    budget: float | None = None,
    preferences: Dict[str, Any] | None = None,
    days: int = 7,
    time_limit: float = 10.0,
    cost_scale: int = DEFAULT_COST_SCALE,
) -> Dict[str, Any]:
    if not HAS_ORTOOLS or cp_model is None:
        return {
            "status": "error",
            "reason": "ortools_not_available",
        }

    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)

    status_map = {
        cp_model.OPTIMAL: "optimal",
        cp_model.FEASIBLE: "feasible",
        cp_model.INFEASIBLE: "infeasible",
        cp_model.MODEL_INVALID: "invalid",
        cp_model.UNKNOWN: "unknown",
    }

    return _solve_weekly_model(
        "cpsat",
        dishes,
        bounds,
        season,
        budget,
        preferences,
        days,
        cost_scale,
        lambda day, dish_id: model.NewBoolVar(f"x_{day}_{dish_id}"),
        model.AddExactlyOne,
        model.Add,
        model.Minimize,
        lambda: solver.Solve(model),
        solver.Value,
        status_map,
        {cp_model.OPTIMAL, cp_model.FEASIBLE},
    )


def solve_weekly_lp(
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
    budget: float | None = None,
    preferences: Dict[str, Any] | None = None,
    days: int = 7,
    time_limit: float = 10.0,
) -> Dict[str, Any]:
    if not HAS_ORTOOLS or pywraplp is None:
        return {
            "status": "error",
            "reason": "ortools_not_available",
        }

    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        return {"status": "error", "reason": "scip_not_available"}

    solver.SetTimeLimit(int(time_limit * 1000))

    status_map = {
        pywraplp.Solver.OPTIMAL: "optimal",
        pywraplp.Solver.FEASIBLE: "feasible",
        pywraplp.Solver.INFEASIBLE: "infeasible",
        pywraplp.Solver.UNBOUNDED: "unbounded",
        pywraplp.Solver.ABNORMAL: "abnormal",
        pywraplp.Solver.NOT_SOLVED: "not_solved",
    }

    return _solve_weekly_model(
        "lp",
        dishes,
        bounds,
        season,
        budget,
        preferences,
        days,
        None,
        lambda day, dish_id: solver.IntVar(0, 1, f"x_{day}_{dish_id}"),
        lambda vars_for_meal: solver.Add(sum(vars_for_meal) == 1),
        solver.Add,
        solver.Minimize,
        solver.Solve,
        lambda var: var.solution_value(),
        status_map,
        {pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE},
    )


def solve_weekly(
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
    budget: float | None = None,
    preferences: Dict[str, Any] | None = None,
    days: int = 7,
    solver: str = "cpsat",
) -> Dict[str, Any]:
    if solver == "lp":
        return solve_weekly_lp(dishes, bounds, season, budget, preferences, days)

    return solve_weekly_cpsat(dishes, bounds, season, budget, preferences, days)


def benchmark_weekly(
    dishes: List[Dish],
    bounds: Bounds,
    season: str,
    budget: float | None = None,
    preferences: Dict[str, Any] | None = None,
    days: int = 7,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    for solver_name in ("cpsat", "lp"):
        started_at = perf_counter()
        result = solve_weekly(
            dishes,
            bounds,
            season,
            budget,
            preferences,
            days,
            solver=solver_name,
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        results[solver_name] = {
            **result,
            "elapsed_ms": elapsed_ms,
        }

    return {
        "status": "ok",
        "solvers": results,
    }
